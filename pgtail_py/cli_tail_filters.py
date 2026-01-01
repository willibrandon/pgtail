"""Filter command handlers for tail mode.

This module provides handlers for filter commands (level, filter, since,
until, between, slow, clear) executed within the tail mode interface.
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


def handle_level_command(
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
        rebuild_buffer_filters(buffer, state, status)

    # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    return True


def handle_filter_command(
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
            rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid pattern: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def handle_since_command(
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
            rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def handle_until_command(
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
            rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def handle_between_command(
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
            rebuild_buffer_filters(buffer, state, status)

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if buffer is not None:
            error_msg = FormattedText([("class:error", f"Invalid time: {e}")])
            buffer.insert_command_output(error_msg)

    return True


def handle_slow_command(
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


def handle_clear_command(
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


def rebuild_buffer_filters(
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
