"""Filter command handlers for tail mode.

This module provides handlers for filter commands (level, filter, since,
until, between, slow, clear) executed within the tail mode interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.filter import LogLevel, parse_levels

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus
    from pgtail_py.tailer import LogTailer


def handle_level_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'level' command to filter by log levels.

    Args:
        args: Level names (e.g., ['error', 'warning'] or ['error,warning'])
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    # Parse comma-separated levels
    level_args: list[str] = []
    for arg in args:
        level_args.extend(arg.split(","))

    levels, invalid = parse_levels(level_args)

    if invalid:
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

    # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    return True


def _is_field_filter_arg(arg: str) -> bool:
    """Check if arg looks like a field filter (field=value syntax).

    Args:
        arg: The argument to check

    Returns:
        True if arg contains = and the part before = is a valid field name
    """
    from pgtail_py.field_filter import FIELD_ALIASES

    if "=" not in arg:
        return False

    field_part = arg.split("=", 1)[0].lower()
    return field_part in FIELD_ALIASES


def handle_filter_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'filter' command for regex and field filtering.

    Supports full filter syntax matching REPL parity:
    - /pattern/     Include only matching lines
    - -/pattern/    Exclude matching lines
    - +/pattern/    Add OR pattern
    - &/pattern/    Add AND pattern
    - /pattern/c    Case-sensitive match
    - field=value   Filter by field (CSV/JSON only)
    - clear         Clear all filters

    Args:
        args: Pattern argument (e.g., ['/deadlock/'], ['-/noise/'], ['app=myapp'])
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    from pgtail_py.field_filter import resolve_field_name
    from pgtail_py.format_detector import LogFormat
    from pgtail_py.regex_filter import (
        FilterType,
        RegexFilter,
        parse_filter_arg,
    )

    if not args:
        # No pattern - show current filter status
        has_regex = state.regex_state.has_filters()
        has_field = state.field_filter.is_active()

        if log_widget is not None:
            if not has_regex and not has_field:
                log_widget.write_line("[dim]No filters active[/]")
            else:
                if has_regex:
                    for f in state.regex_state.includes:
                        cs = "c" if f.case_sensitive else ""
                        log_widget.write_line(f"[dim]include:[/] [cyan]/{f.pattern}/{cs}[/]")
                    for f in state.regex_state.excludes:
                        cs = "c" if f.case_sensitive else ""
                        log_widget.write_line(f"[dim]exclude:[/] [yellow]-/{f.pattern}/{cs}[/]")
                    for f in state.regex_state.ands:
                        cs = "c" if f.case_sensitive else ""
                        log_widget.write_line(f"[dim]and:[/] [green]&/{f.pattern}/{cs}[/]")
                if has_field:
                    log_widget.write_line(f"[dim]{state.field_filter.format_status()}[/]")
        return True

    arg = args[0]

    # Handle 'clear' subcommand
    if arg.lower() == "clear":
        state.regex_state.clear_filters()
        state.field_filter.clear()
        tailer.update_regex_state(None)
        tailer.update_field_filter(state.field_filter)
        status.set_regex_filter(None)
        if log_widget is not None:
            log_widget.write_line("[bold green]✓[/] All filters cleared")
        return True

    # Check if this is a field filter (field=value syntax)
    if _is_field_filter_arg(arg):
        # Warn about text format
        if tailer.format == LogFormat.TEXT and log_widget is not None:
            log_widget.write_line(
                "[yellow]Warning:[/] Field filtering only works for CSV/JSON logs"
            )

        # Parse field=value
        parts = arg.split("=", 1)
        if len(parts) == 2:
            field_name, value = parts
            value = value.strip()
            if value:
                try:
                    state.field_filter.add(field_name, value)
                    tailer.update_field_filter(state.field_filter)
                    resolved = resolve_field_name(field_name)
                    if log_widget is not None:
                        log_widget.write_line(
                            f"[bold green]✓[/] Field filter: [cyan]{resolved}={value}[/]"
                        )
                except ValueError as e:
                    if log_widget is not None:
                        log_widget.write_line(f"[bold red]✗[/] Error: {e}")
        return True

    # Determine filter type based on prefix
    if arg.startswith("-/"):
        filter_type = FilterType.EXCLUDE
        pattern_arg = arg[1:]  # Remove '-' prefix, keep the /pattern/
    elif arg.startswith("+/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg[1:]  # Remove '+' prefix (adds to existing includes)
    elif arg.startswith("&/"):
        filter_type = FilterType.AND
        pattern_arg = arg[1:]  # Remove '&' prefix
    elif arg.startswith("/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg
    else:
        if log_widget is not None:
            log_widget.write_line(f"[bold red]✗[/] Invalid filter syntax: {arg}")
            log_widget.write_line(
                "[dim]Use /pattern/, -/pattern/, +/pattern/, &/pattern/, or field=value[/]"
            )
        return True

    # Parse the pattern
    try:
        pattern, case_sensitive = parse_filter_arg(pattern_arg)
    except ValueError as e:
        if log_widget is not None:
            log_widget.write_line(f"[bold red]✗[/] Error: {e}")
        return True

    # Create and apply the filter
    try:
        regex_filter = RegexFilter.create(pattern, filter_type, case_sensitive)

        # Apply based on filter type
        if filter_type == FilterType.INCLUDE and arg.startswith("/"):
            # Plain /pattern/ sets single include filter (replaces previous includes)
            state.regex_state.includes = [regex_filter]
        elif filter_type == FilterType.INCLUDE:
            # +/pattern/ adds to existing includes (OR logic)
            state.regex_state.includes.append(regex_filter)
        elif filter_type == FilterType.EXCLUDE:
            # -/pattern/ adds to excludes
            state.regex_state.excludes.append(regex_filter)
        elif filter_type == FilterType.AND:
            # &/pattern/ adds to ands
            state.regex_state.ands.append(regex_filter)

        # Update tailer
        tailer.update_regex_state(state.regex_state)

        # Update status with first include pattern for display
        if state.regex_state.includes:
            status.set_regex_filter(state.regex_state.includes[0].pattern)
        else:
            status.set_regex_filter(None)

        # Show confirmation in Textual mode
        if log_widget is not None:
            type_str = {
                FilterType.INCLUDE: "include",
                FilterType.EXCLUDE: "exclude",
                FilterType.AND: "and",
            }.get(filter_type, "filter")
            cs = "c" if case_sensitive else ""
            log_widget.write_line(f"[bold green]✓[/] Filter {type_str}: [cyan]/{pattern}/{cs}[/]")

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception as e:
        if log_widget is not None:
            log_widget.write_line(f"[bold red]✗[/] Invalid pattern: {e}")

    return True


def handle_since_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'since' command for time filtering.

    Args:
        args: Time specification (e.g., ['5m'] or ['14:30'])
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    if not args:
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

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception:
        pass

    return True


def handle_until_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'until' command for time filtering.

    Args:
        args: Time specification
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    if not args:
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

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception:
        pass

    return True


def handle_between_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'between' command for time range filtering.

    Args:
        args: Start and end time specifications
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    if len(args) < 2:
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

        # Note: Textual mode rebuilds log in TailApp._handle_command() after this returns

    except Exception:
        pass

    return True


def handle_slow_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'slow' command for slow query threshold.

    Args:
        args: Threshold in ms
        status: TailStatus instance
        state: AppState instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    if not args:
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

    except ValueError:
        pass

    return True


def handle_clear_command(
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'clear' command to remove all filters.

    Args:
        status: TailStatus instance
        state: AppState instance
        tailer: LogTailer instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    from pgtail_py.regex_filter import FilterState
    from pgtail_py.time_filter import TimeFilter

    # Clear all filters in state
    state.active_levels = None
    state.regex_state = FilterState.empty()
    state.time_filter = TimeFilter.empty()
    state.field_filter.clear()  # Also clear field filters

    # Update tailer
    tailer.update_levels(None)
    tailer.update_regex_state(None)
    tailer.update_time_filter(None)
    tailer.update_field_filter(state.field_filter)  # Also update field filter

    # Update status
    status.set_level_filter(LogLevel.all_levels())
    status.set_regex_filter(None)
    status.set_time_filter(None)
    status.set_slow_threshold(None)

    # Textual mode: clear the log widget content
    if log_widget is not None:
        log_widget.clear()
        status.error_count = 0
        status.warning_count = 0
        status.set_total_lines(0)

    return True
