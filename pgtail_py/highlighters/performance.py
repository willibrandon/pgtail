"""Performance highlighters for PostgreSQL log output.

Highlighters in this module:
- DurationHighlighter: Query durations with threshold-based coloring (priority 300)
- MemoryHighlighter: Memory sizes with units (priority 310)
- StatisticsHighlighter: Checkpoint/vacuum statistics (priority 320)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import GroupedRegexHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# DurationHighlighter
# =============================================================================


class DurationHighlighter(RegexHighlighter):
    """Highlights query durations with threshold-based coloring.

    Durations are colored based on severity thresholds:
    - Green: Fast (below slow threshold)
    - Yellow: Slow (slow ≤ x < very_slow)
    - Bright yellow/bold: Very slow (very_slow ≤ x < critical)
    - Red/bold: Critical (≥ critical threshold)

    Default thresholds (configurable):
    - slow: 100ms
    - very_slow: 500ms
    - critical: 5000ms
    """

    # Pattern: duration value with ms unit
    # Matches: "123.456 ms", "0.123 ms", "1234 ms"
    # Also matches log format: "duration: 123.456 ms"
    PATTERN = r"\b(\d+(?:\.\d+)?)\s*(ms)\b"

    # Default thresholds (can be overridden via config)
    DEFAULT_SLOW = 100
    DEFAULT_VERY_SLOW = 500
    DEFAULT_CRITICAL = 5000

    def __init__(
        self,
        slow: int = DEFAULT_SLOW,
        very_slow: int = DEFAULT_VERY_SLOW,
        critical: int = DEFAULT_CRITICAL,
    ) -> None:
        """Initialize duration highlighter.

        Args:
            slow: Threshold for slow queries (ms).
            very_slow: Threshold for very slow queries (ms).
            critical: Threshold for critical queries (ms).
        """
        super().__init__(
            name="duration",
            priority=300,
            pattern=self.PATTERN,
            style="hl_duration_fast",  # Default, overridden in find_matches
        )
        self._slow = slow
        self._very_slow = very_slow
        self._critical = critical

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return f"Query durations (slow: {self._slow}ms, critical: {self._critical}ms)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all duration matches with severity-based styling.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects with threshold-based styles.
        """
        matches: list[Match] = []

        for m in self._pattern.finditer(text):
            try:
                duration_ms = float(m.group(1))
            except ValueError:
                continue

            # Determine style based on duration
            if duration_ms >= self._critical:
                style = "hl_duration_critical"
            elif duration_ms >= self._very_slow:
                style = "hl_duration_very_slow"
            elif duration_ms >= self._slow:
                style = "hl_duration_slow"
            else:
                style = "hl_duration_fast"

            matches.append(
                Match(
                    start=m.start(),
                    end=m.end(),
                    style=style,
                    text=m.group(),
                )
            )

        return matches


# =============================================================================
# MemoryHighlighter
# =============================================================================


class MemoryHighlighter(GroupedRegexHighlighter):
    """Highlights memory/size values with units.

    Matches PostgreSQL memory format:
    - "1234 bytes"
    - "512 kB"
    - "128 MB"
    - "2 GB"
    - "1 TB"
    """

    # Pattern: numeric value followed by size unit
    PATTERN = r"""
        (?P<value>\d+(?:\.\d+)?)
        \s*
        (?P<unit>bytes|kB|MB|GB|TB)
        \b
    """

    GROUP_STYLES = {
        "value": "hl_memory_value",
        "unit": "hl_memory_unit",
    }

    def __init__(self) -> None:
        """Initialize memory highlighter."""
        super().__init__(
            name="memory",
            priority=310,
            pattern=self.PATTERN,
            group_styles=self.GROUP_STYLES,
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Memory sizes (bytes, kB, MB, GB, TB)"


# =============================================================================
# StatisticsHighlighter
# =============================================================================


class StatisticsHighlighter(RegexHighlighter):
    """Highlights checkpoint and vacuum statistics.

    Matches common PostgreSQL statistics patterns:
    - Checkpoint statistics: "wrote 123 buffers"
    - Vacuum statistics: "removed 456 dead tuples"
    - Percentage values: "12.34%"
    - Count values: "123 pages", "456 tuples"
    """

    # Pattern: Statistics keywords followed by numbers
    # This captures various PostgreSQL statistics formats
    # Note: % doesn't need trailing \b since it's not a word character
    PATTERN = r"\b(\d+(?:\.\d+)?)\s*(buffers?|pages?|tuples?|rows?|transactions?|blocks?|segments?|files?|%)"

    def __init__(self) -> None:
        """Initialize statistics highlighter."""
        super().__init__(
            name="statistics",
            priority=320,
            pattern=self.PATTERN,
            style="hl_statistics",
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Checkpoint/vacuum statistics (buffers, tuples, pages, %)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_performance_highlighters(
    duration_slow: int = DurationHighlighter.DEFAULT_SLOW,
    duration_very_slow: int = DurationHighlighter.DEFAULT_VERY_SLOW,
    duration_critical: int = DurationHighlighter.DEFAULT_CRITICAL,
) -> list[DurationHighlighter | MemoryHighlighter | StatisticsHighlighter]:
    """Return all performance highlighters for registration.

    Args:
        duration_slow: Slow query threshold (ms).
        duration_very_slow: Very slow query threshold (ms).
        duration_critical: Critical query threshold (ms).

    Returns:
        List of performance highlighter instances.
    """
    return [
        DurationHighlighter(
            slow=duration_slow,
            very_slow=duration_very_slow,
            critical=duration_critical,
        ),
        MemoryHighlighter(),
        StatisticsHighlighter(),
    ]


__all__ = [
    "DurationHighlighter",
    "MemoryHighlighter",
    "StatisticsHighlighter",
    "get_performance_highlighters",
]
