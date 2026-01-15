"""Tests for highlighter.py core entities.

Tests cover:
- Match dataclass validation (T028)
- OccupancyTracker functionality (T029)
- HighlighterChain overlap prevention (T030)
- escape_brackets utility (T031)
- RegexHighlighter base class
- GroupedRegexHighlighter base class
- KeywordHighlighter base class
"""

from __future__ import annotations

import os

import pytest

from pgtail_py.highlighter import (
    GroupedRegexHighlighter,
    HighlighterChain,
    KeywordHighlighter,
    Match,
    OccupancyTracker,
    RegexHighlighter,
    escape_brackets,
    is_color_disabled,
)
from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_theme() -> Theme:
    """Create a minimal theme for testing."""
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
            "hl_test2": ColorStyle(fg="green"),
            "hl_keyword": ColorStyle(fg="magenta"),
        },
    )


# =============================================================================
# Test Match (T028)
# =============================================================================


class TestMatch:
    """Tests for Match dataclass validation."""

    def test_valid_match(self) -> None:
        """Match with valid parameters should succeed."""
        match = Match(start=0, end=5, style="hl_test", text="hello")
        assert match.start == 0
        assert match.end == 5
        assert match.style == "hl_test"
        assert match.text == "hello"

    def test_match_is_frozen(self) -> None:
        """Match should be immutable (frozen dataclass)."""
        match = Match(start=0, end=5, style="hl_test", text="hello")
        with pytest.raises(AttributeError):
            match.start = 1  # type: ignore[misc]

    def test_match_negative_start(self) -> None:
        """Match with negative start should raise ValueError."""
        with pytest.raises(ValueError, match="start must be >= 0"):
            Match(start=-1, end=5, style="hl_test", text="hello")

    def test_match_end_not_greater_than_start(self) -> None:
        """Match with end <= start should raise ValueError."""
        with pytest.raises(ValueError, match="end must be > start"):
            Match(start=5, end=5, style="hl_test", text="hello")

        with pytest.raises(ValueError, match="end must be > start"):
            Match(start=5, end=3, style="hl_test", text="hello")

    def test_match_empty_style(self) -> None:
        """Match with empty style should raise ValueError."""
        with pytest.raises(ValueError, match="style must not be empty"):
            Match(start=0, end=5, style="", text="hello")

    def test_match_equality(self) -> None:
        """Two matches with same values should be equal."""
        m1 = Match(start=0, end=5, style="hl_test", text="hello")
        m2 = Match(start=0, end=5, style="hl_test", text="hello")
        assert m1 == m2

    def test_match_hashable(self) -> None:
        """Match should be hashable for use in sets."""
        match = Match(start=0, end=5, style="hl_test", text="hello")
        s = {match}
        assert match in s


# =============================================================================
# Test OccupancyTracker (T029)
# =============================================================================


