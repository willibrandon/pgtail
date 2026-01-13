"""Unit tests for REPL toolbar formatting.

Tests for:
- T010-T012: User Story 1 - Instance count display
- T016-T021: User Story 2 - Filter display
- T029-T030: User Story 3 - Theme display
- T033-T034: User Story 4 - Shell mode indicator
- T038-T040: Edge cases (NO_COLOR, truncation, special chars)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.filter import LogLevel
from pgtail_py.repl_toolbar import _format_filters, create_toolbar_func


# Helper to create a mock AppState
def create_mock_state(
    instances: list | None = None,
    shell_mode: bool = False,
    active_levels: set[LogLevel] | None = None,
    has_filters: bool = False,
    time_filter_active: bool = False,
    time_filter_desc: str = "",
    slow_enabled: bool = False,
    slow_warning_ms: int = 100,
    theme_name: str = "dark",
    regex_filters: list | None = None,
) -> MagicMock:
    """Create a mock AppState with configurable values."""
    state = MagicMock()
    state.instances = instances if instances is not None else []
    state.shell_mode = shell_mode
    state.active_levels = active_levels

    # Regex filter state
    state.regex_state = MagicMock()
    state.regex_state.has_filters.return_value = has_filters
    if regex_filters:
        state.regex_state.includes = regex_filters
        state.regex_state.excludes = []
        state.regex_state.ands = []
    else:
        state.regex_state.includes = []
        state.regex_state.excludes = []
        state.regex_state.ands = []

    # Time filter
    state.time_filter = MagicMock()
    state.time_filter.is_active.return_value = time_filter_active
    state.time_filter.format_description.return_value = time_filter_desc

    # Slow query config
    state.slow_query_config = MagicMock()
    state.slow_query_config.enabled = slow_enabled
    state.slow_query_config.warning_ms = slow_warning_ms

    # Theme manager
    state.theme_manager = MagicMock()
    state.theme_manager.current_theme = MagicMock()
    state.theme_manager.current_theme.name = theme_name

    return state


class TestFormatFilters:
    """Tests for _format_filters function."""

    def test_no_filters_returns_empty(self) -> None:
        """Test that no filters returns empty string (T021)."""
        state = create_mock_state(
            active_levels=None,  # All levels
            has_filters=False,
            time_filter_active=False,
            slow_enabled=False,
        )

        result = _format_filters(state)
        assert result == ""

    def test_level_filter_formatted(self) -> None:
        """Test level filter formatting (T016)."""
        state = create_mock_state(
            active_levels={LogLevel.ERROR, LogLevel.FATAL},
            has_filters=False,
            time_filter_active=False,
            slow_enabled=False,
        )

        result = _format_filters(state)
        assert "levels:" in result
        assert "ERROR" in result
        assert "FATAL" in result

    def test_level_filter_all_levels_hidden(self) -> None:
        """Test level filter hidden when all levels selected."""
        state = create_mock_state(
            active_levels=LogLevel.all_levels(),
            has_filters=False,
            time_filter_active=False,
            slow_enabled=False,
        )

        result = _format_filters(state)
        assert "levels:" not in result

    def test_regex_filter_formatted(self) -> None:
        """Test regex filter formatting (T017)."""
        mock_filter = MagicMock()
        mock_filter.pattern = "deadlock"
        mock_filter.case_sensitive = False  # case_sensitive=False means case-insensitive (add 'i')

        state = create_mock_state(
            active_levels=None,
            has_filters=True,
            time_filter_active=False,
            slow_enabled=False,
            regex_filters=[mock_filter],
        )

        result = _format_filters(state)
        assert "filter:/deadlock/i" in result

    def test_regex_filter_case_sensitive(self) -> None:
        """Test regex filter without case-insensitive flag."""
        mock_filter = MagicMock()
        mock_filter.pattern = "ERROR"
        mock_filter.case_sensitive = True  # case_sensitive=True means NO 'i' flag

        state = create_mock_state(
            active_levels=None,
            has_filters=True,
            time_filter_active=False,
            slow_enabled=False,
            regex_filters=[mock_filter],
        )

        result = _format_filters(state)
        assert "filter:/ERROR/" in result
        assert "/i" not in result.replace("filter:/ERROR/", "")

    def test_regex_filter_multiple_shows_more_indicator(self) -> None:
        """Test multiple regex filters show '+N more' indicator."""
        mock_filter1 = MagicMock()
        mock_filter1.pattern = "first"
        mock_filter1.case_sensitive = True  # No 'i' flag

        mock_filter2 = MagicMock()
        mock_filter2.pattern = "second"
        mock_filter2.case_sensitive = True  # No 'i' flag

        state = create_mock_state(
            active_levels=None,
            has_filters=True,
            time_filter_active=False,
            slow_enabled=False,
            regex_filters=[mock_filter1, mock_filter2],
        )

        result = _format_filters(state)
        assert "filter:/first/" in result
        assert "+1 more" in result

    def test_time_filter_formatted(self) -> None:
        """Test time filter formatting (T018)."""
        state = create_mock_state(
            active_levels=None,
            has_filters=False,
            time_filter_active=True,
            time_filter_desc="since 1h ago",
            slow_enabled=False,
        )

        result = _format_filters(state)
        assert "since 1h ago" in result

    def test_slow_query_threshold_formatted(self) -> None:
        """Test slow query threshold formatting (T019)."""
        state = create_mock_state(
            active_levels=None,
            has_filters=False,
            time_filter_active=False,
            slow_enabled=True,
            slow_warning_ms=200,
        )

        result = _format_filters(state)
        assert "slow:>200ms" in result

    def test_slow_query_threshold_default_hidden(self) -> None:
        """Test slow query threshold hidden when at default (100ms)."""
        state = create_mock_state(
            active_levels=None,
            has_filters=False,
            time_filter_active=False,
            slow_enabled=True,
            slow_warning_ms=100,  # Default value
        )

        result = _format_filters(state)
        assert "slow:" not in result

    def test_multiple_filters_combined(self) -> None:
        """Test multiple filters combined (T020)."""
        mock_filter = MagicMock()
        mock_filter.pattern = "test"
        mock_filter.case_sensitive = True  # No 'i' flag

        state = create_mock_state(
            active_levels={LogLevel.ERROR},
            has_filters=True,
            time_filter_active=True,
            time_filter_desc="since 5m ago",
            slow_enabled=True,
            slow_warning_ms=200,
            regex_filters=[mock_filter],
        )

        result = _format_filters(state)
        assert "levels:ERROR" in result
        assert "filter:/test/" in result
        assert "since 5m ago" in result
        assert "slow:>200ms" in result

    def test_regex_special_characters_displayed_as_is(self) -> None:
        """Test regex with special chars displayed as-is (T040)."""
        mock_filter = MagicMock()
        mock_filter.pattern = "test.*pattern"
        mock_filter.case_sensitive = True  # No 'i' flag

        state = create_mock_state(
            active_levels=None,
            has_filters=True,
            time_filter_active=False,
            slow_enabled=False,
            regex_filters=[mock_filter],
        )

        result = _format_filters(state)
        assert "filter:/test.*pattern/" in result


class TestCreateToolbarFunc:
    """Tests for toolbar function creation."""

    def test_shell_mode_display(self) -> None:
        """Test shell mode displays 'SHELL' indicator (T033)."""
        state = create_mock_state(shell_mode=True)

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("SHELL" in text for _, text in result)
        assert any("Press Escape to exit" in text for _, text in result)

    def test_shell_mode_with_no_color(self) -> None:
        """Test shell mode with NO_COLOR."""
        state = create_mock_state(shell_mode=True)

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=True):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # Should be plain text
        assert len(result) == 1
        assert result[0][0] == ""  # No style
        assert "SHELL" in result[0][1]
        assert "Press Escape to exit" in result[0][1]

    def test_return_to_normal_after_shell_mode(self) -> None:
        """Test toolbar returns to normal display after shell mode exit (T034)."""
        state = create_mock_state(
            shell_mode=False,
            instances=[MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # Should show normal idle mode content
        assert any("1 instance" in text for _, text in result)
        assert not any("SHELL" in text for _, text in result)

    def test_instance_count_singular(self) -> None:
        """Test singular grammar for 1 instance (T011)."""
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("1 instance" in text for _, text in result)
        assert not any("instances" in text for _, text in result)

    def test_instance_count_plural(self) -> None:
        """Test plural grammar for multiple instances (T010)."""
        state = create_mock_state(
            instances=[MagicMock(), MagicMock(), MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("3 instances" in text for _, text in result)

    def test_no_instances_warning(self) -> None:
        """Test 'No instances' warning with refresh hint (T012)."""
        state = create_mock_state(
            instances=[],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("No instances" in text for _, text in result)
        assert any("refresh" in text for _, text in result)

    def test_no_instances_warning_style(self) -> None:
        """Test 'No instances' uses warning style class."""
        state = create_mock_state(
            instances=[],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # Check that warning style is used
        warning_parts = [(style, text) for style, text in result if "No instances" in text]
        assert len(warning_parts) > 0
        assert "class:toolbar.warning" in warning_parts[0][0]

    def test_theme_name_display(self) -> None:
        """Test theme name displayed (T029)."""
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="monokai",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        assert any("Theme: monokai" in text for _, text in result)

    def test_theme_list_unchanged(self) -> None:
        """Test theme display unchanged on theme list (T030)."""
        # This tests that reading theme_manager.current_theme.name works correctly
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result1 = toolbar_func()

        # Simulate 'theme list' command (doesn't change theme)
        # Theme name should remain the same
        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            result2 = toolbar_func()

        # Both should show same theme
        assert any("Theme: dark" in text for _, text in result1)
        assert any("Theme: dark" in text for _, text in result2)

    def test_long_theme_name_truncation(self) -> None:
        """Test long theme name truncated to 15 chars (T039)."""
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="verylongthemenamethatexceedslimit",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # Find the theme display part
        theme_texts = [text for _, text in result if "Theme:" in text]
        assert len(theme_texts) > 0

        # Theme name should be truncated with ellipsis
        theme_text = theme_texts[0]
        # Extract theme name after "Theme: "
        theme_name_part = theme_text.split("Theme: ")[1].strip()
        assert len(theme_name_part) <= 16  # 15 chars + ellipsis
        assert "…" in theme_name_part or len(theme_name_part) <= 15

    def test_no_color_support(self) -> None:
        """Test NO_COLOR environment variable support (T038)."""
        state = create_mock_state(
            instances=[MagicMock(), MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=True):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # All parts should have empty style (no color)
        for style, text in result:
            assert style == "", f"Expected no style, got '{style}' for text '{text}'"

    def test_filter_section_visibility(self) -> None:
        """Test filter section hidden when no filters (T021 verification)."""
        state = create_mock_state(
            instances=[MagicMock()],
            active_levels=None,  # All levels
            has_filters=False,
            time_filter_active=False,
            slow_enabled=False,
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        # Should have instance count and theme, but no filter section
        full_text = "".join(text for _, text in result)
        assert "instance" in full_text
        assert "Theme:" in full_text
        assert "levels:" not in full_text
        assert "filter:" not in full_text

    def test_filter_section_visible_with_filters(self) -> None:
        """Test filter section visible when filters configured."""
        mock_filter = MagicMock()
        mock_filter.pattern = "error"
        mock_filter.case_sensitive = False  # case_sensitive=False means add 'i' flag

        state = create_mock_state(
            instances=[MagicMock()],
            active_levels={LogLevel.ERROR},
            has_filters=True,
            time_filter_active=False,
            slow_enabled=False,
            theme_name="dark",
            regex_filters=[mock_filter],
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        full_text = "".join(text for _, text in result)
        assert "levels:ERROR" in full_text
        assert "filter:/error/i" in full_text

    def test_bullet_separator_between_sections(self) -> None:
        """Test bullet separator (•) between toolbar sections (T043)."""
        mock_filter = MagicMock()
        mock_filter.pattern = "test"
        mock_filter.case_sensitive = True  # No 'i' flag

        state = create_mock_state(
            instances=[MagicMock()],
            has_filters=True,
            theme_name="dark",
            regex_filters=[mock_filter],
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        full_text = "".join(text for _, text in result)
        # Should have bullet separators between sections
        assert "•" in full_text

    def test_style_classes_used(self) -> None:
        """Test appropriate style classes are used for different elements."""
        mock_filter = MagicMock()
        mock_filter.pattern = "test"
        mock_filter.case_sensitive = True  # No 'i' flag

        state = create_mock_state(
            instances=[MagicMock()],
            has_filters=True,
            theme_name="dark",
            regex_filters=[mock_filter],
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)
            result = toolbar_func()

        styles_used = [style for style, _ in result]

        # Should use various toolbar style classes
        assert any("class:toolbar" in s for s in styles_used)
        assert any("class:toolbar.dim" in s for s in styles_used)
        assert any("class:toolbar.filter" in s for s in styles_used)


class TestToolbarDynamicUpdates:
    """Tests for toolbar dynamic update behavior."""

    def test_toolbar_reflects_state_changes(self) -> None:
        """Test toolbar updates when state changes."""
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)

            # Initial state
            result1 = toolbar_func()
            assert any("1 instance" in text for _, text in result1)

            # Simulate state change - add more instances
            state.instances = [MagicMock(), MagicMock()]

            # Toolbar should reflect new state
            result2 = toolbar_func()
            assert any("2 instances" in text for _, text in result2)

    def test_toolbar_reflects_theme_change(self) -> None:
        """Test toolbar updates when theme changes."""
        state = create_mock_state(
            instances=[MagicMock()],
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)

            # Initial theme
            result1 = toolbar_func()
            assert any("Theme: dark" in text for _, text in result1)

            # Simulate theme change
            state.theme_manager.current_theme.name = "monokai"

            # Toolbar should show new theme
            result2 = toolbar_func()
            assert any("Theme: monokai" in text for _, text in result2)

    def test_toolbar_reflects_filter_change(self) -> None:
        """Test toolbar updates when filters change."""
        state = create_mock_state(
            instances=[MagicMock()],
            active_levels=None,
            has_filters=False,
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)

            # Initial - no filters
            result1 = toolbar_func()
            full_text1 = "".join(text for _, text in result1)
            assert "levels:" not in full_text1

            # Simulate filter change
            state.active_levels = {LogLevel.ERROR}

            # Toolbar should show filter
            result2 = toolbar_func()
            full_text2 = "".join(text for _, text in result2)
            assert "levels:ERROR" in full_text2

    def test_toolbar_reflects_shell_mode_toggle(self) -> None:
        """Test toolbar updates when shell mode toggles."""
        state = create_mock_state(
            instances=[MagicMock()],
            shell_mode=False,
            theme_name="dark",
        )

        with patch("pgtail_py.repl_toolbar.is_color_disabled", return_value=False):
            toolbar_func = create_toolbar_func(state)

            # Initial - idle mode
            result1 = toolbar_func()
            assert not any("SHELL" in text for _, text in result1)

            # Enter shell mode
            state.shell_mode = True

            # Toolbar should show shell indicator
            result2 = toolbar_func()
            assert any("SHELL" in text for _, text in result2)

            # Exit shell mode
            state.shell_mode = False

            # Toolbar should return to idle
            result3 = toolbar_func()
            assert not any("SHELL" in text for _, text in result3)
