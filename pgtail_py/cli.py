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
from pgtail_py.config import ensure_history_dir, get_history_path
from pgtail_py.detector import detect_all
from pgtail_py.enable_logging import enable_logging
from pgtail_py.filter import LogLevel, parse_levels
from pgtail_py.instance import Instance
from pgtail_py.regex_filter import (
    FilterState,
    FilterType,
    Highlight,
    RegexFilter,
    parse_filter_arg,
)
from pgtail_py.slow_query import DurationStats, SlowQueryConfig, extract_duration
from pgtail_py.tailer import LogTailer
from pgtail_py.terminal import enable_vt100_mode, reset_terminal


@dataclass
class AppState:
    """Runtime state for the REPL session.

    Attributes:
        instances: List of detected PostgreSQL instances
        current_instance: Currently selected instance for tailing
        active_levels: Set of log levels to display (all by default)
        regex_state: Regex pattern filter state
        slow_query_config: Configuration for slow query highlighting
        duration_stats: Session-scoped query duration statistics
        tailing: Whether actively tailing a log file
        history_path: Path to command history file
        tailer: Active log tailer instance
        stop_event: Event to signal tail stop
        shell_mode: Whether in shell mode (next input runs as shell command)
    """

    instances: list[Instance] = field(default_factory=list)
    current_instance: Instance | None = None
    active_levels: set[LogLevel] = field(default_factory=LogLevel.all_levels)
    regex_state: FilterState = field(default_factory=FilterState.empty)
    slow_query_config: SlowQueryConfig = field(default_factory=SlowQueryConfig)
    duration_stats: DurationStats = field(default_factory=DurationStats)
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)
    tailer: LogTailer | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    shell_mode: bool = False


def _shorten_path(path: Path) -> str:
    """Replace home directory with ~ for display."""
    home = Path.home()
    path_str = str(path)
    home_str = str(home)
    if path_str.startswith(home_str):
        return "~" + path_str[len(home_str):]
    return path_str


def run_shell(cmd_line: str) -> None:
    """Run a shell command.

    Args:
        cmd_line: The command to run.
    """
    if not cmd_line:
        return

    if sys.platform == "win32":
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

    state.tailer = LogTailer(instance.log_path, state.active_levels, state.regex_state)
    state.tailer.start()


def stop_command(state: AppState) -> None:
    """Handle the 'stop' command - stop tailing."""
    if not state.tailing:
        print("Not currently tailing.")
        return

    if state.tailer:
        state.tailer.stop()
        state.tailer = None

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
    elif cmd == "stop":
        stop_command(state)
    elif cmd == "enable-logging":
        enable_logging_command(state, args)
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands.")

    return True


def _get_prompt(state: AppState) -> HTML:
    """Get the prompt string based on current state."""
    if state.shell_mode:
        return HTML("<style fg='#ff6688'>!</style> ")
    if state.tailing and state.current_instance:
        return HTML(f"<style fg='#00aa00'>tailing</style> <style fg='#00aaaa'>[{state.current_instance.id}]</style><style fg='#666666'>&gt;</style> ")
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
