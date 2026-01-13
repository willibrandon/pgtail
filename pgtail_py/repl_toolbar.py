"""Bottom toolbar for REPL mode using prompt_toolkit.

Provides a persistent status bar showing:
- Instance count (always)
- Active filters (when configured)
- Current theme name
- Shell mode indicator (when active)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.utils import is_color_disabled

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def create_toolbar_func(state: AppState):
    """Create a toolbar function that captures state.

    Args:
        state: Application state to read from.

    Returns:
        Callable that returns list of (style, text) tuples for bottom_toolbar.
    """

    def get_toolbar() -> list[tuple[str, str]]:
        """Generate toolbar content based on current state.

        Returns:
            List of (style_class, text) tuples for prompt_toolkit rendering.
        """
        no_color = is_color_disabled()
        parts: list[tuple[str, str]] = []

        # Shell mode - special display
        if state.shell_mode:
            if no_color:
                return [("", " SHELL • Press Escape to exit ")]
            parts.append(("class:toolbar.shell", " SHELL "))
            parts.append(("class:toolbar.dim", "• Press Escape to exit "))
            return parts

        # === Idle Mode ===

        # Instance count
        count = len(state.instances)
        if count == 0:
            if no_color:
                parts.append(("", " No instances (run 'refresh') "))
            else:
                parts.append(("class:toolbar.warning", " No instances "))
                parts.append(("class:toolbar.dim", "(run 'refresh') "))
        elif count == 1:
            style = "" if no_color else "class:toolbar"
            parts.append((style, " 1 instance "))
        else:
            style = "" if no_color else "class:toolbar"
            parts.append((style, f" {count} instances "))

        # Filters (only if configured)
        filters = _format_filters(state)
        if filters:
            if no_color:
                parts.append(("", f"• {filters} "))
            else:
                parts.append(("class:toolbar.dim", "• "))
                parts.append(("class:toolbar.filter", filters))
                parts.append(("class:toolbar", " "))

        # Theme
        if state.theme_manager.current_theme:
            theme_name = state.theme_manager.current_theme.name
            # Truncate long theme names (15 chars max)
            if len(theme_name) > 15:
                theme_name = theme_name[:14] + "…"
            if no_color:
                parts.append(("", f"• Theme: {theme_name} "))
            else:
                parts.append(("class:toolbar.dim", "• "))
                parts.append(("class:toolbar", f"Theme: {theme_name} "))

        return parts

    return get_toolbar


def _format_filters(state: AppState) -> str:
    """Format active filters for toolbar display.

    Only includes filters that are actually configured (not defaults).

    Args:
        state: Application state.

    Returns:
        Space-separated filter string, or empty string if no filters.
    """
    from pgtail_py.filter import LogLevel

    parts: list[str] = []

    # Level filter (only if not ALL levels)
    if state.active_levels is not None and state.active_levels != LogLevel.all_levels():
        level_names = ",".join(sorted(lvl.name for lvl in state.active_levels))
        parts.append(f"levels:{level_names}")

    # Regex filter (first pattern only, show all filter types)
    if state.regex_state.has_filters():
        # Get first filter from any filter type
        first_filter = None
        if state.regex_state.includes:
            first_filter = state.regex_state.includes[0]
        elif state.regex_state.excludes:
            first_filter = state.regex_state.excludes[0]
        elif state.regex_state.ands:
            first_filter = state.regex_state.ands[0]

        if first_filter:
            pattern = first_filter.pattern
            # case_sensitive=False means case-insensitive (add 'i' flag)
            flags = "" if first_filter.case_sensitive else "i"
            parts.append(f"filter:/{pattern}/{flags}")
            # Indicate additional filters
            total_filters = (
                len(state.regex_state.includes)
                + len(state.regex_state.excludes)
                + len(state.regex_state.ands)
            )
            extra = total_filters - 1
            if extra > 0:
                parts[-1] += f" +{extra} more"

    # Time filter
    if state.time_filter.is_active():
        desc = state.time_filter.format_description()
        parts.append(desc)

    # Slow query threshold (only if customized from default 100ms)
    if state.slow_query_config.enabled and state.slow_query_config.warning_ms != 100:
        parts.append(f"slow:>{state.slow_query_config.warning_ms}ms")

    return " ".join(parts)
