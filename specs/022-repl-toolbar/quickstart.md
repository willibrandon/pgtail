# Quickstart: REPL Bottom Toolbar Implementation

**Feature**: 022-repl-toolbar
**Date**: 2026-01-12

## Overview

This guide provides the implementation blueprint for adding a bottom toolbar to pgtail's REPL. The toolbar is always displayed.

## Implementation Order

```
1. themes/*.py    → Add toolbar styles to all built-in themes
2. repl_toolbar.py → NEW: Toolbar rendering logic
3. cli.py         → Integrate toolbar with PromptSession
4. Tests          → Unit tests
```

## Step 1: Theme Styles (themes/*.py)

Add to each built-in theme's `ui` dictionary:

```python
# Example for dark theme
ui={
    # ... existing styles ...
    "toolbar": ColorStyle(bg="#1a1a1a", fg="#cccccc"),
    "toolbar.dim": ColorStyle(bg="#1a1a1a", fg="#666666"),
    "toolbar.filter": ColorStyle(bg="#1a1a1a", fg="#55ffff"),
    "toolbar.warning": ColorStyle(bg="#1a1a1a", fg="#ffff55"),
    "toolbar.shell": ColorStyle(bg="#1a1a1a", fg="#ffffff", bold=True),
}
```

Repeat for: dark, light, high-contrast, monokai, solarized-dark, solarized-light

## Step 2: Toolbar Module (repl_toolbar.py)

Create new file `pgtail_py/repl_toolbar.py`:

```python
"""Bottom toolbar for REPL mode using prompt_toolkit."""

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
        # Check for NO_COLOR
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

    # Regex filter (first pattern only)
    if state.regex_state.has_filters():
        first_filter = state.regex_state.filters[0]
        pattern = first_filter.pattern
        flags = "i" if first_filter.case_insensitive else ""
        parts.append(f"filter:/{pattern}/{flags}")
        # Indicate additional filters
        extra = len(state.regex_state.filters) - 1
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
```

## Step 3: CLI Integration (cli.py)

Modify `main()` function:

```python
from pgtail_py.repl_toolbar import create_toolbar_func

def main() -> None:
    # ... existing initialization ...

    # Create toolbar function (always enabled)
    toolbar_func = create_toolbar_func(state)

    # Set up prompt session with history, key bindings, completer, and toolbar
    history_path = ensure_history_dir()
    bindings = _create_key_bindings(state)
    completer = PgtailCompleter(get_instances=lambda: state.instances)
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        completer=completer,
        bottom_toolbar=toolbar_func,  # ADD
        style=get_style(state.theme_manager),  # ADD (may already be present)
    )

    # ... rest unchanged ...
```

## Step 4: Tests

### Unit Tests (test_repl_toolbar.py)

```python
"""Unit tests for REPL toolbar formatting."""

import pytest
from unittest.mock import MagicMock, patch

from pgtail_py.repl_toolbar import create_toolbar_func, _format_filters


class TestFormatFilters:
    """Tests for _format_filters function."""

    def test_no_filters_returns_empty(self):
        state = MagicMock()
        state.active_levels = None  # All levels
        state.regex_state.has_filters.return_value = False
        state.time_filter.is_active.return_value = False
        state.slow_query_config.enabled = False

        result = _format_filters(state)
        assert result == ""

    def test_level_filter_formatted(self):
        from pgtail_py.filter import LogLevel

        state = MagicMock()
        state.active_levels = {LogLevel.ERROR, LogLevel.FATAL}
        state.regex_state.has_filters.return_value = False
        state.time_filter.is_active.return_value = False
        state.slow_query_config.enabled = False

        result = _format_filters(state)
        assert "levels:" in result
        assert "ERROR" in result
        assert "FATAL" in result


class TestCreateToolbarFunc:
    """Tests for toolbar function creation."""

    def test_shell_mode_display(self):
        state = MagicMock()
        state.shell_mode = True

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("SHELL" in text for _, text in result)

    def test_instance_count_singular(self):
        state = MagicMock()
        state.shell_mode = False
        state.instances = [MagicMock()]  # 1 instance
        state.theme_manager.current_theme.name = "dark"
        state.active_levels = None
        state.regex_state.has_filters.return_value = False
        state.time_filter.is_active.return_value = False
        state.slow_query_config.enabled = False

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("1 instance" in text for _, text in result)

    def test_no_instances_warning(self):
        state = MagicMock()
        state.shell_mode = False
        state.instances = []
        state.theme_manager.current_theme.name = "dark"
        state.active_levels = None
        state.regex_state.has_filters.return_value = False
        state.time_filter.is_active.return_value = False
        state.slow_query_config.enabled = False

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("No instances" in text for _, text in result)
        assert any("refresh" in text for _, text in result)
```

## File Size Estimate

- `repl_toolbar.py`: ~120 lines
- CLI changes: ~10 lines
- Theme changes: ~30 lines (5 lines × 6 themes)
- Tests: ~100 lines

Total new code: ~260 lines, well under 900 LOC limit per file.

## Verification Checklist

- [ ] Instance count displays correctly (0, 1, N)
- [ ] "No instances" shows warning style with refresh hint
- [ ] Level filter appears when configured
- [ ] Regex filter appears when configured
- [ ] Time filter appears when configured
- [ ] Slow query threshold appears when customized
- [ ] Theme name displays correctly
- [ ] Shell mode shows distinct indicator
- [ ] NO_COLOR disables styling but keeps content
- [ ] Toolbar updates after `refresh` command
- [ ] Toolbar updates after `theme` command
- [ ] All 6 built-in themes have toolbar styles
