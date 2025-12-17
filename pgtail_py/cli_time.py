"""Time-based filtering commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.time_filter import TimeFilter, is_future_time, parse_time

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


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


def until_command(state: AppState, args: list[str]) -> None:
    """Handle the 'until' command - filter logs up to a specific time.

    Args:
        state: Current application state.
        args: Command arguments:
            - No args: Display usage
            - Time value: Set upper bound filter
    """
    # No args - show usage
    if not args:
        if state.time_filter.is_active():
            print(f"Time filter: {state.time_filter.format_description()}")
            print()
        print("Usage: until <time>")
        print()
        print("Time formats:")
        print("  5m, 30s, 2h, 1d       Relative (from now)")
        print("  14:30, 14:30:45       Time today")
        print("  2024-01-15T14:30      ISO 8601 datetime")
        print()
        print("Example: until 15:00")
        print()
        print("Note: until disables live tailing (no new entries will appear)")
        return

    # Handle 'clear' subcommand
    if args[0].lower() == "clear":
        state.time_filter = TimeFilter.empty()
        if state.tailer:
            state.tailer.update_time_filter(None)
        print("Time filter cleared")
        return

    # Parse time value
    try:
        until_time = parse_time(args[0])
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Create and apply time filter (until only, no since)
    state.time_filter = TimeFilter(until=until_time, original_input=args[0])

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_time_filter(state.time_filter)

    # Display feedback
    print(f"Showing logs {state.time_filter.format_description()}")
    print("Note: Live tailing disabled (until sets an upper bound)")