class TestOccupancyTracker:
    """Tests for OccupancyTracker class."""

    def test_empty_tracker(self) -> None:
        """New tracker should have all ranges available."""
        tracker = OccupancyTracker(10)
        assert tracker.length == 10
        assert tracker.is_available(0, 10)
        assert tracker.available_ranges() == [(0, 10)]

    def test_mark_occupied_single(self) -> None:
        """Marking a range should make it unavailable."""
        tracker = OccupancyTracker(10)
        tracker.mark_occupied(2, 5)

        assert not tracker.is_available(2, 5)
        assert not tracker.is_available(2, 3)
        assert not tracker.is_available(4, 5)
        assert tracker.is_available(0, 2)
        assert tracker.is_available(5, 10)

    def test_mark_occupied_multiple(self) -> None:
        """Multiple non-overlapping regions can be marked."""
        tracker = OccupancyTracker(20)
        tracker.mark_occupied(2, 5)
        tracker.mark_occupied(10, 15)

        assert tracker.available_ranges() == [(0, 2), (5, 10), (15, 20)]

    def test_is_available_partial_overlap(self) -> None:
        """Range with partial overlap should not be available."""
        tracker = OccupancyTracker(10)
        tracker.mark_occupied(3, 7)

        # Partial overlaps
        assert not tracker.is_available(0, 5)
        assert not tracker.is_available(5, 10)
        assert not tracker.is_available(2, 8)

    def test_is_available_invalid_bounds(self) -> None:
        """Invalid bounds should return False."""
        tracker = OccupancyTracker(10)

        assert not tracker.is_available(-1, 5)
        assert not tracker.is_available(0, 15)
        assert not tracker.is_available(8, 5)  # start >= end

    def test_mark_occupied_out_of_bounds(self) -> None:
        """Marking out of bounds should be handled gracefully."""
        tracker = OccupancyTracker(10)
        # Should not raise, just ignore invalid parts
        tracker.mark_occupied(-1, 3)
        tracker.mark_occupied(8, 15)

    def test_available_ranges_fully_occupied(self) -> None:
        """Fully occupied tracker should return empty list."""
        tracker = OccupancyTracker(5)
        tracker.mark_occupied(0, 5)
        assert tracker.available_ranges() == []

    def test_available_ranges_with_gaps(self) -> None:
        """Available ranges with multiple gaps."""
        tracker = OccupancyTracker(10)
        tracker.mark_occupied(2, 4)
        tracker.mark_occupied(6, 8)

        ranges = tracker.available_ranges()
        assert ranges == [(0, 2), (4, 6), (8, 10)]


# =============================================================================
# Test HighlighterChain (T030)
# =============================================================================


class TestHighlighterChain:
    """Tests for HighlighterChain overlap prevention."""

    def test_empty_chain(self, mock_theme: Theme) -> None:
        """Empty chain should return original text."""
        chain = HighlighterChain()
        result = chain.apply_rich("hello world", mock_theme)
        assert result == "hello world"

    def test_single_highlighter(self, mock_theme: Theme) -> None:
        """Single highlighter should apply correctly."""
        chain = HighlighterChain()
        chain.register(
            RegexHighlighter(
                name="test",
                priority=100,
                pattern=r"\d+",
                style="hl_test",
            )
        )

        result = chain.apply_rich("value: 123", mock_theme)
        assert "[blue bold]123[/]" in result

    def test_overlap_prevention_priority(self, mock_theme: Theme) -> None:
        """Higher priority (lower number) should win on overlap."""
        chain = HighlighterChain()

        # Higher priority (applied first)
        chain.register(
            RegexHighlighter(
                name="high",
                priority=100,
                pattern=r"hello world",
                style="hl_test",
            )
        )

        # Lower priority (should not match within "hello world")
        chain.register(
            RegexHighlighter(
                name="low",
                priority=200,
                pattern=r"world",
                style="hl_test2",
            )
        )

        result = chain.apply_rich("hello world today", mock_theme)
        # "hello world" should be blue bold (hl_test), not green (hl_test2)
        assert "[blue bold]hello world[/]" in result
        assert "green" not in result or "world" not in result.split("green")[0]

    def test_non_overlapping_matches(self, mock_theme: Theme) -> None:
        """Non-overlapping matches should both apply."""
        chain = HighlighterChain()

        chain.register(
            RegexHighlighter(
                name="numbers",
                priority=100,
                pattern=r"\d+",
                style="hl_test",
            )
        )

        chain.register(
            RegexHighlighter(
                name="words",
                priority=200,
                pattern=r"[a-z]+",
                style="hl_test2",
            )
        )

        result = chain.apply_rich("abc 123", mock_theme)
        assert "[green]abc[/]" in result
        assert "[blue bold]123[/]" in result

    def test_depth_limiting(self, mock_theme: Theme) -> None:
        """Max length should truncate highlighting."""
        chain = HighlighterChain(max_length=10)

        chain.register(
            RegexHighlighter(
                name="test",
                priority=100,
                pattern=r"\d+",
                style="hl_test",
            )
        )

        # 15 chars, but only first 10 should be highlighted
        text = "abc 123 xyz 456"
        result = chain.apply_rich(text, mock_theme)

        # "123" is within first 10 chars, "456" is beyond
        assert "[blue bold]123[/]" in result
        # The "456" should appear but not be highlighted
        assert "456" in result

    def test_register_duplicate_name(self) -> None:
        """Registering duplicate name should raise."""
        chain = HighlighterChain()
        chain.register(
            RegexHighlighter(name="test", priority=100, pattern=r"x", style="hl_test")
        )

        with pytest.raises(ValueError, match="already registered"):
            chain.register(
                RegexHighlighter(
                    name="test", priority=200, pattern=r"y", style="hl_test"
                )
            )

    def test_unregister_unknown(self) -> None:
        """Unregistering unknown name should raise."""
        chain = HighlighterChain()

        with pytest.raises(KeyError, match="not found"):
            chain.unregister("unknown")


