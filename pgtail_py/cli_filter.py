"""Log filtering commands for level, regex, and field patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.field_filter import (
    FIELD_ALIASES,
    get_available_field_names,
    resolve_field_name,
)
from pgtail_py.filter import LogLevel, parse_levels
from pgtail_py.format_detector import LogFormat
from pgtail_py.regex_filter import (
    FilterType,
    Highlight,
    RegexFilter,
    parse_filter_arg,
)

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def levels_command(state: AppState, args: list[str]) -> None:
    """Handle the 'levels' command - set or display log level filter.

    Args:
        state: Current application state.
        args: Level names to filter by, or empty to show current.
    """
    # No args - show current filter
    if not args:
        if state.active_levels is None:
            print("Filter: ALL (showing all levels)")
        else:
            names = sorted(level.name for level in state.active_levels)
            print(f"Filter: {' '.join(names)}")
        print()
        print("Usage: levels [LEVEL...]  Set filter to specific levels")
        print("       levels ALL         Show all levels")
        print()
        print(f"Available levels: {' '.join(LogLevel.names())}")
        return

    # Parse levels
    new_levels, invalid = parse_levels(args)

    # Report any invalid level names
    if invalid:
        print(f"Unknown level(s): {', '.join(invalid)}")
        print(f"Valid levels: {' '.join(LogLevel.names())}")
        return

    # Update filter
    state.active_levels = new_levels

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_levels(new_levels)

    # Confirm change
    if new_levels is None:
        print("Filter cleared - showing all levels")
    else:
        names = sorted(level.name for level in new_levels)
        print(f"Filter set: {' '.join(names)}")


def _is_field_filter_arg(arg: str) -> bool:
    """Check if arg looks like a field filter (field=value syntax).

    Args:
        arg: The argument to check

    Returns:
        True if arg contains = and the part before = is a valid field name
    """
    if "=" not in arg:
        return False

    field_part = arg.split("=", 1)[0].lower()
    return field_part in FIELD_ALIASES


def handle_filter_field(state: AppState, arg: str) -> None:
    """Handle field=value filter syntax.

    Args:
        state: Current application state.
        arg: Filter argument in field=value format.
    """
    # Check if tailing and warn about text format
    if state.tailer and state.tailer.format == LogFormat.TEXT:
        print("Warning: Field filtering is only effective for CSV/JSON log formats.")
        print("Text format logs don't have structured fields.")
        print()

    # Parse field=value
    parts = arg.split("=", 1)
    if len(parts) != 2:
        print(f"Invalid field filter syntax: {arg}")
        print("Use field=value syntax (e.g., filter app=myapp)")
        return

    field_name, value = parts
    value = value.strip()

    if not value:
        print(f"Empty value for field filter: {arg}")
        return

    # Resolve and add the filter
    try:
        state.field_filter.add(field_name, value)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_field_filter(state.field_filter)

    resolved = resolve_field_name(field_name)
    print(f"Field filter set: {resolved}={value}")


def filter_command(state: AppState, args: list[str]) -> None:
    """Handle the 'filter' command - set or display regex and field filters.

    Args:
        state: Current application state.
        args: Filter pattern or subcommand.
    """
    # No args - show current filter status
    if not args:
        has_regex = state.regex_state.has_filters()
        has_field = state.field_filter.is_active()

        if not has_regex and not has_field:
            print("No filters active")
        else:
            if has_regex:
                print("Active regex filters:")
                for f in state.regex_state.includes:
                    cs = " (case-sensitive)" if f.case_sensitive else ""
                    print(f"  include: /{f.pattern}/{cs}")
                for f in state.regex_state.excludes:
                    cs = " (case-sensitive)" if f.case_sensitive else ""
                    print(f"  exclude: /{f.pattern}/{cs}")
                for f in state.regex_state.ands:
                    cs = " (case-sensitive)" if f.case_sensitive else ""
                    print(f"  and: /{f.pattern}/{cs}")
            if has_field:
                print(state.field_filter.format_status())
        print()
        print("Usage: filter /pattern/       Include only matching lines (regex)")
        print("       filter -/pattern/      Exclude matching lines")
        print("       filter +/pattern/      Add OR pattern")
        print("       filter &/pattern/      Add AND pattern")
        print("       filter /pattern/c      Case-sensitive match")
        print("       filter field=value     Filter by field (CSV/JSON only)")
        print("       filter clear           Clear all filters")
        print()
        print(f"Available fields: {', '.join(get_available_field_names())}")
        return

    arg = args[0]

    # Handle 'clear' subcommand
    if arg.lower() == "clear":
        state.regex_state.clear_filters()
        state.field_filter.clear()
        if state.tailer:
            state.tailer.update_field_filter(state.field_filter)
        print("All filters cleared")
        return

    # Check if this is a field filter (field=value syntax)
    if _is_field_filter_arg(arg):
        handle_filter_field(state, arg)
        return

    # Determine filter type based on prefix
    if arg.startswith("-/"):
        filter_type = FilterType.EXCLUDE
        pattern_arg = arg[1:]  # Remove '-' prefix, keep the /pattern/
    elif arg.startswith("+/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg[1:]  # Remove '+' prefix
    elif arg.startswith("&/"):
        filter_type = FilterType.AND
        pattern_arg = arg[1:]  # Remove '&' prefix
    elif arg.startswith("/"):
        filter_type = FilterType.INCLUDE
        pattern_arg = arg
    else:
        print(f"Invalid filter syntax: {arg}")
        print("Use /pattern/ syntax (e.g., filter /error/)")
        return

    # Parse the pattern
    try:
        pattern, case_sensitive = parse_filter_arg(pattern_arg)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Validate regex
    try:
        regex_filter = RegexFilter.create(pattern, filter_type, case_sensitive)
    except re.error as e:
        print(f"Invalid regex pattern: {e}")
        return

    # Apply the filter
    if filter_type == FilterType.INCLUDE and arg.startswith("/"):
        # Plain /pattern/ sets single include filter (replaces previous includes)
        state.regex_state.set_include(regex_filter)
        cs = " (case-sensitive)" if case_sensitive else ""
        print(f"Filter set: /{pattern}/{cs}")
    else:
        # +, -, & add to existing filters
        state.regex_state.add_filter(regex_filter)
        type_label = filter_type.value
        cs = " (case-sensitive)" if case_sensitive else ""
        print(f"Filter added ({type_label}): /{pattern}/{cs}")

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_regex_state(state.regex_state)


def highlight_command(state: AppState, args: list[str]) -> None:
    """Handle the 'highlight' command - set or display text highlights.

    Args:
        state: Current application state.
        args: Highlight pattern or subcommand.
    """
    # No args - show current highlight status
    if not args:
        if not state.regex_state.has_highlights():
            print("No highlights active")
        else:
            print("Active highlights:")
            for h in state.regex_state.highlights:
                cs = " (case-sensitive)" if h.case_sensitive else ""
                print(f"  /{h.pattern}/{cs}")
        print()
        print("Usage: highlight /pattern/   Highlight matching text (yellow background)")
        print("       highlight /pattern/c  Case-sensitive highlight")
        print("       highlight clear       Clear all highlights")
        return

    arg = args[0]

    # Handle 'clear' subcommand
    if arg.lower() == "clear":
        state.regex_state.clear_highlights()
        print("Highlights cleared")
        return

    # Parse the pattern
    if not arg.startswith("/"):
        print(f"Invalid highlight syntax: {arg}")
        print("Use /pattern/ syntax (e.g., highlight /error/)")
        return

    try:
        pattern, case_sensitive = parse_filter_arg(arg)
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Validate regex
    try:
        highlight = Highlight.create(pattern, case_sensitive)
    except re.error as e:
        print(f"Invalid regex pattern: {e}")
        return

    # Add the highlight
    state.regex_state.highlights.append(highlight)
    cs = " (case-sensitive)" if case_sensitive else ""
    print(f"Highlight added: /{pattern}/{cs}")

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_regex_state(state.regex_state)
