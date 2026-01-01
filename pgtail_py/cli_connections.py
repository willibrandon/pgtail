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
    from pgtail_py.parser import LogEntry


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

    # Show watch mode (live event stream)
    if show_watch:
        _show_watch(state, db_filter, user_filter, app_filter)
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
    from pgtail_py.connection_stats import ConnectionFilter

    stats = state.connection_stats

    if stats.is_empty():
        print_formatted_text(
            "No connection data available.\n"
            "Start tailing a log with `tail` to begin tracking connections.\n"
            "Note: PostgreSQL must have log_connections=on and log_disconnections=on"
        )
        return

    # Create filter from parameters
    conn_filter = ConnectionFilter(
        database=db_filter,
        user=user_filter,
        application=app_filter,
    )

    # Get filtered active connections
    filtered_active = stats.get_active_connections(conn_filter)

    active_count = len(filtered_active)

    # Check if any filters are active
    has_filter = not conn_filter.is_empty()

    if has_filter:
        # Filtered view - show filter context
        filter_parts: list[str] = []
        if db_filter:
            filter_parts.append(f"db='{db_filter}'")
        if user_filter:
            filter_parts.append(f"user='{user_filter}'")
        if app_filter:
            filter_parts.append(f"app='{app_filter}'")
        filter_desc = ", ".join(filter_parts)

        print_formatted_text(
            HTML(
                f"<b>Active connections</b> (filter: {filter_desc}): "
                f"<ansigreen>{active_count}</ansigreen>\n"
            )
        )
    else:
        # Default summary view
        print_formatted_text(
            HTML(f"<b>Active connections:</b> <ansigreen>{active_count}</ansigreen>\n")
        )

    # Aggregate filtered connections
    from collections import defaultdict

    by_db: dict[str, int] = defaultdict(int)
    by_user: dict[str, int] = defaultdict(int)
    by_app: dict[str, int] = defaultdict(int)

    for event in filtered_active:
        by_db[event.database or "unknown"] += 1
        by_user[event.user or "unknown"] += 1
        by_app[event.application or "unknown"] += 1

    # By database
    if by_db:
        print_formatted_text("By database:")
        for db, count in sorted(by_db.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {db:<15} {count:>5}")
        print()

    # By user
    if by_user:
        print_formatted_text("By user:")
        for user, count in sorted(by_user.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {user:<15} {count:>5}")
        print()

    # By application
    if by_app:
        print_formatted_text("By application:")
        for app, count in sorted(by_app.items(), key=lambda x: -x[1]):
            print_formatted_text(f"  {app:<15} {count:>5}")
        print()

    # Session totals (unfiltered - shows overall session activity)
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
        db_filter: Optional database name filter.
        user_filter: Optional user name filter.
        app_filter: Optional application name filter.
    """
    from datetime import datetime

    from pgtail_py.connection_event import ConnectionEventType
    from pgtail_py.connection_stats import ConnectionFilter
    from pgtail_py.error_trend import sparkline

    stats = state.connection_stats

    if stats.is_empty():
        print_formatted_text(
            "No connection data available.\n"
            "Start tailing a log with `tail` to begin tracking connections.\n"
            "Note: PostgreSQL must have log_connections=on and log_disconnections=on"
        )
        return

    # Create filter from parameters
    conn_filter = ConnectionFilter(
        database=db_filter,
        user=user_filter,
        application=app_filter,
    )

    # Build filter description for header
    filter_desc = ""
    if not conn_filter.is_empty():
        filter_parts: list[str] = []
        if db_filter:
            filter_parts.append(f"db='{db_filter}'")
        if user_filter:
            filter_parts.append(f"user='{user_filter}'")
        if app_filter:
            filter_parts.append(f"app='{app_filter}'")
        filter_desc = f" (filter: {', '.join(filter_parts)})"

    # Get filtered trend buckets (last 60 minutes, 15-minute intervals)
    minutes = 60
    bucket_size = 15
    num_buckets = max(1, minutes // bucket_size)
    buckets: list[tuple[int, int]] = [(0, 0) for _ in range(num_buckets)]
    now = datetime.now()

    for event in stats.get_events():
        # Apply filter
        if not conn_filter.is_empty() and not conn_filter.matches(event):
            continue

        # Calculate bucket
        delta = now - event.timestamp
        minutes_ago = delta.total_seconds() / 60
        if minutes_ago < 0 or minutes_ago >= minutes:
            continue

        bucket_idx = num_buckets - 1 - int(minutes_ago // bucket_size)
        bucket_idx = max(0, min(num_buckets - 1, bucket_idx))

        connects, disconnects = buckets[bucket_idx]
        if event.event_type == ConnectionEventType.CONNECT:
            buckets[bucket_idx] = (connects + 1, disconnects)
        elif event.event_type == ConnectionEventType.DISCONNECT:
            buckets[bucket_idx] = (connects, disconnects + 1)

    # Extract connects and disconnects
    connects = [b[0] for b in buckets]
    disconnects = [b[1] for b in buckets]

    total_connects = sum(connects)
    total_disconnects = sum(disconnects)
    net_change = total_connects - total_disconnects

    print_formatted_text(
        HTML(f"<b>Connection History{filter_desc} (last 60 min, 15-min buckets)</b>")
    )
    print_formatted_text("─────────────────────────────────────────────────\n")

    # Sparklines
    print_formatted_text(
        HTML(f"  <ansigreen>Connects:</ansigreen>    {sparkline(connects)}  total {total_connects}")
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


def _show_watch(
    state: AppState,
    db_filter: str | None = None,
    user_filter: str | None = None,
    app_filter: str | None = None,
) -> None:
    """Display live connection events as they occur.

    Shows real-time stream of connection events with color-coded indicators:
    - [+] green: New connection
    - [-] yellow: Disconnection
    - [!] red: Connection failure

    Args:
        state: Current application state.
        db_filter: Optional database name filter.
        user_filter: Optional user name filter.
        app_filter: Optional application name filter.
    """
    import signal
    import time

    from pgtail_py.connection_event import ConnectionEvent, ConnectionEventType
    from pgtail_py.connection_stats import ConnectionFilter
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

    # Create filter from parameters
    conn_filter = ConnectionFilter(
        database=db_filter,
        user=user_filter,
        application=app_filter,
    )

    # Build filter description for header
    filter_desc = ""
    if not conn_filter.is_empty():
        filter_parts: list[str] = []
        if db_filter:
            filter_parts.append(f"db='{db_filter}'")
        if user_filter:
            filter_parts.append(f"user='{user_filter}'")
        if app_filter:
            filter_parts.append(f"app='{app_filter}'")
        filter_desc = f" (filter: {', '.join(filter_parts)})"

    # Track events seen count for display
    events_seen = 0

    def format_event(event: ConnectionEvent) -> str:
        """Format a connection event for display."""
        ts = event.timestamp.strftime("%H:%M:%S")
        user = event.user or "?"
        db = event.database or "?"
        app = event.application if event.application != "unknown" else ""
        host = event.host or ""

        details = f"{user}@{db}"
        if app:
            details += f" ({app})"
        if host:
            details += f" from {host}"

        if event.event_type == ConnectionEventType.CONNECT:
            return f"\033[92m[+]\033[0m {ts}  {details}"  # Green
        elif event.event_type == ConnectionEventType.DISCONNECT:
            duration = ""
            if event.duration_seconds is not None:
                if event.duration_seconds < 60:
                    duration = f" ({event.duration_seconds:.1f}s)"
                elif event.duration_seconds < 3600:
                    mins = int(event.duration_seconds / 60)
                    secs = int(event.duration_seconds % 60)
                    duration = f" ({mins}m{secs}s)"
                else:
                    hours = int(event.duration_seconds / 3600)
                    mins = int((event.duration_seconds % 3600) / 60)
                    duration = f" ({hours}h{mins}m)"
            return f"\033[93m[-]\033[0m {ts}  {details}{duration}"  # Yellow
        else:  # CONNECTION_FAILED
            return f"\033[91m[!]\033[0m {ts}  {details} FAILED"  # Red

    def on_entry(entry: LogEntry) -> None:
        """Handle incoming log entries."""
        nonlocal events_seen
        event = ConnectionEvent.from_log_entry(entry)
        if event is not None:
            # Also track in stats (always, regardless of filter)
            state.connection_stats.add(entry)
            # Apply filter before display
            if conn_filter.is_empty() or conn_filter.matches(event):
                print(format_event(event))
                events_seen += 1

    # Create tailer for connection event tracking
    watch_tailer = LogTailer(
        instance.log_path,
        active_levels=None,  # Track all levels
        regex_state=None,
        time_filter=None,
        field_filter=None,
        on_entry=on_entry,
        data_dir=instance.data_dir,
        log_directory=instance.log_directory,
    )

    print_formatted_text(
        HTML(
            f"<b>Watching connections{filter_desc}</b> - {instance.log_path.name} (Ctrl+C to exit)\n"
            "<ansigreen>[+]</ansigreen> connect  "
            "<ansiyellow>[-]</ansiyellow> disconnect  "
            "<ansired>[!]</ansired> failed\n"
        )
    )

    # Use signal handler for reliable Ctrl+C detection
    # (prompt_toolkit may intercept KeyboardInterrupt)
    stop_requested = False

    def handle_sigint(signum: int, frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    old_handler = signal.signal(signal.SIGINT, handle_sigint)

    watch_tailer.start()

    try:
        while not stop_requested:
            time.sleep(0.1)
    finally:
        signal.signal(signal.SIGINT, old_handler)
        watch_tailer.stop()
        print_formatted_text(f"\nExited watch mode. {events_seen} events seen.")


def _clear_stats(state: AppState) -> None:
    """Clear all connection statistics."""
    state.connection_stats.clear()
    print_formatted_text("Connection statistics cleared.")
