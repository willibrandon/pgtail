"""Core CLI commands for instance management and navigation."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pgtail_py.cli_utils import find_instance, shorten_path, validate_file_path, validate_tail_args
from pgtail_py.detector import detect_all
from pgtail_py.display import get_valid_display_fields
from pgtail_py.format_detector import LogFormat
from pgtail_py.tailer import LogTailer
from pgtail_py.terminal import reset_terminal
from pgtail_py.time_filter import TimeFilter, parse_time

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance
    from pgtail_py.parser import LogEntry


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
        data_dir = shorten_path(inst.data_dir)
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
                    --file <path>  Tail an arbitrary log file
                    -f <path>      Short form of --file
  levels [LEVEL...] Set log level filter (e.g., 'levels ERROR WARNING')
                    With no args, shows current filter settings
                    Use 'levels ALL' to show all levels
  filter /pattern/  Filter logs by regex pattern
                    -/pattern/  Exclude matching lines
                    +/pattern/  Add OR pattern
                    &/pattern/  Add AND pattern
                    /pattern/c  Case-sensitive match
                    field=value Filter by field (CSV/JSON only)
                    clear       Clear all filters
  highlight /pattern/  Highlight matching text (yellow background)
                    /pattern/c  Case-sensitive highlight
                    clear       Clear all highlights
  since <time>      Filter logs since time (e.g., 'since 5m', 'since 14:30')
                    clear       Remove time filter
  until <time>      Filter logs until time (e.g., 'until 15:00')
                    Disables live tailing (upper bound set)
  between <s> <e>   Filter logs in time range (e.g., 'between 14:30 15:00')
  display [mode]    Control display mode for log entries
                    compact   Single line (default)
                    full      All available fields with labels
                    fields <f1,f2,...>  Show only specified fields
  output [format]   Control output format
                    json      Output as JSON (one object per line)
                    text      Output as colored text (default)
  slow [w s c]      Configure slow query highlighting (thresholds in ms)
                    With no args, shows current settings
                    'slow off' disables highlighting
  stats             Show query duration statistics
  errors            Show error statistics
                    --trend     Show error rate sparkline
                    --live      Live updating counter
                    --code CODE Filter by SQLSTATE code
                    --since TIME Filter by time window
                    clear       Reset statistics
  connections       Show connection statistics
                    --history   Show connection trends over time
                    --watch     Live stream of connection events
                    --db=NAME   Filter by database name
                    --user=NAME Filter by user name
                    --app=NAME  Filter by application name
                    clear       Reset statistics
  notify            Configure desktop notifications
                    on LEVEL... Enable for log levels (FATAL, PANIC, etc.)
                    on /pattern/  Enable for regex pattern matches
                    off         Disable all notifications
                    test        Send a test notification
                    quiet HH:MM-HH:MM  Set quiet hours
                    quiet off   Disable quiet hours
                    clear       Remove all notification rules
  theme [name]      Switch color theme (e.g., 'theme light', 'theme monokai')
                    list        Show all available themes
                    preview <n> Preview a theme without switching
                    edit <name> Create or edit a custom theme
                    reload      Reload current theme from disk
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


def tail_command(state: AppState, args: list[str]) -> None:
    """Handle the 'tail' command - tail logs for an instance or file.

    By default, launches the status bar tail mode with split-screen interface.
    Use --stream for legacy streaming mode.

    Supports glob patterns: tail --file "*.log"
    Supports multiple files: tail --file a.log --file b.log

    Args:
        state: Current application state.
        args: Command arguments (instance ID/path, --file <path>, --since/--stream flags).
    """
    from pgtail_py.multi_tailer import GlobPattern, is_glob_pattern

    # Parse flags from arguments
    since_time = None
    stream_mode = False
    file_paths: list[str] = []  # Support multiple --file arguments
    instance_arg = None
    i = 0
    while i < len(args):
        if args[i] == "--since" and i + 1 < len(args):
            try:
                since_time = parse_time(args[i + 1])
            except ValueError as e:
                print(f"Error parsing --since time: {e}")
                return
            i += 2
        elif args[i] == "--stream":
            stream_mode = True
            i += 1
        elif args[i] in ("--file", "-f"):
            # T025: --file argument parsing (now supports multiple)
            if i + 1 >= len(args):
                # T033: Handle --file without path argument
                print("Error: --file requires a path argument")
                print("Usage: tail --file <path>")
                return
            file_paths.append(args[i + 1])
            i += 2
        elif args[i].startswith("--"):
            print(f"Unknown option: {args[i]}")
            return
        else:
            if instance_arg is None:
                instance_arg = args[i]
            i += 1

    # T026: Mutual exclusivity check (--file vs instance ID)
    # Use first file path for validation if multiple provided
    file_path_for_check = file_paths[0] if file_paths else None
    error = validate_tail_args(
        file_path=file_path_for_check,
        instance_id=int(instance_arg) if instance_arg and instance_arg.isdigit() else None,
    )
    if error:
        print(f"Error: {error}")
        return

    # T027, T028: File-only tailing mode with glob support
    if file_paths:
        # Resolve all paths, expanding globs
        resolved_paths: list[tuple[Path, str | None]] = []  # (path, glob_pattern_or_None)

        for file_path in file_paths:
            if is_glob_pattern(file_path):
                # T073: Expand glob pattern
                glob = GlobPattern.from_path(file_path)
                matches = glob.expand()

                if not matches:
                    # T074: Handle "No files match pattern" error
                    print(f"Error: No files match pattern: {file_path}")
                    return

                # Warn if many files matched
                if len(matches) > 10:
                    print(f"Warning: Pattern matches {len(matches)} files")

                for path in matches:
                    resolved_paths.append((path, file_path))
            else:
                # Single file path
                resolved_path, path_error = validate_file_path(file_path)
                if path_error:
                    print(f"Error: {path_error}")
                    return
                resolved_paths.append((resolved_path, None))

        # Apply --since as time filter if provided
        if since_time is not None:
            state.time_filter = TimeFilter(since=since_time)

        # Stop any existing tailer before starting a new one
        if state.tailer is not None:
            state.tailer.stop()
            state.tailer = None

        # Determine display name
        if len(resolved_paths) == 1:
            display_name = resolved_paths[0][0].name
        else:
            display_name = f"{len(resolved_paths)} files"

        # T029, T030, T031, T032: File-only tail mode
        if stream_mode:
            # Legacy stream mode - only supports single file
            if len(resolved_paths) > 1:
                print("Error: --stream mode only supports single file")
                print("Use without --stream for multiple files")
                return
            tail_file_stream_mode(state, resolved_paths[0][0])
        else:
            # Determine glob pattern for dynamic file watching
            glob_pattern_str = next((p[1] for p in resolved_paths if p[1]), None)
            tail_file_mode(
                state,
                resolved_paths[0][0],
                multi_file_paths=[p[0] for p in resolved_paths]
                if len(resolved_paths) > 1
                else None,
                glob_pattern=glob_pattern_str,
                display_name=display_name if len(resolved_paths) > 1 else None,
            )
        return

    # Standard instance-based tailing
    if instance_arg is None:
        # If no arg given, use first instance or show error
        if not state.instances:
            print("No instances detected. Run 'refresh' to scan.")
            return
        if len(state.instances) == 1:
            instance = state.instances[0]
        else:
            print("Multiple instances found. Specify an ID or use --file:")
            print("  tail <id>")
            print("  tail --file <path>")
            print()
            list_command(state)
            return
    else:
        instance = find_instance(state, instance_arg)
        if instance is None:
            print(f"Instance not found: {instance_arg}")
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

    # Apply --since as time filter if provided
    if since_time is not None:
        state.time_filter = TimeFilter(since=since_time)

    # Stop any existing tailer before starting a new one
    if state.tailer is not None:
        state.tailer.stop()
        state.tailer = None

    # Use status bar mode by default, streaming mode with --stream
    if not stream_mode:
        # Status bar tail mode (default)
        tail_status_bar_mode(state, instance)
    else:
        # Legacy streaming mode
        tail_stream_mode(state, instance)


def tail_status_bar_mode(state: AppState, instance: Instance) -> None:
    """Launch the status bar tail mode interface.

    Args:
        state: Current application state.
        instance: PostgreSQL instance to tail.
    """
    from pgtail_py.tail_textual import TailApp

    # log_path is verified by caller before calling this function
    assert instance.log_path is not None

    state.current_instance = instance
    state.tailing = True

    # Create and start Textual TailApp
    try:
        TailApp.run_tail_mode(state, instance, instance.log_path)
    finally:
        # Clean up state after exit
        state.tailing = False
        state.current_instance = None
        reset_terminal()


def tail_stream_mode(state: AppState, instance: Instance) -> None:
    """Legacy streaming tail mode.

    Args:
        state: Current application state.
        instance: PostgreSQL instance to tail.
    """
    # log_path is verified by caller before calling this function
    assert instance.log_path is not None

    # Start tailing
    state.current_instance = instance
    state.tailing = True
    state.output_paused = False
    state.stop_event.clear()

    print(f"Tailing {instance.log_path}")
    # Show active filters and settings
    if state.time_filter.is_active():
        print(f"Time filter: {state.time_filter.format_description()}")
    if state.field_filter.is_active():
        print(state.field_filter.format_status())
    if (
        state.display_state.mode.value != "compact"
        or state.display_state.output_format.value != "text"
    ):
        print(state.display_state.format_status())
    print("Press Ctrl+C to stop")
    print()

    # Create combined callback for error tracking, connection tracking, and notifications
    def on_entry_callback(entry: LogEntry) -> None:
        state.error_stats.add(entry)
        state.connection_stats.add(entry)
        if state.notification_manager:
            state.notification_manager.check(entry)

    # Callback for when tailer switches to a new log file (after restart/rotation)
    def on_file_change(new_path: Path) -> None:
        print(f"\nSwitched to: {new_path.name}")

    state.tailer = LogTailer(
        instance.log_path,
        state.active_levels,
        state.regex_state,
        state.time_filter if state.time_filter.is_active() else None,
        state.field_filter if state.field_filter.is_active() else None,
        on_entry=on_entry_callback,
        data_dir=instance.data_dir,
        log_directory=instance.log_directory,
        on_file_change=on_file_change,
    )

    # Set callback to display format when detected
    def on_format_detected(fmt: LogFormat) -> None:
        format_names = {
            LogFormat.TEXT: "text",
            LogFormat.CSV: "csvlog",
            LogFormat.JSON: "jsonlog",
        }
        print(f"Detected format: {format_names.get(fmt, fmt.value)}")

    state.tailer.set_format_callback(on_format_detected)
    state.tailer.start()


def tail_file_mode(
    state: AppState,
    log_path: Path,
    *,
    multi_file_paths: list[Path] | None = None,
    glob_pattern: str | None = None,
    display_name: str | None = None,
) -> None:
    """Launch the status bar tail mode for an arbitrary file or multiple files.

    T029, T030: Implements file-only tailing using TailApp with instance=None.
    T075, T089: Supports multi-file tailing with glob patterns.

    Args:
        state: Current application state.
        log_path: Resolved path to the primary log file.
        multi_file_paths: List of paths for multi-file tailing.
        glob_pattern: Glob pattern for dynamic file watching.
        display_name: Display name for status bar (e.g., "3 files").
    """
    from pgtail_py.tail_textual import TailApp

    # T031: Set state.current_file_path when tailing a file
    state.current_file_path = log_path
    state.tailing = True

    # Determine filename for display
    filename = display_name or log_path.name

    # Create and start Textual TailApp with instance=None
    try:
        # T030: Call TailApp.run_tail_mode with instance=None
        TailApp.run_tail_mode(
            state=state,
            instance=None,
            log_path=log_path,
            filename=filename,
            multi_file_paths=multi_file_paths,
            glob_pattern=glob_pattern,
        )
    finally:
        # T032: Clear state.current_file_path when stopping
        state.tailing = False
        state.current_file_path = None
        reset_terminal()


def tail_file_stream_mode(state: AppState, log_path: Path) -> None:
    """Legacy streaming tail mode for an arbitrary file.

    Args:
        state: Current application state.
        log_path: Resolved path to the log file.
    """
    from pgtail_py.instance import Instance

    # T031: Set state.current_file_path when tailing a file
    state.current_file_path = log_path
    state.tailing = True
    state.output_paused = False
    state.stop_event.clear()

    print(f"Tailing {log_path}")
    # Show active filters and settings
    if state.time_filter.is_active():
        print(f"Time filter: {state.time_filter.format_description()}")
    if state.field_filter.is_active():
        print(state.field_filter.format_status())
    if (
        state.display_state.mode.value != "compact"
        or state.display_state.output_format.value != "text"
    ):
        print(state.display_state.format_status())
    print("Press Ctrl+C to stop")
    print()

    # Create combined callback for error tracking, connection tracking, and notifications
    def on_entry_callback(entry: LogEntry) -> None:
        state.error_stats.add(entry)
        state.connection_stats.add(entry)
        if state.notification_manager:
            state.notification_manager.check(entry)

    # Create a file-only instance for the tailer
    file_instance = Instance.file_only(log_path)

    state.tailer = LogTailer(
        log_path,
        state.active_levels,
        state.regex_state,
        state.time_filter if state.time_filter.is_active() else None,
        state.field_filter if state.field_filter.is_active() else None,
        on_entry=on_entry_callback,
        data_dir=file_instance.data_dir,
        log_directory=file_instance.log_directory,
    )

    # Set callback to display format when detected
    def on_format_detected(fmt: LogFormat) -> None:
        format_names = {
            LogFormat.TEXT: "text",
            LogFormat.CSV: "csvlog",
            LogFormat.JSON: "jsonlog",
        }
        print(f"Detected format: {format_names.get(fmt, fmt.value)}")

    state.tailer.set_format_callback(on_format_detected)
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
    state.output_paused = False
    state.stop_event.set()
    state.current_instance = None
    # T032: Clear state.current_file_path when stopping
    state.current_file_path = None

    # Reset terminal state to prevent mangled output
    reset_terminal()
    print("Stopped tailing.")


def display_command(state: AppState, args: list[str]) -> None:
    """Handle the 'display' command - control log entry display mode.

    Args:
        state: Current application state.
        args: Command arguments (compact, full, or fields <field1,field2,...>).
    """
    if not args:
        # Show current display mode
        print(state.display_state.format_status())
        return

    subcommand = args[0].lower()

    if subcommand == "compact":
        state.display_state.set_compact()
        print("Display mode: compact")
    elif subcommand == "full":
        state.display_state.set_full()
        print("Display mode: full")
    elif subcommand == "fields":
        if len(args) < 2:
            print("Usage: display fields <field1,field2,...>")
            print(f"Valid fields: {', '.join(get_valid_display_fields())}")
            return

        # Parse comma-separated field list
        field_arg = args[1]
        fields = [f.strip() for f in field_arg.split(",") if f.strip()]

        if not fields:
            print("No fields specified.")
            print(f"Valid fields: {', '.join(get_valid_display_fields())}")
            return

        invalid = state.display_state.set_custom(fields)

        if invalid:
            print(f"Unknown fields: {', '.join(invalid)}")
            print(f"Valid fields: {', '.join(get_valid_display_fields())}")
            if state.display_state.custom_fields:
                print(f"Using valid fields: {', '.join(state.display_state.custom_fields)}")
        else:
            print(f"Display mode: custom ({len(fields)} fields)")
    else:
        print(f"Unknown display mode: {subcommand}")
        print("Usage: display [compact|full|fields <field1,field2,...>]")


def output_command(state: AppState, args: list[str]) -> None:
    """Handle the 'output' command - control output format (text or JSON).

    Args:
        state: Current application state.
        args: Command arguments (json or text).
    """
    if not args:
        # Show current output format
        fmt = state.display_state.output_format.value
        print(f"Output format: {fmt}")
        print()
        print("Usage: output json   Output as JSON (one object per line)")
        print("       output text   Output as colored text (default)")
        return

    subcommand = args[0].lower()

    if subcommand == "json":
        state.display_state.set_output_json()
        print("Output format: json")
        print("Note: Slow query highlighting and regex highlights disabled in JSON mode")
    elif subcommand == "text":
        state.display_state.set_output_text()
        print("Output format: text")
    else:
        print(f"Unknown output format: {subcommand}")
        print("Usage: output [json|text]")
