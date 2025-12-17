"""REPL loop and command handlers for pgtail."""

import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from pgtail_py.colors import (
    LOG_STYLE,
    format_log_entry_with_highlights,
    format_slow_query_entry,
    print_log_entry,
)
from pgtail_py.commands import PgtailCompleter
from pgtail_py.config import (
    SETTINGS_SCHEMA,
    ConfigSchema,
    create_default_config,
    delete_config_key,
    ensure_history_dir,
    get_config_path,
    get_default_value,
    get_history_path,
    load_config,
    parse_value,
    reset_config,
    save_config,
    validate_key,
)
from pgtail_py.detector import detect_all
from pgtail_py.enable_logging import enable_logging
from pgtail_py.export import (
    ExportFormat,
    confirm_overwrite,
    export_to_file,
    follow_export,
    get_filtered_entries,
    parse_since,
    pipe_to_command,
)
from pgtail_py.filter import LogLevel, parse_levels
from pgtail_py.instance import Instance
from pgtail_py.regex_filter import (
    FilterState,
    FilterType,
    Highlight,
    RegexFilter,
    parse_filter_arg,
)
from pgtail_py.slow_query import (
    DurationStats,
    SlowQueryConfig,
    extract_duration,
    validate_thresholds,
)
from pgtail_py.tailer import LogTailer
from pgtail_py.terminal import enable_vt100_mode, reset_terminal
from pgtail_py.time_filter import TimeFilter, is_future_time, parse_time


def _warn(msg: str) -> None:
    """Print a warning message."""
    print(f"Warning: {msg}")


@dataclass
class AppState:
    """Runtime state for the REPL session.

    Attributes:
        instances: List of detected PostgreSQL instances
        current_instance: Currently selected instance for tailing
        active_levels: Set of log levels to display (all by default)
        regex_state: Regex pattern filter state
        time_filter: Time-based filter state
        slow_query_config: Configuration for slow query highlighting
        duration_stats: Session-scoped query duration statistics
        tailing: Whether actively tailing a log file
        history_path: Path to command history file
        tailer: Active log tailer instance
        stop_event: Event to signal tail stop
        shell_mode: Whether in shell mode (next input runs as shell command)
        config: Loaded configuration from config file
    """

    instances: list[Instance] = field(default_factory=list)
    current_instance: Instance | None = None
    active_levels: set[LogLevel] | None = field(default_factory=LogLevel.all_levels)
    regex_state: FilterState = field(default_factory=FilterState.empty)
    time_filter: TimeFilter = field(default_factory=TimeFilter.empty)
    slow_query_config: SlowQueryConfig = field(default_factory=SlowQueryConfig)
    duration_stats: DurationStats = field(default_factory=DurationStats)
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)
    tailer: LogTailer | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    shell_mode: bool = False
    config: ConfigSchema = field(default_factory=ConfigSchema)

    def __post_init__(self) -> None:
        """Load config and apply settings after initialization."""
        self.config = load_config(warn_func=_warn)
        self._apply_config()

    def _apply_config(self) -> None:
        """Apply configuration settings to state."""
        # Apply default.levels if configured
        if self.config.default.levels:
            import contextlib

            valid_levels: set[LogLevel] = set()
            for level_name in self.config.default.levels:
                with contextlib.suppress(ValueError):
                    valid_levels.add(LogLevel.from_string(level_name))
            if valid_levels:
                self.active_levels = valid_levels

        # Apply slow.* thresholds
        self.slow_query_config = SlowQueryConfig(
            enabled=True,
            warning_ms=self.config.slow.warn,
            slow_ms=self.config.slow.error,
            critical_ms=self.config.slow.critical,
        )


def _shorten_path(path: Path) -> str:
    """Replace home directory with ~ for display."""
    home = Path.home()
    path_str = str(path)
    home_str = str(home)
    if path_str.startswith(home_str):
        return "~" + path_str[len(home_str) :]
    return path_str


def _detect_windows_shell() -> str:
    """Detect the parent shell on Windows.

    Returns:
        'powershell' if running from PowerShell, 'cmd' otherwise.
    """
    import psutil

    try:
        proc = psutil.Process()
        # Walk up the process tree to find the shell
        for _ in range(5):  # Check up to 5 levels
            parent = proc.parent()
            if parent is None:
                break
            name = parent.name().lower()
            if "powershell" in name or "pwsh" in name:
                return "powershell"
            if name == "cmd.exe":
                return "cmd"
            proc = parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    # Default to PowerShell on modern Windows
    return "powershell"


def run_shell(cmd_line: str) -> None:
    """Run a shell command.

    Args:
        cmd_line: The command to run.
    """
    if not cmd_line:
        return

    if sys.platform == "win32":
        shell = _detect_windows_shell()
        if shell == "powershell":
            shell_cmd = ["powershell", "-NoProfile", "-Command", cmd_line]
        else:
            shell_cmd = ["cmd", "/c", cmd_line]
    else:
        shell_cmd = ["sh", "-c", cmd_line]

    try:
        subprocess.run(shell_cmd, check=False)
    except Exception as e:
        print(f"Shell error: {e}")


def format_instances_table(instances: list[Instance]) -> str:
    """Format instances as an aligned table.

    Args:
        instances: List of instances to format.

    Returns:
        Formatted table string matching Go version format.
    """
    if not instances:
        return """No PostgreSQL instances found.

Suggestions:
  - Start a PostgreSQL instance
  - Set PGDATA environment variable to your data directory
  - Run 'refresh' after starting PostgreSQL
  - Check ~/.pgrx/ for pgrx development instances"""

    # Header matches Go version: #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
    lines = ["  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY"]
    for inst in instances:
        data_dir = _shorten_path(inst.data_dir)
        source = inst.source.value  # process, pgrx, pgdata, known
        lines.append(
            f"  {inst.id}  {inst.version:<8} {inst.port_str:<6} {inst.status_str:<8} "
            f"{inst.log_status:<4} {source:<7} {data_dir}"
        )

    return "\n".join(lines)


