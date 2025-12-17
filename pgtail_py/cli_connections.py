"""Connection statistics command handlers.

Provides the `connections` command for displaying connection statistics,
summaries grouped by database/user/application, and the clear subcommand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def connections_command(state: AppState, args: list[str]) -> None:
    """Handle the connections command.

    Args:
        state: Current application state.
        args: Command arguments (e.g., clear, --history, --watch, filters).
    """
    # Check for clear subcommand first
    if "clear" in args:
        if len(args) > 1:
            print_formatted_text(
                HTML("<ansiyellow>Warning: clear ignores other options</ansiyellow>")
            )
        _clear_stats(state)
        return

    # For Phase 3 (MVP), only summary view is implemented
    # Parse filter arguments for future use
    db_filter: str | None = None
    user_filter: str | None = None
    app_filter: str | None = None
    show_history = False
    show_watch = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--history":
            show_history = True
        elif arg == "--watch":
            show_watch = True
        elif arg.startswith("--db="):
            db_filter = arg[5:]
        elif arg.startswith("--user="):
            user_filter = arg[7:]
        elif arg.startswith("--app="):
            app_filter = arg[6:]
        else:
            print_formatted_text(
                HTML(
                    "<ansiyellow>Usage: connections [--history] [--watch] "
                    "[--db=NAME] [--user=NAME] [--app=NAME] [clear]</ansiyellow>"
                )
            )
            return
        i += 1

    # Check for invalid combinations
    if show_history and show_watch:
        print_formatted_text(
            HTML("<ansiyellow>Cannot use --history and --watch together.</ansiyellow>")
        )
        return

    # Show history view (trend visualization)
    if show_history:
        _show_history(state, db_filter, user_filter, app_filter)
        return

    if show_watch:
        print_formatted_text(
            HTML("<ansiyellow>--watch not yet implemented. Coming in Phase 5.</ansiyellow>")
        )
        return

    # Show summary (default view)
    _show_summary(state, db_filter, user_filter, app_filter)


def _show_summary(
    state: AppState,
    db_filter: str | None = None,
    user_filter: str | None = None,
    app_filter: str | None = None,
) -> None:
    """Display connection summary.

    Args:
        state: Current application state.
        db_filter: Optional database name filter.
        user_filter: Optional user name filter.
        app_filter: Optional application name filter.
    """
    stats = state.connection_stats

    if stats.is_empty():
        print_formatted_text(
            "No connection data available.\n"
            "Start tailing a log with `tail` to begin tracking connections.\n"
            "Note: PostgreSQL must have log_connections=on and log_disconnections=on"
        )
        return

    # Get active connections (filtering will be applied in Phase 6)
    active = stats.active_count()

    # Check if any filters are active
    has_filter = any([db_filter, user_filter, app_filter])

    if has_filter:
        # Filtered view - show filter context
        filter_parts = []
        if db_filter:
            filter_parts.append(f"db='{db_filter}'")
        if user_filter:
            filter_parts.append(f"user='{user_filter}'")
        if app_filter:
            filter_parts.append(f"app='{app_filter}'")
        filter_desc = ", ".join(filter_parts)

        # For now, filtering not applied to counts (Phase 6)
        # Just show the header indicating filters
        print_formatted_text(
            HTML(
                f"<b>Active connections</b> (filter: {filter_desc}): <ansigreen>{active}</ansigreen>\n"
            )
        )
    else:
        # Default summary view
        print_formatted_text(HTML(f"<b>Active connections:</b> <ansigreen>{active}</ansigreen>\n"))

    # By database
    by_db = stats.get_by_database()
    if by_db:
        print_formatted_text("By database:")
        for db, count in sorted(by_db.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {db:<15} {count:>5}")
        print()

    # By user
    by_user = stats.get_by_user()
    if by_user:
        print_formatted_text("By user:")
        for user, count in sorted(by_user.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {user:<15} {count:>5}")
        print()

    # By application
    by_app = stats.get_by_application()
    if by_app:
        print_formatted_text("By application:")
        for app, count in sorted(by_app.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {app:<15} {count:>5}")
        print()

    # Session totals
    totals = f"Session totals: {stats.connect_count} connects, {stats.disconnect_count} disconnects"
    if stats.failed_count > 0:
        totals += f", {stats.failed_count} failed"
    print_formatted_text(totals)


def _show_history(
    state: AppState,
    db_filter: str | None = None,
    user_filter: str | None = None,
    app_filter: str | None = None,
) -> None:
    """Display connection history with trend visualization.

    Shows connection rate trends using sparklines, including:
    - Connection rate over time (15-minute buckets)
    - Disconnection rate over time
    - Net change detection (leak detection)

    Args:
        state: Current application state.
        db_filter: Optional database name filter (not yet applied).
        user_filter: Optional user name filter (not yet applied).
        app_filter: Optional application name filter (not yet applied).
    """
    from pgtail_py.error_trend import sparkline

    stats = state.connection_stats

    if stats.is_empty():
        print_formatted_text(
            "No connection data available.\n"
            "Start tailing a log with `tail` to begin tracking connections.\n"
            "Note: PostgreSQL must have log_connections=on and log_disconnections=on"
        )
        return

    # Note: Filters will be applied in Phase 6
    if any([db_filter, user_filter, app_filter]):
        filter_parts = []
        if db_filter:
            filter_parts.append(f"db='{db_filter}'")
        if user_filter:
            filter_parts.append(f"user='{user_filter}'")
        if app_filter:
            filter_parts.append(f"app='{app_filter}'")
        print_formatted_text(
            HTML(
                f"<ansiyellow>Note: Filter ({', '.join(filter_parts)}) "
                "not yet applied to history. Coming in Phase 6.</ansiyellow>\n"
            )
        )

    # Get trend buckets (last 60 minutes, 15-minute intervals)
    buckets = stats.get_trend_buckets(minutes=60, bucket_size=15)

    # Extract connects and disconnects
    connects = [b[0] for b in buckets]
    disconnects = [b[1] for b in buckets]

    total_connects = sum(connects)
    total_disconnects = sum(disconnects)
    net_change = total_connects - total_disconnects

    print_formatted_text(HTML("<b>Connection History (last 60 min, 15-min buckets)</b>"))
    print_formatted_text("─────────────────────────────────────────────────\n")

    # Sparklines
    print_formatted_text(
        HTML(
            f"  <ansigreen>Connects:</ansigreen>    {sparkline(connects)}  "
            f"total {total_connects}"
        )
    )
    print_formatted_text(
        HTML(
            f"  <ansiyellow>Disconnects:</ansiyellow> {sparkline(disconnects)}  "
            f"total {total_disconnects}"
        )
    )

    # Net change indicator
    if net_change > 0:
        print_formatted_text(
            HTML(f"\n  Net change: <ansigreen>+{net_change}</ansigreen> (connections growing)")
        )
    elif net_change < 0:
        print_formatted_text(
            HTML(f"\n  Net change: <ansiyellow>{net_change}</ansiyellow> (connections decreasing)")
        )
    else:
        print_formatted_text("\n  Net change: 0 (stable)")

    # Detect potential connection leak (many connects, few disconnects)
    if total_connects > 10 and total_disconnects == 0:
        print_formatted_text(
            HTML(
                "\n  <ansired>⚠ Possible connection leak detected:</ansired> "
                "connections without disconnections"
            )
        )
    elif total_connects > 20 and total_disconnects < total_connects * 0.1:
        print_formatted_text(
            HTML(
                "\n  <ansiyellow>⚠ Low disconnect rate:</ansiyellow> "
                f"only {total_disconnects} disconnects for {total_connects} connects"
            )
        )

    # Current active count
    print_formatted_text(HTML(f"\n  Active now: <ansigreen>{stats.active_count()}</ansigreen>"))


def _clear_stats(state: AppState) -> None:
    """Clear all connection statistics."""
    state.connection_stats.clear()
    print_formatted_text("Connection statistics cleared.")
