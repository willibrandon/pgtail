"""Log filtering commands for level, regex, and field patterns."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text

from pgtail_py.cli_highlight import (
    format_highlight_list,
    handle_highlight_add,
    handle_highlight_disable,
    handle_highlight_enable,
    handle_highlight_export,
    handle_highlight_import,
    handle_highlight_off,
    handle_highlight_on,
    handle_highlight_preview,
    handle_highlight_remove,
    handle_highlight_reset,
)
from pgtail_py.cli_utils import warn
from pgtail_py.colors import get_style
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
from pgtail_py.tail_rich import reset_highlighter_chain

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
    """Handle the 'highlight' command - semantic highlighters and regex patterns.

    Subcommands:
        list              Show all semantic highlighters with status
        enable <name>     Enable a semantic highlighter
        disable <name>    Disable a semantic highlighter
        add <name> <pattern> [--style <style>] [--priority <num>]
                          Add a custom regex highlighter
        remove <name>     Remove a custom highlighter
        /pattern/         Add regex highlight pattern (legacy)
        clear             Clear regex highlight patterns (legacy)

    Args:
        state: Current application state.
        args: Subcommand or highlight pattern.
    """
    # No args - show semantic highlighter list
    if not args:
        formatted = format_highlight_list(state.highlighting_config)
        print_formatted_text(formatted, style=get_style(state.theme_manager))
        return

    arg = args[0].lower()

    # Handle 'list' subcommand - show semantic highlighters
    if arg == "list":
        formatted = format_highlight_list(state.highlighting_config)
        print_formatted_text(formatted, style=get_style(state.theme_manager))
        return

    # Handle 'on' subcommand - enable all highlighting
    if arg == "on":
        success, message = handle_highlight_on(state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'off' subcommand - disable all highlighting
    if arg == "off":
        success, message = handle_highlight_off(state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'enable' subcommand
    if arg == "enable":
        if len(args) < 2:
            print("Usage: highlight enable <name>")
            return
        name = args[1]
        success, message = handle_highlight_enable(name, state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'disable' subcommand
    if arg == "disable":
        if len(args) < 2:
            print("Usage: highlight disable <name>")
            return
        name = args[1]
        success, message = handle_highlight_disable(name, state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'add' subcommand - add custom highlighter
    if arg == "add":
        success, message = handle_highlight_add(args[1:], state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'remove' subcommand - remove custom highlighter
    if arg == "remove":
        if len(args) < 2:
            print("Usage: highlight remove <name>")
            return
        name = args[1]
        success, message = handle_highlight_remove(name, state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'clear' subcommand - clear legacy regex highlights
    if arg == "clear":
        state.regex_state.clear_highlights()
        print("Regex highlights cleared")
        return

    # Handle 'export' subcommand - export highlighting config
    if arg == "export":
        success, message = handle_highlight_export(args[1:], state.highlighting_config, warn)
        print(message)
        return

    # Handle 'import' subcommand - import highlighting config
    if arg == "import":
        success, message = handle_highlight_import(args[1:], state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Handle 'preview' subcommand - preview highlighting with samples
    if arg == "preview":
        success, output = handle_highlight_preview(
            state.highlighting_config,
            theme=state.theme_manager.current_theme,
            use_rich=False,
        )
        if isinstance(output, str):
            print(output)
        else:
            print_formatted_text(output, style=get_style(state.theme_manager))
        return

    # Handle 'reset' subcommand - reset all settings to defaults
    if arg == "reset":
        success, message = handle_highlight_reset(state.highlighting_config, warn)
        if success:
            reset_highlighter_chain()
        print(message)
        return

    # Legacy: Parse regex pattern
    original_arg = args[0]  # Use original case for pattern
    if not original_arg.startswith("/"):
        print(f"Unknown subcommand: {arg}")
        print()
        print("Usage: highlight list             Show semantic highlighters")
        print("       highlight on               Enable all highlighting")
        print("       highlight off              Disable all highlighting")
        print("       highlight enable <name>    Enable a highlighter")
        print("       highlight disable <name>   Disable a highlighter")
        print("       highlight add <name> <pattern> [--style <style>] [--priority <num>]")
        print("       highlight remove <name>    Remove custom highlighter")
        print("       highlight export [--file <path>]  Export config as TOML")
        print("       highlight import <path>    Import config from TOML")
        print("       highlight preview          Preview with sample lines")
        print("       highlight reset            Reset all settings to defaults")
        print("       highlight /pattern/        Add regex highlight (legacy)")
        print("       highlight clear            Clear regex highlights (legacy)")
        return

    try:
        pattern, case_sensitive = parse_filter_arg(original_arg)
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
    print(f"Regex highlight added: /{pattern}/{cs}")

    # Update tailer if currently tailing
    if state.tailer:
        state.tailer.update_regex_state(state.regex_state)