def list_command(state: AppState) -> None:
    """Handle the 'list' command - show detected instances."""
    print(format_instances_table(state.instances))


def help_command() -> None:
    """Handle the 'help' command - show available commands."""
    help_text = """
Available commands:
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (by ID or data directory path)
  levels [LEVEL...] Set log level filter (e.g., 'levels ERROR WARNING')
                    With no args, shows current filter settings
                    Use 'levels ALL' to show all levels
  filter /pattern/  Filter logs by regex pattern
                    -/pattern/  Exclude matching lines
                    +/pattern/  Add OR pattern
                    &/pattern/  Add AND pattern
                    /pattern/c  Case-sensitive match
                    clear       Clear all filters
  highlight /pattern/  Highlight matching text (yellow background)
                    /pattern/c  Case-sensitive highlight
                    clear       Clear all highlights
  since <time>      Filter logs since time (e.g., 'since 5m', 'since 14:30')
                    clear       Remove time filter
  slow [w s c]      Configure slow query highlighting (thresholds in ms)
                    With no args, shows current settings
                    'slow off' disables highlighting
  stats             Show query duration statistics
  set <key> [val]   Set/view a config value (e.g., 'set slow.warn 50')
                    With no value, shows current setting
  unset <key>       Remove a setting to revert to default
  config            Show current configuration as TOML
                    Subcommands: path, edit, reset
  export <file>     Export filtered logs to file
                    --format <fmt>  Output format (text, json, csv)
                    --since <time>  Only entries after time (1h, 30m, 2d)
                    --append        Append to existing file
                    --follow        Continuous export (like tail -f | tee)
  pipe <cmd>        Pipe filtered logs to external command
                    --format <fmt>  Output format (text, json, csv)
  stop              Stop current tail and return to prompt
  refresh           Re-scan for PostgreSQL instances
  enable-logging <id>  Enable logging_collector for an instance
  clear             Clear the screen
  help              Show this help message
  quit / exit       Exit pgtail
  !<command>        Run a shell command (e.g., '!ls -la')
  !                 Enter shell mode (next input runs as shell command)

Keyboard shortcuts:
  Tab       Autocomplete commands and arguments
  Up/Down   Navigate command history
  Ctrl+C    Stop current tail
  Ctrl+D    Exit pgtail
"""
    print(help_text.strip())


def clear_command() -> None:
    """Handle the 'clear' command - clear terminal screen."""
    os.system("cls" if sys.platform == "win32" else "clear")


def refresh_command(state: AppState) -> None:
    """Handle the 'refresh' command - re-scan for instances."""
    print("Scanning for PostgreSQL instances...")
    state.instances = detect_all()
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found.")
    elif count == 1:
        print("Found 1 PostgreSQL instance.")
    else:
        print(f"Found {count} PostgreSQL instances.")


def _find_instance(state: AppState, arg: str) -> Instance | None:
    """Find an instance by ID or path.

    Args:
        state: Current application state.
        arg: Instance ID (number) or data directory path.

    Returns:
        Instance if found, None otherwise.
    """
    # Try as numeric ID first
    try:
        instance_id = int(arg)
        for inst in state.instances:
            if inst.id == instance_id:
                return inst
        return None
    except ValueError:
        pass

    # Try as path
    path = Path(arg).resolve()
    for inst in state.instances:
        if inst.data_dir.resolve() == path:
            return inst

    return None


def tail_command(state: AppState, args: list[str]) -> None:
    """Handle the 'tail' command - tail logs for an instance.

    Args:
        state: Current application state.
        args: Command arguments (instance ID or path).
    """
    if not args:
        # If no arg given, use first instance or show error
        if not state.instances:
            print("No instances detected. Run 'refresh' to scan.")
            return
        if len(state.instances) == 1:
            instance = state.instances[0]
        else:
            print("Multiple instances found. Specify an ID:")
            print("  tail <id>")
            print()
            list_command(state)
            return
    else:
        instance = _find_instance(state, args[0])
        if instance is None:
            print(f"Instance not found: {args[0]}")
            print()
            print("Available instances:")
            for inst in state.instances:
                print(f"  {inst.id}: {inst.data_dir}")
            return

    if not instance.log_path:
        print(f"Logging not enabled for instance {instance.id}")
        print(f"Data directory: {instance.data_dir}")
        print()
        print("Enable logging with: enable-logging {instance.id}")
        return

    if not instance.log_path.exists():
        print(f"Log file not found: {instance.log_path}")
        return

    # Start tailing
    state.current_instance = instance
    state.tailing = True
    state.stop_event.clear()

    print(f"Tailing {instance.log_path}")
    print("Press Ctrl+C to stop")
    print()

    state.tailer = LogTailer(
        instance.log_path,
        state.active_levels,
        state.regex_state,
        state.time_filter if state.time_filter.is_active() else None,
    )
    state.tailer.start()


def stop_command(state: AppState) -> None:
    """Handle the 'stop' command - stop tailing."""
    if not state.tailing:
        print("Not currently tailing.")
        return

    if state.tailer:
        state.tailer.stop()
        # Keep tailer reference so buffer is available for export

    state.tailing = False
    state.stop_event.set()
    state.current_instance = None

    # Reset terminal state to prevent mangled output
    reset_terminal()
    print("Stopped tailing.")


