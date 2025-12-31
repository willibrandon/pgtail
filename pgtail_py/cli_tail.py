"""Command handlers for tail mode.

This module provides command parsing and handling for commands executed
within the status bar tail mode interface, including filter commands,
display commands, and exit commands.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.filter import LogLevel, parse_levels

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_buffer import TailBuffer
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus
    from pgtail_py.tailer import LogTailer


# Supported tail mode commands
TAIL_MODE_COMMANDS: list[str] = [
    # Filter commands (modify what's shown)
    "level",  # level error,warning
    "filter",  # filter /pattern/
    "since",  # since 5m
    "until",  # until 14:30
    "between",  # between 14:00 14:30
    "slow",  # slow 100
    "clear",  # clear all filters
    # Display commands (inline output)
    "errors",  # show error summary
    "connections",  # show connection summary
    # Mode commands
    "pause",  # enter PAUSED mode
    "follow",  # enter FOLLOW mode
    # Help
    "help",  # show help
    # Exit commands
    "stop",  # return to REPL
    "exit",  # return to REPL
    "q",  # return to REPL
]


def handle_tail_command(
    cmd: str,
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    stop_callback: Callable[[], None],
    log_widget: TailLog | None = None,
) -> bool:
    """Handle a command entered in tail mode.

    Args:
        cmd: Command name (e.g., 'level', 'filter', 'stop')
        args: Command arguments
        buffer: TailBuffer instance (prompt_toolkit mode) or None (Textual mode)
        status: TailStatus instance
        state: AppState with filter settings
        tailer: LogTailer instance
        stop_callback: Callback to stop the application
        log_widget: TailLog widget (Textual mode) or None (prompt_toolkit mode)

    Returns:
        True if command was handled, False if unknown command
    """
    # Exit commands
    if cmd in ("stop", "exit", "q"):
        stop_callback()
        return True

    # Mode commands - handle both buffer (prompt_toolkit) and log_widget (Textual)
    if cmd == "pause":
        if buffer is not None:
            buffer.set_paused()
            status.set_follow_mode(False, buffer.new_since_pause)
        else:
            # Textual mode - just update status
            status.set_follow_mode(False, 0)
        return True

    if cmd == "follow":
        if buffer is not None:
            buffer.resume_follow()
        # Textual Log widget auto-scrolls when at bottom
        status.set_follow_mode(True, 0)
        return True

    # Filter commands - pass log_widget for Textual mode
    if cmd == "level":
        return _handle_level_command(args, buffer, status, state, tailer, log_widget)

    if cmd == "filter":
        return _handle_filter_command(args, buffer, status, state, tailer, log_widget)

    if cmd == "since":
        return _handle_since_command(args, buffer, status, state, tailer, log_widget)

    if cmd == "until":
        return _handle_until_command(args, buffer, status, state, tailer, log_widget)

    if cmd == "between":
        return _handle_between_command(args, buffer, status, state, tailer, log_widget)

    if cmd == "slow":
        return _handle_slow_command(args, buffer, status, state, log_widget)

    if cmd == "clear":
        return _handle_clear_command(buffer, status, state, tailer, log_widget)

    # Display commands
    if cmd == "errors":
        return _handle_errors_command(args, buffer, state, log_widget)

    if cmd == "connections":
        return _handle_connections_command(args, buffer, state, log_widget)

    # Help command
    if cmd == "help":
        return _handle_help_command(args, buffer, log_widget)

    # Unknown command - show inline error (only in prompt_toolkit mode)
    if buffer is not None:
        error_msg = FormattedText([("class:error", f"Unknown command: {cmd}")])
        buffer.insert_command_output(error_msg)
    # Textual mode - errors are silently ignored (no inline output)
    return False


def _handle_level_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'level' command to filter by log levels.

    Args:
        args: Level names (e.g., ['error', 'warning'] or ['error,warning'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    # Parse comma-separated levels
    level_args: list[str] = []
    for arg in args:
        level_args.extend(arg.split(","))

    levels, invalid = parse_levels(level_args)

    if invalid:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid levels: {', '.join(invalid)}")])
            buffer.insert_command_output(error_msg)
        return True

    # Update state
    state.active_levels = levels

    # Update tailer
    tailer.update_levels(levels)

    # Update status
    if levels is None:
        status.set_level_filter(LogLevel.all_levels())
    else:
        status.set_level_filter(levels)

    # Update buffer filters (prompt_toolkit mode only)
    if buffer is not None:
        _rebuild_buffer_filters(buffer, state, status)

    # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    return True


def _handle_filter_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'filter' command for regex filtering.

    Args:
        args: Pattern argument (e.g., ['/deadlock/'] or ['/pattern/i'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    if not args:
        # No pattern - show current filter (prompt_toolkit mode only)
        if buffer is not None:
            if state.regex_state and state.regex_state.has_filters():
                patterns: list[str] = [f.pattern for f in state.regex_state.includes]
                if patterns:
                    msg = FormattedText([("", f"Active filter: /{patterns[0]}/")])
                else:
                    msg = FormattedText([("", "No regex filter active")])
            else:
                msg = FormattedText([("", "No regex filter active")])
            buffer.insert_command_output(msg)
        return True

    pattern_str = " ".join(args)

    # Parse /pattern/ or /pattern/i syntax
    case_sensitive = False  # Default to case-insensitive
    if pattern_str.startswith("/"):
        if pattern_str.endswith("/i"):
            pattern_str = pattern_str[1:-2]
            case_sensitive = False
        elif pattern_str.endswith("/c"):
            pattern_str = pattern_str[1:-2]
            case_sensitive = True
        elif pattern_str.endswith("/"):
            pattern_str = pattern_str[1:-1]

    # Import and create filter
    from pgtail_py.regex_filter import FilterState, FilterType, RegexFilter

    try:
        regex_filter = RegexFilter.create(pattern_str, FilterType.INCLUDE, case_sensitive)
        state.regex_state = FilterState(includes=[regex_filter])

        # Update tailer
        tailer.update_regex_state(state.regex_state)

        # Update status
        status.set_regex_filter(pattern_str)

        # Update buffer filters (prompt_toolkit mode only)
        if buffer is not None:
            _rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid pattern: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def _handle_since_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'since' command for time filtering.

    Args:
        args: Time specification (e.g., ['5m'] or ['14:30'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    if not args:
        if buffer is not None:
            error_msg = FormattedText([("class:error", "Usage: since <time> (e.g., 5m, 14:30)")])
            buffer.insert_command_output(error_msg)
        return True

    time_str = args[0]

    from pgtail_py.time_filter import TimeFilter, parse_time

    try:
        since_time = parse_time(time_str)
        time_filter = TimeFilter(since=since_time, original_input=time_str)
        state.time_filter = time_filter

        # Update tailer
        tailer.update_time_filter(time_filter)

        # Update status
        status.set_time_filter(f"since:{time_str}")

        # Update buffer filters (prompt_toolkit mode only)
        if buffer is not None:
            _rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def _handle_until_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'until' command for time filtering.

    Args:
        args: Time specification
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    if not args:
        if buffer is not None:
            error_msg = FormattedText([("class:error", "Usage: until <time>")])
            buffer.insert_command_output(error_msg)
        return True

    time_str = args[0]

    from pgtail_py.time_filter import TimeFilter, parse_time

    try:
        until_time = parse_time(time_str)
        time_filter = TimeFilter(until=until_time, original_input=time_str)
        state.time_filter = time_filter

        # Update tailer
        tailer.update_time_filter(time_filter)

        # Update status
        status.set_time_filter(f"until:{time_str}")

        # Update buffer filters (prompt_toolkit mode only)
        if buffer is not None:
            _rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def _handle_between_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'between' command for time range filtering.

    Args:
        args: Start and end time specifications
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    if len(args) < 2:
        if buffer is not None:
            error_msg = FormattedText([("class:error", "Usage: between <start> <end>")])
            buffer.insert_command_output(error_msg)
        return True

    start_str = args[0]
    end_str = args[1]

    from pgtail_py.time_filter import TimeFilter, parse_time

    try:
        since_time = parse_time(start_str)
        until_time = parse_time(end_str)
        time_filter = TimeFilter(
            since=since_time, until=until_time, original_input=f"{start_str} {end_str}"
        )
        state.time_filter = time_filter

        # Update tailer
        tailer.update_time_filter(time_filter)

        # Update status
        status.set_time_filter(f"between:{start_str}-{end_str}")

        # Update buffer filters (prompt_toolkit mode only)
        if buffer is not None:
            _rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def _handle_slow_command(
    args: list[str],
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'slow' command for slow query threshold.

    Args:
        args: Threshold in ms
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    if not args:
        # Show current threshold (prompt_toolkit mode only)
        if buffer is not None:
            if state.slow_query_config and state.slow_query_config.enabled:
                msg = FormattedText(
                    [("", f"Slow query threshold: {state.slow_query_config.warning_ms}ms")]
                )
            else:
                msg = FormattedText([("", "Slow query highlighting disabled")])
            buffer.insert_command_output(msg)
        return True

    try:
        threshold = int(args[0])
        if threshold <= 0:
            raise ValueError("Threshold must be positive")

        # Update slow query config
        from pgtail_py.slow_query import SlowQueryConfig

        state.slow_query_config = SlowQueryConfig(
            enabled=True,
            warning_ms=threshold,
            slow_ms=threshold * 2,
            critical_ms=threshold * 5,
        )

        # Update status
        status.set_slow_threshold(threshold)

    except ValueError as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid threshold: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def _handle_clear_command(
    buffer: TailBuffer | None,
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'clear' command to remove all filters.

    Args:
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    from pgtail_py.regex_filter import FilterState
    from pgtail_py.time_filter import TimeFilter

    # Clear all filters in state
    state.active_levels = None
    state.regex_state = FilterState.empty()
    state.time_filter = TimeFilter.empty()

    # Update tailer
    tailer.update_levels(None)
    tailer.update_regex_state(None)
    tailer.update_time_filter(None)

    # Update status
    status.set_level_filter(LogLevel.all_levels())
    status.set_regex_filter(None)
    status.set_time_filter(None)
    status.set_slow_threshold(None)

    # Clear buffer filters and recalculate counts (prompt_toolkit mode only)
    if buffer is not None:
        buffer.update_filters([])
        error_count, warning_count = buffer.get_filtered_error_warning_counts()
        status.error_count = error_count
        status.warning_count = warning_count
        status.set_total_lines(buffer.filtered_count)

    # Textual mode: clear the log widget content
    if log_widget is not None:
        log_widget.clear()
        status.error_count = 0
        status.warning_count = 0
        status.set_total_lines(0)

    return True


def _handle_errors_command(
    args: list[str],
    buffer: TailBuffer | None,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'errors' command to show error summary.

    Args:
        args: Command arguments (e.g., ['--trend'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    error_stats = state.error_stats

    # Build summary
    lines: list[tuple[str, str]] = []

    total = error_stats.error_count + error_stats.warning_count
    lines.append(("", "Error Statistics (session)\n"))
    lines.append(("", f"  Total: {total}\n"))

    # By severity
    by_level = error_stats.get_by_level()
    if by_level:
        lines.append(("", "  By Level:\n"))
        for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True):
            lines.append(("", f"    {level.name}: {count}\n"))

    # By SQLSTATE
    by_code = error_stats.get_by_code()
    if by_code:
        lines.append(("", "  By SQLSTATE:\n"))
        for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(("", f"    {code}: {count}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled errors to log
        log_widget.write_line(f"[bold cyan]Error Statistics[/bold cyan]  Total: [magenta]{total}[/magenta]")
        if by_level:
            log_widget.write_line("[dim]  By Level:[/dim]")
            for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True):
                # Color by severity
                color = {"PANIC": "bold red", "FATAL": "red", "ERROR": "yellow", "WARNING": "cyan"}.get(
                    level.name, "white"
                )
                log_widget.write_line(f"    [{color}]{level.name}[/{color}]: [magenta]{count}[/magenta]")
        if by_code:
            log_widget.write_line("[dim]  By SQLSTATE:[/dim]")
            for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:10]:
                log_widget.write_line(f"    [cyan]{code}[/cyan]: [magenta]{count}[/magenta]")
    return True


def _handle_connections_command(
    args: list[str],
    buffer: TailBuffer | None,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'connections' command to show connection summary.

    Args:
        args: Command arguments
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    conn_stats = state.connection_stats

    # Build summary
    lines: list[tuple[str, str]] = []

    lines.append(("", "Connection Statistics (session)\n"))
    lines.append(("", f"  Active: {conn_stats.active_count()}\n"))
    lines.append(("", f"  Total connects: {conn_stats.connect_count}\n"))
    lines.append(("", f"  Total disconnects: {conn_stats.disconnect_count}\n"))

    # By database
    by_db = conn_stats.get_by_database()
    if by_db:
        lines.append(("", "  By Database:\n"))
        for db, count in sorted(by_db.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(("", f"    {db}: {count}\n"))

    # By user
    by_user = conn_stats.get_by_user()
    if by_user:
        lines.append(("", "  By User:\n"))
        for user, count in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(("", f"    {user}: {count}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled connections to log
        log_widget.write_line("[bold cyan]Connection Statistics[/bold cyan]")
        log_widget.write_line(
            f"  Active: [magenta]{conn_stats.active_count()}[/magenta]  "
            f"Connects: [green]{conn_stats.connect_count}[/green]  "
            f"Disconnects: [red]{conn_stats.disconnect_count}[/red]"
        )
        if by_db:
            log_widget.write_line("[dim]  By Database:[/dim]")
            for db, count in sorted(by_db.items(), key=lambda x: x[1], reverse=True)[:5]:
                log_widget.write_line(f"    [cyan]{db}[/cyan]: [magenta]{count}[/magenta]")
        if by_user:
            log_widget.write_line("[dim]  By User:[/dim]")
            for user, count in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]:
                log_widget.write_line(f"    [cyan]{user}[/cyan]: [magenta]{count}[/magenta]")
    return True


def _rebuild_buffer_filters(
    buffer: TailBuffer, state: AppState, status: TailStatus | None = None
) -> None:
    """Rebuild buffer filter functions from state and recalculate counts.

    Args:
        buffer: TailBuffer instance
        state: AppState with current filter settings
        status: TailStatus instance to update counts (optional)
    """
    from pgtail_py.parser import LogEntry

    filters: list[Callable[[LogEntry], bool]] = []

    # Level filter
    if state.active_levels is not None:

        def level_filter(entry: LogEntry) -> bool:
            return entry.level in state.active_levels  # type: ignore[operator]

        filters.append(level_filter)

    # Regex filter
    if state.regex_state and state.regex_state.has_filters():

        def regex_filter(entry: LogEntry) -> bool:
            return state.regex_state.should_show(entry.raw)  # type: ignore[union-attr]

        filters.append(regex_filter)

    # Time filter
    if state.time_filter and state.time_filter.is_active():

        def time_filter(entry: LogEntry) -> bool:
            return state.time_filter.matches(entry)  # type: ignore[union-attr]

        filters.append(time_filter)

    # Update buffer
    buffer.update_filters(filters)

    # Recalculate error/warning counts and line count from filtered entries
    if status is not None:
        error_count, warning_count = buffer.get_filtered_error_warning_counts()
        status.error_count = error_count
        status.warning_count = warning_count
        status.set_total_lines(buffer.filtered_count)


def _handle_help_command(
    args: list[str],
    buffer: TailBuffer | None,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'help' command to show available commands and shortcuts.

    Subcommands:
        help keys - Show keybinding reference

    Args:
        args: Command arguments (e.g., ['keys'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    # Handle 'help keys' subcommand
    if args and args[0].lower() == "keys":
        return _handle_help_keys_command(buffer, log_widget)

    # Build styled help text
    lines: list[tuple[str, str]] = []

    # Navigation section
    lines.append(("bold fg:ansicyan", "Navigation\n"))
    nav_keys = [
        ("Up/Down", "Scroll 1 line"),
        ("PgUp/PgDn", "Scroll full page"),
        ("Ctrl+u/d", "Scroll half page"),
        ("Ctrl+b/f", "Scroll full page"),
        ("Home", "Go to top"),
        ("End", "Go to bottom (resume FOLLOW mode)"),
    ]
    for key, desc in nav_keys:
        lines.append(("fg:ansigreen", f"  {key:<12} "))
        lines.append(("", f"{desc}\n"))

    lines.append(("", "\n"))
    lines.append(("bold fg:ansicyan", "Utility Keys\n"))
    utility_keys = [
        ("Ctrl+L", "Redraw screen"),
        ("F12", "Toggle debug overlay"),
        ("Ctrl+C", "Exit tail mode"),
    ]
    for key, desc in utility_keys:
        lines.append(("fg:ansigreen", f"  {key:<12} "))
        lines.append(("", f"{desc}\n"))

    # Commands section
    lines.append(("", "\n"))
    lines.append(("bold fg:ansicyan", "Commands\n"))
    commands = [
        ("help", "Show this help"),
        ("help keys", "Show keybinding reference"),
        ("pause", "Enter PAUSED mode"),
        ("follow", "Resume FOLLOW mode"),
        ("level <lvl>", "Filter by level (e.g., 'level error,warning')"),
        ("filter /re/", "Filter by regex pattern"),
        ("since <time>", "Show entries since time (e.g., '5m', '14:30')"),
        ("until <time>", "Show entries until time"),
        ("between s e", "Show entries in time range"),
        ("slow <ms>", "Set slow query threshold"),
        ("clear", "Clear all filters"),
        ("errors", "Show error statistics"),
        ("connections", "Show connection statistics"),
        ("stop/exit/q", "Exit tail mode"),
    ]
    for cmd, desc in commands:
        lines.append(("fg:ansiyellow", f"  {cmd:<12} "))
        lines.append(("", f"{desc}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled help to log
        log_widget.write_line("[bold cyan]Navigation[/bold cyan]")
        for key, desc in nav_keys:
            log_widget.write_line(f"  [green]{key:<12}[/green] [dim]{desc}[/dim]")
        log_widget.write_line("")
        log_widget.write_line("[bold cyan]Utility Keys[/bold cyan]")
        for key, desc in utility_keys:
            log_widget.write_line(f"  [green]{key:<12}[/green] [dim]{desc}[/dim]")
        log_widget.write_line("")
        log_widget.write_line("[bold cyan]Commands[/bold cyan]")
        for cmd, desc in commands:
            log_widget.write_line(f"  [yellow]{cmd:<12}[/yellow] [dim]{desc}[/dim]")
    return True


def _handle_help_keys_command(buffer: TailBuffer | None, log_widget: TailLog | None = None) -> bool:
    """Handle 'help keys' command to show keybinding reference.

    Args:
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    from pgtail_py.tail_help import KEYBINDINGS, format_keybindings_text

    if buffer is not None:
        # Format for prompt_toolkit
        keybindings_text = format_keybindings_text()
        lines: list[tuple[str, str]] = []
        for line in keybindings_text.split("\n"):
            lines.append(("", f"{line}\n"))
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled keybindings to log
        for category, bindings in KEYBINDINGS.items():
            log_widget.write_line(f"[bold cyan]{category}[/bold cyan]")
            for key, desc in bindings:
                log_widget.write_line(f"  [green]{key:<16}[/green] [dim]{desc}[/dim]")
    return True
