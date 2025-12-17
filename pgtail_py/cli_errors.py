"""Error statistics command handlers.

Provides the `errors` command for displaying error statistics,
trends, live counters, and filtering by SQLSTATE code.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from pgtail_py.error_stats import get_sqlstate_name

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def errors_command(state: AppState, args: list[str]) -> None:
    """Handle the errors command.

    Args:
        state: Current application state.
        args: Command arguments (e.g., --trend, --live, --code, clear).
    """
    if not args:
        _show_summary(state)
    elif args[0] == "clear":
        _clear_stats(state)
    elif args[0] == "--trend":
        _show_trend(state)
    elif args[0] == "--live":
        _show_live(state)
    elif args[0] == "--code" and len(args) > 1:
        _show_by_code(state, args[1])
    else:
        print_formatted_text(
            HTML("<ansiyellow>Usage: errors [--trend|--live|--code CODE|clear]</ansiyellow>")
        )


def _show_summary(state: AppState) -> None:
    """Display error summary."""
    stats = state.error_stats

    if stats.is_empty():
        print_formatted_text("No errors recorded in this session.")
        return

    # Header
    print_formatted_text(
        HTML(
            f"<b>Error Statistics</b>\n"
            f"─────────────────────────────\n"
            f"Errors: <ansired>{stats.error_count}</ansired>  "
            f"Warnings: <ansiyellow>{stats.warning_count}</ansiyellow>"
        )
    )

    # By type (SQLSTATE code)
    by_code = stats.get_by_code()
    if by_code:
        print_formatted_text("\nBy type:")
        for code, count in list(by_code.items())[:10]:  # Top 10
            name = get_sqlstate_name(code)
            if name != code:
                print_formatted_text(f"  {code} {name:<25} {count:>5}")
            else:
                print_formatted_text(f"  {code:<31} {count:>5}")

    # By level
    by_level = stats.get_by_level()
    if by_level:
        print_formatted_text("\nBy level:")
        for level in sorted(by_level.keys(), key=lambda x: x.value):
            count = by_level[level]
            print_formatted_text(f"  {level.name:<9} {count:>5}")


def _clear_stats(state: AppState) -> None:
    """Clear all error statistics."""
    state.error_stats.clear()
    print_formatted_text("Error statistics cleared.")


def _show_trend(state: AppState) -> None:
    """Display error rate trend with sparkline."""
    from pgtail_py.error_trend import sparkline

    stats = state.error_stats

    if stats.is_empty():
        print_formatted_text("No errors recorded in this session.")
        return

    buckets = stats.get_trend_buckets(60)
    total = sum(buckets)
    avg = total / len(buckets) if buckets else 0

    # Detect spikes (>2x average)
    spike_info = ""
    if avg > 0:
        max_val = max(buckets)
        if max_val > avg * 2:
            # Find when the spike occurred
            spike_idx = buckets.index(max_val)
            minutes_ago = 60 - spike_idx - 1
            spike_info = f"  ← spike {minutes_ago}m ago ({max_val}/min)"

    print_formatted_text("Error rate (per minute):\n")
    print_formatted_text(
        f"Last 60 min: {sparkline(buckets)}  total {total}, avg {avg:.1f}/min{spike_info}"
    )


def _show_live(state: AppState) -> None:
    """Display live updating error counter with ANSI cursor control.

    Updates in place every 500ms showing:
    - Error count (red)
    - Warning count (yellow)
    - Time since last error

    Starts a background tailer to track new errors while in live mode.
    Press Ctrl+C to exit.
    """
    import sys
    import time

    from pgtail_py.tailer import LogTailer

    # Need a log file to track - check current or last instance
    instance = state.current_instance
    if instance is None and state.instances:
        # Try first instance with logs
        for inst in state.instances:
            if inst.log_path and inst.log_path.exists():
                instance = inst
                break

    if instance is None or not instance.log_path:
        print_formatted_text(
            HTML(
                "<ansiyellow>No log file available. "
                "Use 'tail' first to select an instance.</ansiyellow>"
            )
        )
        return

    if not instance.log_path.exists():
        print_formatted_text(
            HTML(f"<ansiyellow>Log file not found: {instance.log_path}</ansiyellow>")
        )
        return

    # ANSI escape codes
    CLEAR_LINE = "\033[2K"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"

    def format_time_since(last_time: datetime | None) -> str:
        """Format time since last error."""
        if last_time is None:
            return "never"

        delta = datetime.now() - last_time
        seconds = int(delta.total_seconds())

        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s ago"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m ago"

    def render_display() -> str:
        """Render the live display - read fresh values each time."""
        stats = state.error_stats
        time_since = format_time_since(stats.last_error_time)
        return (
            f"Errors: \033[91m{stats.error_count}\033[0m | "
            f"Warnings: \033[93m{stats.warning_count}\033[0m | "
            f"Last error: {time_since}"
        )

    # Start a background tailer just for error tracking (no display)
    live_tailer = LogTailer(
        instance.log_path,
        active_levels=None,  # Track all levels
        regex_state=None,
        time_filter=None,
        field_filter=None,
        on_entry=state.error_stats.add,
    )
    live_tailer.start()

    # Hide cursor during live mode
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    try:
        # Print initial line (will be updated in place)
        print_formatted_text(
            f"Live error counter - {instance.log_path.name} (Ctrl+C to exit)\n"
        )
        sys.stdout.write(render_display())
        sys.stdout.flush()

        while True:
            time.sleep(0.5)  # 500ms update interval

            # Move cursor to beginning of line and clear
            sys.stdout.write("\r" + CLEAR_LINE)

            # Write updated stats
            sys.stdout.write(render_display())
            sys.stdout.flush()

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        sys.stdout.write("\n")
    finally:
        # Stop the background tailer
        live_tailer.stop()
        # Always restore cursor visibility
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
        print_formatted_text("Exited live mode.")


def _show_by_code(state: AppState, code: str) -> None:
    """Display errors filtered by SQLSTATE code."""
    # Validate code format
    if len(code) != 5:
        print_formatted_text(
            HTML(
                "<ansiyellow>Invalid SQLSTATE code format. "
                "Expected 5 characters (e.g., 23505).</ansiyellow>"
            )
        )
        return

    stats = state.error_stats
    events = stats.get_events_by_code(code)

    if not events:
        print_formatted_text(f"No errors with code {code} recorded.")
        return

    name = get_sqlstate_name(code)
    if name != code:
        print_formatted_text(f"{code} {name}: {len(events)} occurrences\n")
    else:
        print_formatted_text(f"{code}: {len(events)} occurrences\n")

    # Show recent examples
    print_formatted_text("Recent examples:")
    for event in events[-5:]:  # Last 5
        ts = event.timestamp.strftime("%H:%M:%S")
        msg = event.message[:60] + "..." if len(event.message) > 60 else event.message
        print_formatted_text(f"  {ts} {msg}")
