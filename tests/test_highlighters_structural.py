"""Tests for structural highlighters (T039).

Tests cover:
- TimestampHighlighter: Date, time, ms, timezone patterns
- PIDHighlighter: Process IDs in brackets
- ContextLabelHighlighter: DETAIL:, HINT:, CONTEXT:, etc.
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.structural import (
    ContextLabelHighlighter,
    PIDHighlighter,
    TimestampHighlighter,
    get_structural_highlighters,
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
            "hl_timestamp_date": ColorStyle(fg="gray"),
            "hl_timestamp_time": ColorStyle(fg="gray"),
            "hl_timestamp_ms": ColorStyle(fg="gray", dim=True),
            "hl_timestamp_tz": ColorStyle(fg="gray", dim=True),
            "hl_pid": ColorStyle(fg="cyan"),
            "hl_context": ColorStyle(fg="yellow", bold=True),
        },
    )


# =============================================================================
# Test TimestampHighlighter
# =============================================================================


class TestTimestampHighlighter:
    """Tests for TimestampHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = TimestampHighlighter()
        assert h.name == "timestamp"
        assert h.priority == 100
        assert "timestamp" in h.description.lower()

    def test_basic_timestamp(self, test_theme: Theme) -> None:
        """Should match basic timestamp format."""
        h = TimestampHighlighter()
        text = "2024-01-15 14:30:45"
        matches = h.find_matches(text, test_theme)

        # Should have date and time groups
        assert len(matches) >= 2
        styles = {m.style for m in matches}
        assert "hl_timestamp_date" in styles
        assert "hl_timestamp_time" in styles

    def test_timestamp_with_ms(self, test_theme: Theme) -> None:
        """Should match timestamp with milliseconds."""
        h = TimestampHighlighter()
        text = "2024-01-15 14:30:45.123"
        matches = h.find_matches(text, test_theme)

        styles = {m.style for m in matches}
        assert "hl_timestamp_ms" in styles

    def test_timestamp_with_timezone(self, test_theme: Theme) -> None:
        """Should match timestamp with timezone."""
        h = TimestampHighlighter()
        text = "2024-01-15 14:30:45 UTC"
        matches = h.find_matches(text, test_theme)

        styles = {m.style for m in matches}
        assert "hl_timestamp_tz" in styles

    def test_iso_format(self, test_theme: Theme) -> None:
        """Should match ISO 8601 format with T separator."""
        h = TimestampHighlighter()
        text = "2024-01-15T14:30:45.123456+00:00"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 2

    def test_full_timestamp(self, test_theme: Theme) -> None:
        """Should match complete timestamp with all components."""
        h = TimestampHighlighter()
        text = "2024-01-15 14:30:45.123 PST"
        matches = h.find_matches(text, test_theme)

        # Should have all four components
        styles = {m.style for m in matches}
        assert "hl_timestamp_date" in styles
        assert "hl_timestamp_time" in styles
        assert "hl_timestamp_ms" in styles
        assert "hl_timestamp_tz" in styles


# =============================================================================
# Test PIDHighlighter
# =============================================================================


class TestPIDHighlighter:
    """Tests for PIDHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = PIDHighlighter()
        assert h.name == "pid"
        assert h.priority == 110
        assert "process" in h.description.lower()

    def test_simple_pid(self, test_theme: Theme) -> None:
        """Should match simple PID in brackets."""
        h = PIDHighlighter()
        text = "[12345]"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "[12345]"
        assert matches[0].style == "hl_pid"

    def test_pid_with_subprocess(self, test_theme: Theme) -> None:
        """Should match PID with subprocess ID."""
        h = PIDHighlighter()
        text = "[12345-1]"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "[12345-1]"

    def test_pid_in_context(self, test_theme: Theme) -> None:
        """Should match PID within log line."""
        h = PIDHighlighter()
        text = "2024-01-15 14:30:45.123 UTC [12345] LOG: statement: SELECT 1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "[12345]"

    def test_multiple_pids(self, test_theme: Theme) -> None:
        """Should match multiple PIDs in text."""
        h = PIDHighlighter()
        text = "Process [12345] waiting for [67890]"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2

    def test_no_match_level_tag(self, test_theme: Theme) -> None:
        """Should not match log level tags like [LOG]."""
        h = PIDHighlighter()
        text = "[LOG] Something happened"
        matches = h.find_matches(text, test_theme)

        # [LOG] doesn't contain digits, so shouldn't match
        assert len(matches) == 0


# =============================================================================
# Test ContextLabelHighlighter
# =============================================================================


class TestContextLabelHighlighter:
    """Tests for ContextLabelHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = ContextLabelHighlighter()
        assert h.name == "context"
        assert h.priority == 120
        assert "context" in h.description.lower()

    def test_detail_label(self, test_theme: Theme) -> None:
        """Should match DETAIL: label."""
        h = ContextLabelHighlighter()
        text = "DETAIL: Key already exists"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "DETAIL:"
        assert matches[0].style == "hl_context"

    def test_hint_label(self, test_theme: Theme) -> None:
        """Should match HINT: label."""
        h = ContextLabelHighlighter()
        text = "HINT: Try using a different value"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "HINT:"

    def test_context_label(self, test_theme: Theme) -> None:
        """Should match CONTEXT: label."""
        h = ContextLabelHighlighter()
        text = "CONTEXT: SQL statement"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "CONTEXT:"

    def test_statement_label(self, test_theme: Theme) -> None:
        """Should match STATEMENT: label."""
        h = ContextLabelHighlighter()
        text = "STATEMENT: INSERT INTO users VALUES (1)"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "STATEMENT:"

    def test_query_label(self, test_theme: Theme) -> None:
        """Should match QUERY: label."""
        h = ContextLabelHighlighter()
        text = "QUERY: SELECT * FROM users WHERE id = 1"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "QUERY:"

    def test_location_label(self, test_theme: Theme) -> None:
        """Should match LOCATION: label."""
        h = ContextLabelHighlighter()
        text = "LOCATION: exec_simple_query, postgres.c:1234"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "LOCATION:"

    def test_multiple_labels(self, test_theme: Theme) -> None:
        """Should match multiple labels in text."""
        h = ContextLabelHighlighter()
        text = "Error message\nDETAIL: Key exists\nHINT: Use different value"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2  # DETAIL and HINT


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_structural_highlighters(self) -> None:
        """get_structural_highlighters should return all three highlighters."""
        highlighters = get_structural_highlighters()

        assert len(highlighters) == 3
        names = {h.name for h in highlighters}
        assert names == {"timestamp", "pid", "context"}

    def test_priority_order(self) -> None:
        """Highlighters should have increasing priorities."""
        highlighters = get_structural_highlighters()
        priorities = [h.priority for h in highlighters]

        assert priorities == sorted(priorities)
        assert all(100 <= p < 200 for p in priorities)