# =============================================================================
# Test escape_brackets (T031)
# =============================================================================


class TestEscapeBrackets:
    """Tests for escape_brackets utility."""

    def test_no_brackets(self) -> None:
        """Text without brackets should be unchanged."""
        assert escape_brackets("hello world") == "hello world"

    def test_single_bracket(self) -> None:
        """Single bracket should be escaped."""
        assert escape_brackets("[bold]") == "\\[bold]"

    def test_multiple_brackets(self) -> None:
        """Multiple brackets should all be escaped."""
        assert escape_brackets("[a][b][c]") == "\\[a]\\[b]\\[c]"

    def test_nested_brackets(self) -> None:
        """Nested brackets in log output."""
        text = "[12345] ERROR: connection [local]"
        expected = "\\[12345] ERROR: connection \\[local]"
        assert escape_brackets(text) == expected

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        assert escape_brackets("") == ""


# =============================================================================
# Test RegexHighlighter
# =============================================================================


class TestRegexHighlighter:
    """Tests for RegexHighlighter base class."""

    def test_simple_pattern(self, mock_theme: Theme) -> None:
        """Simple regex pattern should match."""
        highlighter = RegexHighlighter(
            name="test",
            priority=100,
            pattern=r"\d+",
            style="hl_test",
        )

        matches = highlighter.find_matches("value: 123", mock_theme)
        assert len(matches) == 1
        assert matches[0].start == 7
        assert matches[0].end == 10
        assert matches[0].text == "123"

    def test_multiple_matches(self, mock_theme: Theme) -> None:
        """Pattern should find all matches."""
        highlighter = RegexHighlighter(
            name="test",
            priority=100,
            pattern=r"\d+",
            style="hl_test",
        )

        matches = highlighter.find_matches("a:1 b:22 c:333", mock_theme)
        assert len(matches) == 3
        assert [m.text for m in matches] == ["1", "22", "333"]

    def test_case_insensitive(self, mock_theme: Theme) -> None:
        """Case insensitive flag should work."""
        import re

        highlighter = RegexHighlighter(
            name="test",
            priority=100,
            pattern=r"error",
            style="hl_test",
            flags=re.IGNORECASE,
        )

        matches = highlighter.find_matches("ERROR Error error", mock_theme)
        assert len(matches) == 3

    def test_invalid_pattern(self) -> None:
        """Invalid regex should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid regex"):
            RegexHighlighter(
                name="test",
                priority=100,
                pattern=r"[invalid",  # Unclosed bracket
                style="hl_test",
            )

    def test_zero_length_pattern(self) -> None:
        """Pattern matching zero-length should raise."""
        with pytest.raises(ValueError, match="zero-length"):
            RegexHighlighter(
                name="test",
                priority=100,
                pattern=r"^",  # Matches empty at start
                style="hl_test",
            )


# =============================================================================
# Test GroupedRegexHighlighter
# =============================================================================


class TestGroupedRegexHighlighter:
    """Tests for GroupedRegexHighlighter base class."""

    def test_named_groups(self, mock_theme: Theme) -> None:
        """Named groups should map to different styles."""
        highlighter = GroupedRegexHighlighter(
            name="test",
            priority=100,
            pattern=r"(?P<key>\w+)=(?P<value>\d+)",
            group_styles={
                "key": "hl_test",
                "value": "hl_test2",
            },
        )

        matches = highlighter.find_matches("count=42", mock_theme)
        assert len(matches) == 2

        key_match = next(m for m in matches if m.text == "count")
        value_match = next(m for m in matches if m.text == "42")

        assert key_match.style == "hl_test"
        assert value_match.style == "hl_test2"

    def test_multiple_group_matches(self, mock_theme: Theme) -> None:
        """Multiple overall matches with groups."""
        highlighter = GroupedRegexHighlighter(
            name="test",
            priority=100,
            pattern=r"(?P<key>\w+):(?P<value>\d+)",
            group_styles={
                "key": "hl_test",
                "value": "hl_test2",
            },
        )

        matches = highlighter.find_matches("a:1 b:2", mock_theme)
        assert len(matches) == 4  # 2 keys + 2 values


# =============================================================================
# Test KeywordHighlighter
# =============================================================================


class TestKeywordHighlighter:
    """Tests for KeywordHighlighter base class."""

    def test_keyword_matching(self, mock_theme: Theme) -> None:
        """Keywords should be matched."""
        highlighter = KeywordHighlighter(
            name="test",
            priority=100,
            keywords={
                "SELECT": "hl_keyword",
                "FROM": "hl_keyword",
                "WHERE": "hl_keyword",
            },
        )

        matches = highlighter.find_matches("SELECT * FROM users", mock_theme)
        assert len(matches) == 2
        texts = {m.text.upper() for m in matches}
        assert texts == {"SELECT", "FROM"}

    def test_case_insensitive(self, mock_theme: Theme) -> None:
        """Case insensitive matching should work."""
        highlighter = KeywordHighlighter(
            name="test",
            priority=100,
            keywords={"error": "hl_test"},
            case_sensitive=False,
        )

        matches = highlighter.find_matches("ERROR Error error", mock_theme)
        assert len(matches) == 3

    def test_word_boundary(self, mock_theme: Theme) -> None:
        """Word boundary matching should prevent partial matches."""
        highlighter = KeywordHighlighter(
            name="test",
            priority=100,
            keywords={"in": "hl_test"},
            word_boundary=True,
        )

        matches = highlighter.find_matches("in insert into", mock_theme)
        # Only "in" at start should match, not "in" in "insert" or "into"
        assert len(matches) == 1
        assert matches[0].text == "in"

    def test_many_keywords(self, mock_theme: Theme) -> None:
        """Many keywords should still work efficiently."""
        keywords = {f"keyword{i}": "hl_test" for i in range(100)}
        highlighter = KeywordHighlighter(
            name="test",
            priority=100,
            keywords=keywords,
        )

        matches = highlighter.find_matches("keyword1 keyword50 keyword99", mock_theme)
        assert len(matches) == 3


# =============================================================================
# Test is_color_disabled
# =============================================================================


class TestIsColorDisabled:
    """Tests for NO_COLOR environment variable handling."""

    def test_no_color_not_set(self) -> None:
        """When NO_COLOR is not set, color should be enabled."""
        # Ensure NO_COLOR is not set
        os.environ.pop("NO_COLOR", None)
        assert not is_color_disabled()

    def test_no_color_empty(self) -> None:
        """When NO_COLOR is empty, color should be enabled."""
        os.environ["NO_COLOR"] = ""
        try:
            assert not is_color_disabled()
        finally:
            os.environ.pop("NO_COLOR", None)

    def test_no_color_set(self) -> None:
        """When NO_COLOR is set, color should be disabled."""
        os.environ["NO_COLOR"] = "1"
        try:
            assert is_color_disabled()
        finally:
            os.environ.pop("NO_COLOR", None)

    def test_no_color_any_value(self) -> None:
        """Any non-empty NO_COLOR value should disable color."""
        for value in ["1", "true", "yes", "anything"]:
            os.environ["NO_COLOR"] = value
            try:
                assert is_color_disabled()
            finally:
                os.environ.pop("NO_COLOR", None)
