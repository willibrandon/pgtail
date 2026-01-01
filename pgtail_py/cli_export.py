"""Export and pipe commands for log entries."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pgtail_py.colors import print_log_entry
from pgtail_py.export import (
    ExportFormat,
    confirm_overwrite,
    export_to_file,
    follow_export,
    get_filtered_entries,
    parse_since,
    pipe_to_command,
)

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


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
    if state.tailer is None:
        print("No log file loaded. Use 'tail <instance>' first.")
        return

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