def levels_command(state: AppState, args: list[str]) -> None:
    """Handle the 'levels' command - set or display log level filter.

    Args:
        state: Current application state.
        args: Level names to filter by, or empty to show current.
    """
    # No args - show current filter
    if not args:
        if state.active_levels is None:
            print("Filter: ALL (showing all levels)")
        else:
            names = sorted(level.name for level in state.active_levels)
            print(f"Filter: {' '.join(names)}")
        print()
        print("Usage: levels [LEVEL...]  Set filter to specific levels")
        print("       levels ALL         Show all levels")
        print()
        print(f"Available levels: {' '.join(LogLevel.names())}")
        return

    # Parse levels
    new_levels, invalid = parse_levels(args)

    # Report any invalid level names
    if invalid:
        print(f"Unknown level(s): {', '.join(invalid)}")
        print(f"Valid levels: {' '.join(LogLevel.names())}")
        return

    # Update filter
    state.active_levels = new_levels

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_levels(new_levels)

    # Confirm change
    if new_levels is None:
        print("Filter cleared - showing all levels")
    else:
        names = sorted(level.name for level in new_levels)
        print(f"Filter set: {' '.join(names)}")


def filter_command(state: AppState, args: list[str]) -> None:
    """Handle the 'filter' command - set or display regex pattern filter.

    Args:
        state: Current application state.
        args: Filter pattern or subcommand.
    """
    import re

    # No args - show current filter status
    if not args:
        if not state.regex_state.has_filters():
            print("No filters active")
        else:
            print("Active filters:")
            for f in state.regex_state.includes:
                cs = " (case-sensitive)" if f.case_sensitive else ""
                print(f"  include: /{f.pattern}/{cs}")
            for f in state.regex_state.excludes:
                cs = " (case-sensitive)" if f.case_sensitive else ""
                print(f"  exclude: /{f.pattern}/{cs}")
            for f in state.regex_state.ands:
                cs = " (case-sensitive)" if f.case_sensitive else ""
                print(f"  and: /{f.pattern}/{cs}")
        print()
        print("Usage: filter /pattern/       Include only matching lines")
        print("       filter -/pattern/      Exclude matching lines")
        print("       filter +/pattern/      Add OR pattern")
        print("       filter &/pattern/      Add AND pattern")
        print("       filter /pattern/c      Case-sensitive match")
        print("       filter clear           Clear all filters")
        return

    arg = args[0]

    # Handle 'clear' subcommand
    if arg.lower() == "clear":
        state.regex_state.clear_filters()
        print("Filters cleared")
        return

    # Determine filter type based on prefix
    if arg.startswith("-/"):
        filter_type = FilterType.EXCLUDE
        pattern_arg = arg[1:]  # Remove '-' prefix, keep the /pattern/
    elif arg.startswith("+/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg[1:]  # Remove '+' prefix
    elif arg.startswith("&/"):
        filter_type = FilterType.AND
        pattern_arg = arg[1:]  # Remove '&' prefix
    elif arg.startswith("/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg
    else:
        print(f"Invalid filter syntax: {arg}")
        print("Use /pattern/ syntax (e.g., filter /error/)")
        return

    # Parse the pattern
    try:
        pattern, case_sensitive = parse_filter_arg(pattern_arg)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Validate regex
    try:
        regex_filter = RegexFilter.create(pattern, filter_type, case_sensitive)
    except re.error as e:
        print(f"Invalid regex pattern: {e}")
        return

    # Apply the filter
    if filter_type == FilterType.INCLUDE and arg.startswith("/"):
        # Plain /pattern/ sets single include filter (replaces previous includes)
        state.regex_state.set_include(regex_filter)
        cs = " (case-sensitive)" if case_sensitive else ""
        print(f"Filter set: /{pattern}/{cs}")
    else:
        # +, -, & add to existing filters
        state.regex_state.add_filter(regex_filter)
        type_label = filter_type.value
        cs = " (case-sensitive)" if case_sensitive else ""
        print(f"Filter added ({type_label}): /{pattern}/{cs}")

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_regex_state(state.regex_state)


def highlight_command(state: AppState, args: list[str]) -> None:
    """Handle the 'highlight' command - set or display text highlights.

    Args:
        state: Current application state.
        args: Highlight pattern or subcommand.
    """
    import re

    # No args - show current highlight status
    if not args:
        if not state.regex_state.has_highlights():
            print("No highlights active")
        else:
            print("Active highlights:")
            for h in state.regex_state.highlights:
                cs = " (case-sensitive)" if h.case_sensitive else ""
                print(f"  /{h.pattern}/{cs}")
        print()
        print("Usage: highlight /pattern/   Highlight matching text (yellow background)")
        print("       highlight /pattern/c  Case-sensitive highlight")
        print("       highlight clear       Clear all highlights")
        return

    arg = args[0]

    # Handle 'clear' subcommand
    if arg.lower() == "clear":
        state.regex_state.clear_highlights()
        print("Highlights cleared")
        return

    # Parse the pattern
    if not arg.startswith("/"):
        print(f"Invalid highlight syntax: {arg}")
        print("Use /pattern/ syntax (e.g., highlight /error/)")
        return

    try:
        pattern, case_sensitive = parse_filter_arg(arg)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Validate regex
    try:
        highlight = Highlight.create(pattern, case_sensitive)
    except re.error as e:
        print(f"Invalid regex pattern: {e}")
        return

    # Add the highlight
    state.regex_state.highlights.append(highlight)
    cs = " (case-sensitive)" if case_sensitive else ""
    print(f"Highlight added: /{pattern}/{cs}")

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_regex_state(state.regex_state)


def slow_command(state: AppState, args: list[str]) -> None:
    """Handle the 'slow' command - configure slow query highlighting.

    Args:
        state: Current application state.
        args: Command arguments:
            - No args: Display current configuration
            - 'off': Disable slow query highlighting
            - Three numbers: Set warning/slow/critical thresholds in ms
    """
    # T023: No args - display current configuration
    if not args:
        if state.slow_query_config.enabled:
            print("Slow query highlighting: ENABLED")
            print()
            print("Thresholds:")
            print(state.slow_query_config.format_thresholds())
        else:
            print("Slow query highlighting: DISABLED")
            print()
            print("Usage:")
            print("  slow <warning> <slow> <critical>  Enable with thresholds (in ms)")
            print("  slow off                          Disable highlighting")
            print()
            print("Example: slow 100 500 1000")
        return

    # T024: Handle 'off' subcommand
    if args[0].lower() == "off":
        state.slow_query_config.enabled = False
        print("Slow query highlighting disabled")
        return

    # T022, T025: Three numeric arguments - set custom thresholds
    if len(args) != 3:
        print("Error: Expected 3 threshold values or 'off'")
        print("Usage: slow <warning> <slow> <critical>")
        print("Example: slow 100 500 1000")
        return

    # Parse threshold values
    try:
        warning = float(args[0])
        slow = float(args[1])
        critical = float(args[2])
    except ValueError:
        print("Error: Thresholds must be numbers")
        print("Usage: slow <warning> <slow> <critical>")
        print("Example: slow 100 500 1000")
        return

    # Validate thresholds
    error = validate_thresholds(warning, slow, critical)
    if error:
        print(f"Error: {error}")
        return

    # Apply new configuration
    state.slow_query_config = SlowQueryConfig(
        enabled=True,
        warning_ms=warning,
        slow_ms=slow,
        critical_ms=critical,
    )

    print("Slow query highlighting enabled")
    print()
    print("Thresholds:")
    print(state.slow_query_config.format_thresholds())
    print()
    print("Note: PostgreSQL must have log_min_duration_statement enabled to log query durations.")
    if state.current_instance and state.current_instance.port:
        port = state.current_instance.port
        print(
            f'  psql -p {port} -c "ALTER SYSTEM SET log_min_duration_statement = 0; SELECT pg_reload_conf();"'
        )
    else:
        print(
            '  psql -p <port> -c "ALTER SYSTEM SET log_min_duration_statement = 0; SELECT pg_reload_conf();"'
        )
        print("  (Use 'list' to see instance ports)")


def stats_command(state: AppState) -> None:
    """Handle the 'stats' command - display query duration statistics.

    Args:
        state: Current application state.
    """
    # T034: Handle empty stats
    if state.duration_stats.is_empty():
        print("No query duration data collected yet.")
        print()
        print("Duration statistics are collected automatically while tailing logs.")
        print("PostgreSQL must have log_min_duration_statement enabled to log query durations.")
        return

    # T033: Display statistics summary
    print(state.duration_stats.format_summary())


def set_command(state: AppState, args: list[str]) -> None:
    """Handle the 'set' command - set or display a config value.

    Args:
        state: Current application state.
        args: Command arguments: [key] or [key, value...].
    """
    # No args - show usage
    if not args:
        print("Usage: set <key> [value]")
        print()
        print("Available settings:")
        for key in SETTINGS_SCHEMA:
            default = get_default_value(key)
            print(f"  {key} (default: {default!r})")
        return

    key = args[0]

    # Validate key
    if not validate_key(key):
        print(f"Unknown setting: {key}")
        print()
        print("Available settings:")
        for k in SETTINGS_SCHEMA:
            print(f"  {k}")
        return

    # No value - display current value (T019)
    if len(args) == 1:
        # Get current value from config
        parts = key.split(".")
        section = getattr(state.config, parts[0])
        current = getattr(section, parts[1])
        default = get_default_value(key)
        print(f"{key} = {current!r}")
        if current != default:
            print(f"  (default: {default!r})")
        return

    # Parse and validate value (T018, T020)
    raw_value = args[1:]
    try:
        value = parse_value(key, raw_value if len(raw_value) > 1 else raw_value[0])
    except ValueError as e:
        print(f"Invalid value for {key}: {e}")
        return

    # Validate the value using schema validator
    _, validator, _ = SETTINGS_SCHEMA[key]
    try:
        validated = validator(value)
    except ValueError as e:
        print(f"Invalid value for {key}: {e}")
        return

    # Save to config file (T021 - creates file/dirs if needed)
    if not save_config(key, validated, warn_func=_warn):
        print("Failed to save configuration")
        return

    # Update in-memory config
    parts = key.split(".")
    section = getattr(state.config, parts[0])
    setattr(section, parts[1], validated)

    # Apply changes immediately (T022)
    _apply_setting(state, key)

    print(f"{key} = {validated!r}")
    print(f"Saved to {get_config_path()}")


def unset_command(state: AppState, args: list[str]) -> None:
    """Handle the 'unset' command - remove a config setting.

    Args:
        state: Current application state.
        args: Command arguments: [key].
    """
    # T042: No args - show usage
    if not args:
        print("Usage: unset <key>")
        print()
        print("Remove a setting to revert to its default value.")
        print()
        print("Available settings:")
        for key in SETTINGS_SCHEMA:
            default = get_default_value(key)
            print(f"  {key} (default: {default!r})")
        return

    key = args[0]

    # T043: Validate key exists in schema
    if not validate_key(key):
        print(f"Unknown setting: {key}")
        print()
        print("Available settings:")
        for k in SETTINGS_SCHEMA:
            print(f"  {k}")
        return

    # Get default value for confirmation message
    default = get_default_value(key)

    # T044: Remove key from config file
    config_path = get_config_path()
    if config_path.exists():
        deleted = delete_config_key(key, warn_func=_warn)
        if not deleted:
            print(f"{key} is not set in config file.")
            print(f"Current value is already the default: {default!r}")
            return
    else:
        print(f"{key} is not set (no config file exists).")
        print(f"Already using default: {default!r}")
        return

    # T045: Revert in-memory value to default and apply
    parts = key.split(".")
    section = getattr(state.config, parts[0])
    setattr(section, parts[1], default)
    _apply_setting(state, key)

    # T046: Show confirmation with default value
    print(f"{key} reset to default: {default!r}")


def _apply_setting(state: AppState, key: str) -> None:
    """Apply a single setting change to runtime state.

    Args:
        state: Current application state.
        key: The setting key that was changed.
    """
    import contextlib

    if key == "default.levels":
        levels = state.config.default.levels
        if not levels:
            state.active_levels = LogLevel.all_levels()
        else:
            valid_levels: set[LogLevel] = set()
            for level_name in levels:
                with contextlib.suppress(ValueError):
                    valid_levels.add(LogLevel.from_string(level_name))
            state.active_levels = valid_levels if valid_levels else LogLevel.all_levels()
        # Update tailer if tailing
        if state.tailer:
            state.tailer.update_levels(state.active_levels)
    elif key.startswith("slow."):
        state.slow_query_config = SlowQueryConfig(
            enabled=True,
            warning_ms=state.config.slow.warn,
            slow_ms=state.config.slow.error,
            critical_ms=state.config.slow.critical,
        )


def config_command(state: AppState, args: list[str]) -> None:
    """Handle the 'config' command - display or manage configuration.

    Args:
        state: Current application state.
        args: Subcommand (path, edit, reset) or empty to show config.
    """
    # Handle subcommands
    if args:
        subcommand = args[0].lower()
        if subcommand == "path":
            config_path_command()
            return
        elif subcommand == "edit":
            config_edit_command(state)
            return
        elif subcommand == "reset":
            config_reset_command(state)
            return
        else:
            print(f"Unknown subcommand: {subcommand}")
            print("Available: path, edit, reset")
            return

    # No subcommand - display current configuration (T025, T026, T027)
    config_path = get_config_path()
    file_exists = config_path.exists()

    # Header with file path
    if file_exists:
        print(f"# Config file: {config_path}")
    else:
        print(f"# Config file: {config_path} (not created yet)")
        print("# Showing default values")
    print()

    # Format as TOML-like output
    print("[default]")
    levels = state.config.default.levels
    print(f"levels = {levels!r}")
    print(f"follow = {str(state.config.default.follow).lower()}")
    print()

    print("[slow]")
    print(f"warn = {state.config.slow.warn}")
    print(f"error = {state.config.slow.error}")
    print(f"critical = {state.config.slow.critical}")
    print()

    print("[display]")
    print(f'timestamp_format = "{state.config.display.timestamp_format}"')
    print(f"show_pid = {str(state.config.display.show_pid).lower()}")
    print(f"show_level = {str(state.config.display.show_level).lower()}")
    print()

    print("[theme]")
    print(f'name = "{state.config.theme.name}"')
    print()

    print("[notifications]")
    print(f"enabled = {str(state.config.notifications.enabled).lower()}")
    print(f"levels = {state.config.notifications.levels!r}")
    if state.config.notifications.quiet_hours:
        print(f'quiet_hours = "{state.config.notifications.quiet_hours}"')
    else:
        print('# quiet_hours = "22:00-08:00"')


def config_path_command() -> None:
    """Handle the 'config path' command - show config file location (T028)."""
    config_path = get_config_path()
    print(config_path)
    if config_path.exists():
        print("  (file exists)")
    else:
        print("  (file not created yet - use 'set' to create)")


def config_edit_command(state: AppState) -> None:
    """Handle the 'config edit' command - open config in $EDITOR (T029-T033).

    Args:
        state: Current application state.
    """
    # T030: Check $EDITOR environment variable
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        print("No editor configured.")
        print()
        print("Set the EDITOR environment variable:")
        print("  export EDITOR=vim")
        print("  export EDITOR=nano")
        print("  export EDITOR='code --wait'")
        print()
        print(f"Or edit directly: {get_config_path()}")
        return

    config_path = get_config_path()

    # T031: Create config file with template if it doesn't exist
    if not config_path.exists():
        print(f"Creating config file: {config_path}")
        if not create_default_config():
            print("Error: Could not create config file")
            return

    # T032: Open editor and wait for exit
    print(f"Opening {config_path} in {editor}...")
    try:
        # Use shell=True to handle editors with arguments like "code --wait"
        result = subprocess.run(
            f'{editor} "{config_path}"',
            shell=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"Editor exited with code {result.returncode}")
    except Exception as e:
        print(f"Error launching editor: {e}")
        return

    # T033: Reload config after editor closes
    print("Reloading configuration...")
    state.config = load_config(warn_func=_warn)
    state._apply_config()
    print("Configuration reloaded.")


def config_reset_command(state: AppState) -> None:
    """Handle the 'config reset' command - reset to defaults with backup (T034-T039).

    Args:
        state: Current application state.
    """
    config_path = get_config_path()

    # T035: Check if config file exists
    if not config_path.exists():
        print("No config file to reset.")
        print(f"Config path: {config_path}")
        print()
        print("Already using default settings.")
        return

    # T036, T037: Create backup and delete original (handled by reset_config)
    backup_path = reset_config(warn_func=_warn)

    if backup_path is None:
        print("Error: Could not reset config file")
        return

    # T038: Reset in-memory config to defaults
    state.config = ConfigSchema()
    state._apply_config()

    # T039: Display confirmation
    print("Configuration reset to defaults.")
    print()
    print(f"Backup saved: {backup_path}")


def enable_logging_command(state: AppState, args: list[str]) -> None:
    """Handle the 'enable-logging' command - enable logging_collector for an instance.

    Args:
        state: Current application state.
        args: Instance ID or path.
    """
    if not args:
        print("Usage: enable-logging <id|path>")
        print()
        print("Enables logging_collector in postgresql.conf")
        print("After running, you must restart PostgreSQL for changes to take effect.")
        return

    instance = _find_instance(state, args[0])
    if instance is None:
        print(f"Instance not found: {args[0]}")
        print()
        print("Available instances:")
        for inst in state.instances:
            print(f"  {inst.id}: {inst.data_dir}")
        return

    # Check if logging is already enabled
    if instance.log_path and instance.log_path.exists():
        print(f"Logging is already enabled for instance {instance.id}")
        print(f"Log file: {instance.log_path}")
        return

    print(f"Enabling logging for instance {instance.id}...")
    print(f"Data directory: {instance.data_dir}")
    print()

    result = enable_logging(instance.data_dir)

    if result.changes:
        print("Changes made:")
        for change in result.changes:
            print(f"  • {change}")
        print()

    if result.success:
        print(result.message)
        print()
        print("⚠️  PostgreSQL must be restarted for changes to take effect:")
        if instance.running:
            print(f"    pg_ctl restart -D {instance.data_dir}")
        else:
            print(f"    pg_ctl start -D {instance.data_dir}")
        print()
        print("After restarting, run 'refresh' to update instance list.")
    else:
        print(f"Error: {result.message}")


def export_command(state: AppState, args: list[str]) -> None:
    """Handle the 'export' command - export filtered logs to a file.

    Args:
        state: Current application state.
        args: Command arguments (filename, options).
    """
    # Check if we have a tailer with entries
    if not state.tailer:
        print("No log file loaded. Use 'tail <instance>' first.")
        return

    # Parse arguments: export [--append] [--format fmt] [--since time] [--follow] <filename>
    append = False
    follow = False
    fmt = ExportFormat.TEXT
    since = None
    filename = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--append":
            append = True
            i += 1
        elif arg == "--follow":
            follow = True
            i += 1
        elif arg == "--format" and i + 1 < len(args):
            try:
                fmt = ExportFormat.from_string(args[i + 1])
            except ValueError as e:
                print(f"Error: {e}")
                return
            i += 2
        elif arg == "--since" and i + 1 < len(args):
            try:
                since = parse_since(args[i + 1])
            except ValueError as e:
                print(f"Error: {e}")
                return
            i += 2
        elif arg.startswith("--"):
            print(f"Unknown option: {arg}")
            return
        else:
            filename = arg
            i += 1

    if not filename:
        print("Usage: export [options] <filename>")
        print()
        print("Export filtered log entries to a file.")
        print()
        print("Options:")
        print("  --append         Append to existing file")
        print("  --format <fmt>   Output format (text, json, csv)")
        print("  --since <time>   Only entries after time (e.g., 1h, 30m, 2d)")
        print("  --follow         Continuous export (like tail -f | tee)")
        return

    # Validate options
    if follow and append:
        print("Error: Cannot use --follow with --append")
        return

    if follow and since:
        print("Error: Cannot use --follow with --since")
        return

    path = Path(filename)

    # Confirm overwrite if file exists and not appending
    if not append and not confirm_overwrite(path):
        print("Export cancelled.")
        return

    # Handle follow mode
    if follow:
        _export_follow_mode(state, path, fmt)
        return

    # Get filtered entries from the tailer's buffer
    entries = get_filtered_entries(
        state.tailer.get_buffer(),
        state.active_levels,
        state.regex_state,
        since,
    )

    # Export to file
    try:
        count = export_to_file(entries, path, fmt, append)
        if count == 0:
            print("No entries to export (buffer is empty or all filtered out).")
        else:
            print(f"Exported {count} entries to {path}")
    except PermissionError:
        print(f"Error: Permission denied: {path}")
        print("Try a different location or check permissions.")
    except OSError as e:
        print(f"Error writing to file: {e}")


def _export_follow_mode(state: AppState, path: Path, fmt: ExportFormat) -> None:
    """Handle continuous export mode (--follow).

    Args:
        state: Current application state.
        path: Output file path.
        fmt: Output format.
    """
    # Restart tailer if it was stopped
    if not state.tailer.is_running:
        state.tailer.start()

    print(f"Exporting to {path} (Ctrl+C to stop)")
    print()

    count = follow_export(
        state.tailer,
        path,
        fmt,
        state.active_levels,
        state.regex_state,
        on_entry=print_log_entry,  # Tee behavior - display on screen
    )

    print()
    print(f"Exported {count} entries to {path}")


def pipe_command(state: AppState, args: list[str]) -> None:
    """Handle the 'pipe' command - pipe filtered logs to an external command.

    Args:
        state: Current application state.
        args: Command arguments (format option, command).
    """
    # Check if we have a tailer with entries
    if not state.tailer:
        print("No log file loaded. Use 'tail <instance>' first.")
        return

    # Parse arguments: pipe [--format fmt] <command...>
    fmt = ExportFormat.TEXT
    command_start = 0

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--format" and i + 1 < len(args):
            try:
                fmt = ExportFormat.from_string(args[i + 1])
            except ValueError as e:
                print(f"Error: {e}")
                return
            i += 2
            command_start = i
        elif arg.startswith("--"):
            print(f"Unknown option: {arg}")
            return
        else:
            # First non-option arg starts the command
            command_start = i
            break

    # Join remaining args as the command
    command_args = args[command_start:]
    if not command_args:
        print("Usage: pipe [--format text|json|csv] <command...>")
        print()
        print("Pipe filtered log entries to an external command.")
        print()
        print("Options:")
        print("  --format <fmt>   Output format (text, json, csv)")
        print()
        print("Examples:")
        print("  pipe wc -l              Count filtered entries")
        print("  pipe grep ERROR         Search for ERROR in entries")
        print("  pipe --format json jq   Process JSON with jq")
        return

    command = " ".join(command_args)

    # Get filtered entries from the tailer's buffer
    entries = get_filtered_entries(
        state.tailer.get_buffer(),
        state.active_levels,
        state.regex_state,
    )

    # Pipe to command
    try:
        result = pipe_to_command(entries, command, fmt)

        # Display stdout if any
        if result.stdout:
            print(result.stdout.rstrip())

        # Display stderr if any
        if result.stderr:
            print(f"stderr: {result.stderr.rstrip()}")

        # Report non-zero exit code
        if result.returncode != 0:
            print(f"Command exited with code {result.returncode}")
    except FileNotFoundError:
        cmd_name = command.split()[0]
        print(f"Error: Command not found: {cmd_name}")
    except OSError as e:
        print(f"Error running command: {e}")


def since_command(state: AppState, args: list[str]) -> None:
    """Handle the 'since' command - filter logs by time.

    Args:
        state: Current application state.
        args: Command arguments:
            - No args: Display current time filter status
            - 'clear': Remove time filter
            - Time value: Set filter (e.g., 5m, 2h, 14:30, 2024-01-15T14:30)
    """
    # No args - show current time filter status
    if not args:
        if not state.time_filter.is_active():
            print("No time filter active")
        else:
            print(f"Time filter: {state.time_filter.format_description()}")
        print()
        print("Usage: since <time>     Show logs since time")
        print("       since clear      Remove time filter")
        print()
        print("Time formats:")
        print("  5m, 30s, 2h, 1d       Relative (from now)")
        print("  14:30, 14:30:45       Time today")
        print("  2024-01-15T14:30      ISO 8601 datetime")
        return

    arg = args[0].lower()

    # Handle 'clear' subcommand
    if arg == "clear":
        state.time_filter = TimeFilter.empty()
        if state.tailer:
            state.tailer.update_time_filter(None)
        print("Time filter cleared")
        return

    # Parse time value
    try:
        since_time = parse_time(args[0])
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Warn if time is in the future
    if is_future_time(since_time):
        print(f"Warning: {args[0]} is in the future, no entries will match yet")

    # Create and apply time filter
    state.time_filter = TimeFilter(since=since_time, original_input=args[0])

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_time_filter(state.time_filter)

    # Display feedback
    print(f"Showing logs {state.time_filter.format_description()}")


def between_command(state: AppState, args: list[str]) -> None:
    """Handle the 'between' command - filter logs in a time range.

    Args:
        state: Current application state.
        args: Command arguments:
            - No args: Display usage
            - Two time values: Set filter for start to end range
    """
    # Skip "and" if present (e.g., "between 14:30 and 15:00")
    if len(args) >= 2 and args[1].lower() == "and":
        args = [args[0]] + args[2:]

    # No args or not enough args - show usage
    if len(args) < 2:
        if state.time_filter.is_active():
            print(f"Time filter: {state.time_filter.format_description()}")
            print()
        print("Usage: between <start> <end>")
        print()
        print("Time formats:")
        print("  5m, 30s, 2h, 1d       Relative (from now)")
        print("  14:30, 14:30:45       Time today")
        print("  2024-01-15T14:30      ISO 8601 datetime")
        print()
        print("Example: between 14:30 15:00")
        return

    # Parse start time
    try:
        start_time = parse_time(args[0])
    except ValueError as e:
        print(f"Error parsing start time: {e}")
        return

    # Parse end time
    try:
        end_time = parse_time(args[1])
    except ValueError as e:
        print(f"Error parsing end time: {e}")
        return

    # Validate start < end
    if start_time >= end_time:
        print("Error: Start time must be before end time")
        print(f"  Start: {start_time.strftime('%H:%M:%S')}")
        print(f"  End:   {end_time.strftime('%H:%M:%S')}")
        return

    # Create and apply time filter
    original = f"{args[0]} {args[1]}"
    state.time_filter = TimeFilter(since=start_time, until=end_time, original_input=original)

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_time_filter(state.time_filter)

    # Display feedback
    print(f"Showing logs {state.time_filter.format_description()}")


def handle_command(state: AppState, line: str) -> bool:
    """Process a command line and execute the appropriate handler.

    Args:
        state: Current application state.
        line: The command line to process.

    Returns:
        True to continue the REPL loop, False to exit.
    """
    line = line.strip()

    # Handle empty input
    if not line:
        state.shell_mode = False
        return True

    # Handle shell mode
    if state.shell_mode:
        state.shell_mode = False
        run_shell(line)
        return True

    # Handle ! prefix for shell commands
    if line.startswith("!"):
        cmd_line = line[1:].strip()
        if cmd_line:
            # !command - run immediately
            run_shell(cmd_line)
        else:
            # ! alone - enter shell mode
            state.shell_mode = True
        return True

    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ("quit", "exit", "q"):
        # Stop tailing before exit
        if state.tailing:
            stop_command(state)
        return False
    elif cmd == "list":
        list_command(state)
    elif cmd == "help":
        help_command()
    elif cmd == "clear":
        clear_command()
    elif cmd == "refresh":
        refresh_command(state)
    elif cmd == "tail":
        tail_command(state, args)
    elif cmd == "levels":
        levels_command(state, args)
    elif cmd == "filter":
        filter_command(state, args)
    elif cmd == "highlight":
        highlight_command(state, args)
    elif cmd == "slow":
        slow_command(state, args)
    elif cmd == "stats":
        stats_command(state)
    elif cmd == "set":
        set_command(state, args)
    elif cmd == "unset":
        unset_command(state, args)
    elif cmd == "config":
        config_command(state, args)
    elif cmd == "stop":
        stop_command(state)
    elif cmd == "enable-logging":
        enable_logging_command(state, args)
    elif cmd == "export":
        export_command(state, args)
    elif cmd == "pipe":
        pipe_command(state, args)
    elif cmd == "since":
        since_command(state, args)
    elif cmd == "between":
        between_command(state, args)
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands.")

    return True


def _get_prompt(state: AppState) -> HTML:
    """Get the prompt string based on current state."""
    if state.shell_mode:
        return HTML("<style fg='#ff6688'>!</style> ")
    if state.tailing and state.current_instance:
        return HTML(
            f"<style fg='#00aa00'>tailing</style> <style fg='#00aaaa'>[{state.current_instance.id}]</style><style fg='#666666'>&gt;</style> "
        )
    return HTML("<style fg='#00aa00'>pgtail</style><style fg='#666666'>&gt;</style> ")


def _process_tail_output(state: AppState) -> None:
    """Process pending tail output and print entries."""
    if not state.tailer:
        return

    # Process all available entries
    while True:
        entry = state.tailer.get_entry(timeout=0.01)
        if entry is None:
            break

        # Extract duration for slow query detection and stats collection
        duration_ms = extract_duration(entry.message)

        # Collect duration stats (T016)
        if duration_ms is not None:
            state.duration_stats.add(duration_ms)

        # Check for slow query highlighting first (T014, T015 - slow query takes precedence)
        if state.slow_query_config.enabled and duration_ms is not None:
            slow_level = state.slow_query_config.get_level(duration_ms)
            if slow_level is not None:
                # Slow query highlighting completely replaces regex highlighting
                formatted = format_slow_query_entry(entry, slow_level)
                print_formatted_text(formatted, style=LOG_STYLE)
                continue

        # Fall back to regex highlighting
        if state.regex_state.has_highlights():
            # Collect all highlight spans from all highlight patterns
            all_spans: list[tuple[int, int]] = []
            for h in state.regex_state.highlights:
                all_spans.extend(h.find_spans(entry.message))

            if all_spans:
                formatted = format_log_entry_with_highlights(entry, all_spans)
                print_formatted_text(formatted, style=LOG_STYLE)
            else:
                print_log_entry(entry)
        else:
            print_log_entry(entry)


def _create_key_bindings(state: AppState) -> KeyBindings:
    """Create key bindings for the REPL.

    Args:
        state: Application state (captured in closure).

    Returns:
        KeyBindings instance with shell mode handling.
    """
    bindings = KeyBindings()

    @bindings.add("!")
    def handle_exclamation(event: object) -> None:
        """Handle ! key - enter shell mode if buffer is empty."""
        app = event.app  # type: ignore[attr-defined]
        buf = app.current_buffer
        if buf.text == "":
            state.shell_mode = True
            app.invalidate()  # Force prompt refresh
        else:
            buf.insert_text("!")

    @bindings.add("escape")
    def handle_escape(event: object) -> None:
        """Handle Escape key - exit shell mode."""
        state.shell_mode = False
        event.app.invalidate()  # type: ignore[attr-defined]

    @bindings.add("backspace")
    def handle_backspace(event: object) -> None:
        """Handle Backspace - exit shell mode if buffer empty."""
        app = event.app  # type: ignore[attr-defined]
        buf = app.current_buffer
        if state.shell_mode and buf.text == "":
            state.shell_mode = False
            app.invalidate()  # Force prompt refresh
        elif buf.text:
            buf.delete_before_cursor(1)

    return bindings


def main() -> None:
    """Main entry point for pgtail."""
    # Enable VT100 mode for colors on Windows
    enable_vt100_mode()

    print("pgtail - PostgreSQL log tailer")
    print()

    # Initialize state with detected instances
    state = AppState()
    state.instances = detect_all()

    # Show instance count on startup
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found. Use 'refresh' to scan again.")
    elif count == 1:
        print("Found 1 PostgreSQL instance. Type 'list' to see details.")
    else:
        print(f"Found {count} PostgreSQL instances. Type 'list' to see details.")

    print("Type 'help' for available commands, 'quit' to exit.")
    print()

    # Set up prompt session with history, key bindings, and completer
    history_path = ensure_history_dir()
    bindings = _create_key_bindings(state)
    completer = PgtailCompleter(get_instances=lambda: state.instances)
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        completer=completer,
    )

    # REPL loop
    while True:
        try:
            # When tailing, process output in a loop until Ctrl+C
            if state.tailing:
                try:
                    while state.tailing:
                        _process_tail_output(state)
                except KeyboardInterrupt:
                    # Ctrl+C stops tailing
                    print()
                    stop_command(state)
                    continue

            line = session.prompt(lambda: _get_prompt(state))
            if not handle_command(state, line):
                break
        except KeyboardInterrupt:
            # Ctrl+C - if tailing, stop; otherwise ignore
            print()
            if state.tailing:
                stop_command(state)
            continue
        except EOFError:
            # Ctrl+D - exit
            print()
            if state.tailing:
                stop_command(state)
            break

    print("Goodbye!")
