"""Core CLI commands for instance management and navigation."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from pgtail_py.cli_utils import find_instance, shorten_path
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
    """Handle the 'tail' command - tail logs for an instance.

    Args:
        state: Current application state.
        args: Command arguments (instance ID or path, optional --since flag).
    """
    # Parse --since flag from arguments
    since_time = None
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
        elif args[i].startswith("--"):
            print(f"Unknown option: {args[i]}")
            return
        else:
            if instance_arg is None:
                instance_arg = args[i]
            i += 1

    if instance_arg is None:
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

    # Start tailing
    state.current_instance = instance
    state.tailing = True
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

    state.tailer = LogTailer(
        instance.log_path,
        state.active_levels,
        state.regex_state,
        state.time_filter if state.time_filter.is_active() else None,
        state.field_filter if state.field_filter.is_active() else None,
        on_entry=on_entry_callback,
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
    state.stop_event.set()
    state.current_instance = None

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
