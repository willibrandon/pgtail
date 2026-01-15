"""Tests for performance highlighters (T048).

Tests cover:
- DurationHighlighter: Threshold-based duration coloring
- MemoryHighlighter: Memory sizes with units
- StatisticsHighlighter: Checkpoint/vacuum statistics
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.performance import (
    DurationHighlighter,
    MemoryHighlighter,
    StatisticsHighlighter,
    get_performance_highlighters,
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
            "hl_duration_fast": ColorStyle(fg="green"),
            "hl_duration_slow": ColorStyle(fg="yellow"),
            "hl_duration_very_slow": ColorStyle(fg="yellow", bold=True),
            "hl_duration_critical": ColorStyle(fg="red", bold=True),
            "hl_memory_value": ColorStyle(fg="magenta"),
            "hl_memory_unit": ColorStyle(fg="magenta", dim=True),
            "hl_statistics": ColorStyle(fg="cyan"),
        },
    )


# =============================================================================
# Test DurationHighlighter
# =============================================================================


class TestDurationHighlighter:
    """Tests for DurationHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = DurationHighlighter()
        assert h.name == "duration"
        assert h.priority == 300
        assert "duration" in h.description.lower()

    def test_fast_duration(self, test_theme: Theme) -> None:
        """Should style durations below slow threshold as fast."""
        h = DurationHighlighter(slow=100)
        text = "duration: 50.123 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_duration_fast"

    def test_slow_duration(self, test_theme: Theme) -> None:
        """Should style durations at/above slow threshold as slow."""
        h = DurationHighlighter(slow=100, very_slow=500)
        text = "duration: 250.5 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_duration_slow"

    def test_very_slow_duration(self, test_theme: Theme) -> None:
        """Should style durations at/above very_slow threshold."""
        h = DurationHighlighter(slow=100, very_slow=500, critical=5000)
        text = "duration: 1500.0 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_duration_very_slow"

    def test_critical_duration(self, test_theme: Theme) -> None:
        """Should style durations at/above critical threshold."""
        h = DurationHighlighter(critical=5000)
        text = "duration: 10000 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_duration_critical"

    def test_decimal_duration(self, test_theme: Theme) -> None:
        """Should match decimal durations."""
        h = DurationHighlighter()
        text = "123.456 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert "123.456 ms" in matches[0].text

    def test_custom_thresholds(self, test_theme: Theme) -> None:
        """Should use custom thresholds."""
        h = DurationHighlighter(slow=10, very_slow=50, critical=100)

        # 5ms should be fast
        matches = h.find_matches("5 ms", test_theme)
        assert matches[0].style == "hl_duration_fast"

        # 25ms should be slow
        matches = h.find_matches("25 ms", test_theme)
        assert matches[0].style == "hl_duration_slow"


# =============================================================================
# Test MemoryHighlighter
# =============================================================================


class TestMemoryHighlighter:
    """Tests for MemoryHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = MemoryHighlighter()
        assert h.name == "memory"
        assert h.priority == 310
        assert "memory" in h.description.lower()

    def test_bytes(self, test_theme: Theme) -> None:
        """Should match bytes unit."""
        h = MemoryHighlighter()
        text = "1234 bytes"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1
        styles = {m.style for m in matches}
        assert "hl_memory_value" in styles or "hl_memory_unit" in styles

    def test_kilobytes(self, test_theme: Theme) -> None:
        """Should match kB unit."""
        h = MemoryHighlighter()
        text = "512 kB"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_megabytes(self, test_theme: Theme) -> None:
        """Should match MB unit."""
        h = MemoryHighlighter()
        text = "128 MB"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_gigabytes(self, test_theme: Theme) -> None:
        """Should match GB unit."""
        h = MemoryHighlighter()
        text = "2 GB"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_terabytes(self, test_theme: Theme) -> None:
        """Should match TB unit."""
        h = MemoryHighlighter()
        text = "1 TB"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_decimal_value(self, test_theme: Theme) -> None:
        """Should match decimal memory values."""
        h = MemoryHighlighter()
        text = "1.5 GB"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1


# =============================================================================
# Test StatisticsHighlighter
# =============================================================================


class TestStatisticsHighlighter:
    """Tests for StatisticsHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = StatisticsHighlighter()
        assert h.name == "statistics"
        assert h.priority == 320
        assert "statistic" in h.description.lower()

    def test_buffers(self, test_theme: Theme) -> None:
        """Should match buffer statistics."""
        h = StatisticsHighlighter()
        text = "wrote 123 buffers"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_statistics"

    def test_pages(self, test_theme: Theme) -> None:
        """Should match page statistics."""
        h = StatisticsHighlighter()
        text = "scanned 456 pages"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_tuples(self, test_theme: Theme) -> None:
        """Should match tuple statistics."""
        h = StatisticsHighlighter()
        text = "removed 789 tuples"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_percentage(self, test_theme: Theme) -> None:
        """Should match percentage statistics."""
        h = StatisticsHighlighter()
        text = "12.34%"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_rows(self, test_theme: Theme) -> None:
        """Should match row statistics."""
        h = StatisticsHighlighter()
        text = "affected 100 rows"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_performance_highlighters(self) -> None:
        """get_performance_highlighters should return all highlighters."""
        highlighters = get_performance_highlighters()

        assert len(highlighters) == 3
        names = {h.name for h in highlighters}
        assert names == {"duration", "memory", "statistics"}

    def test_custom_duration_thresholds(self) -> None:
        """get_performance_highlighters should accept custom duration thresholds."""
        highlighters = get_performance_highlighters(
            duration_slow=50,
            duration_very_slow=200,
            duration_critical=1000,
        )

        duration = next(h for h in highlighters if h.name == "duration")
        assert duration._slow == 50
        assert duration._very_slow == 200
        assert duration._critical == 1000

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 300-399 range."""
        highlighters = get_performance_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(300 <= p < 400 for p in priorities)
