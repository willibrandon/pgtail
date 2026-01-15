"""Structural highlighters for PostgreSQL log output.

Highlighters in this module:
- TimestampHighlighter: Date, time, milliseconds, timezone (priority 100)
- PIDHighlighter: Process IDs in brackets [12345] or [12345-1] (priority 110)
- ContextLabelHighlighter: Context labels like DETAIL:, HINT:, CONTEXT: (priority 120)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import GroupedRegexHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# TimestampHighlighter
# =============================================================================


class TimestampHighlighter(GroupedRegexHighlighter):
    """Highlights timestamps with distinct styling for each component.

    Matches PostgreSQL timestamp formats:
    - 2024-01-15 14:30:45.123 UTC
    - 2024-01-15T14:30:45.123456+00:00
    - 2024-01-15 14:30:45 PST
    """

    # Pattern components:
    # - date: YYYY-MM-DD
    # - time: HH:MM:SS
    # - ms: .NNN or .NNNNNN (optional)
    # - tz: timezone abbreviation or offset (optional)
    PATTERN = r"""
        (?P<date>\d{4}-\d{2}-\d{2})
        [T\x20]
        (?P<time>\d{2}:\d{2}:\d{2})
        (?:\.(?P<ms>\d{3,6}))?
        (?:\x20?(?P<tz>[A-Z]{2,4}|[+-]\d{2}:?\d{2}))?
    """

    GROUP_STYLES = {
        "date": "hl_timestamp_date",
        "time": "hl_timestamp_time",
        "ms": "hl_timestamp_ms",
        "tz": "hl_timestamp_tz",
    }

    def __init__(self) -> None:
        """Initialize timestamp highlighter."""
        super().__init__(
            name="timestamp",
            priority=100,
            pattern=self.PATTERN,
            group_styles=self.GROUP_STYLES,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Timestamps with date, time, milliseconds, timezone"


# =============================================================================
# PIDHighlighter
# =============================================================================


class PIDHighlighter(RegexHighlighter):
    """Highlights process IDs in brackets.

    Matches formats:
    - [12345] - Standard PID
    - [12345-1] - PID with sub-process ID (parallel workers)
    """

    # Pattern: [digits] or [digits-digits]
    # Note: Only match standalone PIDs, not things like log levels [LOG]
    PATTERN = r"\[(\d+)(?:-\d+)?\]"

    def __init__(self) -> None:
        """Initialize PID highlighter."""
        super().__init__(
            name="pid",
            priority=110,
            pattern=self.PATTERN,
            style="hl_pid",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Process IDs in brackets [12345] or [12345-1]"


# =============================================================================
# ContextLabelHighlighter
# =============================================================================


class ContextLabelHighlighter(RegexHighlighter):
    """Highlights PostgreSQL context labels.

    Matches labels at start of line or after whitespace:
    - DETAIL:
    - HINT:
    - CONTEXT:
    - STATEMENT:
    - QUERY:
    - LOCATION:
    """

    # Pattern: Known context labels followed by colon
    # Must be at start of line or preceded by whitespace
    PATTERN = r"(?:^|\s)(DETAIL|HINT|CONTEXT|STATEMENT|QUERY|LOCATION):"

    def __init__(self) -> None:
        """Initialize context label highlighter."""
        super().__init__(
            name="context",
            priority=120,
            pattern=self.PATTERN,
            style="hl_context",
        )
        # Override pattern to capture only the label (not preceding whitespace)
        self._label_pattern = re.compile(
            r"(DETAIL|HINT|CONTEXT|STATEMENT|QUERY|LOCATION):", re.MULTILINE
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Context labels (DETAIL:, HINT:, CONTEXT:, etc.)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all context label matches in text.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects.
        """
        matches: list[Match] = []
        for m in self._label_pattern.finditer(text):
            matches.append(
                Match(
                    start=m.start(),
                    end=m.end(),
                    style=self._style,
                    text=m.group(),
                )
            )
        return matches


# =============================================================================
# Module-level registration
# =============================================================================


def get_structural_highlighters() -> list[TimestampHighlighter | PIDHighlighter | ContextLabelHighlighter]:
    """Return all structural highlighters for registration.

    Returns:
        List of structural highlighter instances.
    """
    return [
        TimestampHighlighter(),
        PIDHighlighter(),
        ContextLabelHighlighter(),
    ]


__all__ = [
    "TimestampHighlighter",
    "PIDHighlighter",
    "ContextLabelHighlighter",
    "get_structural_highlighters",
]
