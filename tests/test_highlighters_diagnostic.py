"""Tests for diagnostic highlighters (T043).

Tests cover:
- SQLStateHighlighter: Error class coloring
- ErrorNameHighlighter: PostgreSQL error names
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.diagnostic import (
    ErrorNameHighlighter,
    SQLStateHighlighter,
    get_diagnostic_highlighters,
)
from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_theme() -> Theme:
    """Create a test theme with highlight styles."""
    return Theme(
        name="test",
        description="Test theme",
        levels={},
        ui={
            "hl_sqlstate_success": ColorStyle(fg="green"),
            "hl_sqlstate_warning": ColorStyle(fg="yellow"),
            "hl_sqlstate_error": ColorStyle(fg="red"),
            "hl_sqlstate_internal": ColorStyle(fg="red", bold=True),
            "hl_error_name": ColorStyle(fg="red"),
        },
    )


# =============================================================================
# Test SQLStateHighlighter
# =============================================================================


class TestSQLStateHighlighter:
    """Tests for SQLStateHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = SQLStateHighlighter()
        assert h.name == "sqlstate"
        assert h.priority == 200
        assert "sqlstate" in h.description.lower()

    def test_success_code(self, test_theme: Theme) -> None:
        """Should match success SQLSTATE codes (00xxx)."""
        h = SQLStateHighlighter()
        text = "SQLSTATE 00000"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "00000"
        assert matches[0].style == "hl_sqlstate_success"

    def test_warning_code(self, test_theme: Theme) -> None:
        """Should match warning SQLSTATE codes (01xxx, 02xxx)."""
        h = SQLStateHighlighter()
        text = "SQLSTATE 01000"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_sqlstate_warning"

    def test_no_data_code(self, test_theme: Theme) -> None:
        """Should match no data SQLSTATE codes (02xxx) as warning."""
        h = SQLStateHighlighter()
        text = "Code: 02000"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_sqlstate_warning"

    def test_error_code(self, test_theme: Theme) -> None:
        """Should match error SQLSTATE codes as error."""
        h = SQLStateHighlighter()
        text = "Error code 23505"  # unique_violation
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "23505"
        assert matches[0].style == "hl_sqlstate_error"

    def test_internal_error_code(self, test_theme: Theme) -> None:
        """Should match internal error SQLSTATE codes (XX, P0, F0)."""
        h = SQLStateHighlighter()
        text = "SQLSTATE XX000"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_sqlstate_internal"

    def test_multiple_codes(self, test_theme: Theme) -> None:
        """Should match multiple SQLSTATE codes in text."""
        h = SQLStateHighlighter()
        text = "Error 23505 changed to 00000"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2


# =============================================================================
# Test ErrorNameHighlighter
# =============================================================================


class TestErrorNameHighlighter:
    """Tests for ErrorNameHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = ErrorNameHighlighter()
        assert h.name == "error_name"
        assert h.priority == 210
        assert "error" in h.description.lower()

    def test_unique_violation(self, test_theme: Theme) -> None:
        """Should match unique_violation error name."""
        h = ErrorNameHighlighter()
        text = "ERROR: unique_violation"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "unique_violation"
        assert matches[0].style == "hl_error_name"

    def test_deadlock_detected(self, test_theme: Theme) -> None:
        """Should match deadlock_detected error name."""
        h = ErrorNameHighlighter()
        text = "deadlock_detected while processing"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "deadlock_detected"

    def test_foreign_key_violation(self, test_theme: Theme) -> None:
        """Should match foreign_key_violation error name."""
        h = ErrorNameHighlighter()
        text = "Error: foreign_key_violation on table"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match error names case-insensitively."""
        h = ErrorNameHighlighter()
        text = "UNIQUE_VIOLATION error"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_serialization_failure(self, test_theme: Theme) -> None:
        """Should match serialization_failure error name."""
        h = ErrorNameHighlighter()
        text = "serialization_failure during commit"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_insufficient_resources(self, test_theme: Theme) -> None:
        """Should match insufficient_resources error name."""
        h = ErrorNameHighlighter()
        text = "insufficient_resources: out of memory"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_diagnostic_highlighters(self) -> None:
        """get_diagnostic_highlighters should return all highlighters."""
        highlighters = get_diagnostic_highlighters()

        assert len(highlighters) == 2
        names = {h.name for h in highlighters}
        assert names == {"sqlstate", "error_name"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 200-299 range."""
        highlighters = get_diagnostic_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(200 <= p < 300 for p in priorities)
