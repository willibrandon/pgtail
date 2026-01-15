"""Tests for theme.py Theme.get_style() method (T034).

Tests cover:
- get_style with existing key
- get_style with missing key and default fallback
- get_style with missing key and custom fallback
"""

from __future__ import annotations

import pytest

from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_theme() -> Theme:
    """Create a test theme with various styles."""
    return Theme(
        name="test",
        description="Test theme",
        levels={
            "ERROR": ColorStyle(fg="red"),
            "WARNING": ColorStyle(fg="yellow"),
            "LOG": ColorStyle(fg="white"),
        },
        ui={
            "timestamp": ColorStyle(fg="gray"),
            "highlight": ColorStyle(fg="black", bg="yellow"),
            "hl_test": ColorStyle(fg="blue", bold=True),
            "hl_sqlstate_error": ColorStyle(fg="red", bold=True),
        },
    )


# =============================================================================
# Test get_style
# =============================================================================


class TestGetStyle:
    """Tests for Theme.get_style() method."""

    def test_get_style_existing_key(self, test_theme: Theme) -> None:
        """get_style should return style for existing key."""
        style = test_theme.get_style("hl_test")
        assert style is not None
        assert style.fg == "blue"
        assert style.bold is True

    def test_get_style_missing_key_default_fallback(
        self, test_theme: Theme
    ) -> None:
        """get_style should return None for missing key by default."""
        style = test_theme.get_style("nonexistent_key")
        assert style is None

    def test_get_style_missing_key_custom_fallback(
        self, test_theme: Theme
    ) -> None:
        """get_style should return custom fallback for missing key."""
        fallback = ColorStyle(fg="green")
        style = test_theme.get_style("nonexistent_key", fallback=fallback)
        assert style is fallback
        assert style.fg == "green"

    def test_get_style_ui_key(self, test_theme: Theme) -> None:
        """get_style should find keys in ui dict."""
        style = test_theme.get_style("timestamp")
        assert style is not None
        assert style.fg == "gray"

    def test_get_style_hl_prefix(self, test_theme: Theme) -> None:
        """get_style should work with hl_ prefixed keys."""
        style = test_theme.get_style("hl_sqlstate_error")
        assert style is not None
        assert style.fg == "red"
        assert style.bold is True

    def test_get_style_empty_fallback(self, test_theme: Theme) -> None:
        """get_style with empty ColorStyle fallback should return it."""
        fallback = ColorStyle()
        style = test_theme.get_style("missing", fallback=fallback)
        assert style is fallback
        assert style.fg is None
        assert style.bold is False
