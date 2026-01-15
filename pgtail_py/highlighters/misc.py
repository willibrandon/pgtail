"""Miscellaneous highlighters for PostgreSQL log output.

Highlighters in this module:
- BooleanHighlighter: Boolean values on/off, true/false (priority 1000)
- NullHighlighter: NULL keyword (priority 1010)
- OIDHighlighter: Object IDs (priority 1020)
- PathHighlighter: Unix file paths (priority 1030)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# BooleanHighlighter
# =============================================================================


class BooleanHighlighter(RegexHighlighter):
    """Highlights boolean values.

    Matches:
    - on/off
    - true/false
    - yes/no

    True values: green (hl_bool_true)
    False values: red (hl_bool_false)
    """

    # Pattern: boolean keywords with word boundaries
    PATTERN = r"\b(on|off|true|false|yes|no)\b"

    # Values that represent "true"
    TRUE_VALUES = frozenset({"on", "true", "yes"})

    def __init__(self) -> None:
        """Initialize boolean highlighter."""
        super().__init__(
            name="boolean",
            priority=1000,
            pattern=self.PATTERN,
            style="hl_bool_true",  # Default, overridden in find_matches
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Boolean values (on/off, true/false, yes/no)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all boolean value matches with appropriate styling.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects with true/false-based styles.
        """
        matches: list[Match] = []

        for m in self._pattern.finditer(text):
            value = m.group(1).lower()
            style = "hl_bool_true" if value in self.TRUE_VALUES else "hl_bool_false"

            matches.append(
                Match(
                    start=m.start(1),
                    end=m.end(1),
                    style=style,
                    text=m.group(1),
                )
            )

        return matches


# =============================================================================
# NullHighlighter
# =============================================================================


class NullHighlighter(RegexHighlighter):
    """Highlights NULL keyword.

    Matches standalone NULL keyword in various contexts.
    """

    PATTERN = r"\bNULL\b"

    def __init__(self) -> None:
        """Initialize NULL highlighter."""
        super().__init__(
            name="null",
            priority=1010,
            pattern=self.PATTERN,
            style="hl_null",
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "NULL keyword"


# =============================================================================
# OIDHighlighter
# =============================================================================


class OIDHighlighter(RegexHighlighter):
    """Highlights Object IDs (OIDs).

    Matches patterns like:
    - OID 12345
    - oid=12345
    - regclass 16384
    """

    # Pattern: OID keyword followed by number
    PATTERN = r"\b(OID|regclass|regtype|regproc)\s*[=:]?\s*(\d+)\b"

    def __init__(self) -> None:
        """Initialize OID highlighter."""
        super().__init__(
            name="oid",
            priority=1020,
            pattern=self.PATTERN,
            style="hl_oid",
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Object IDs (OID 12345, regclass)"


# =============================================================================
# PathHighlighter
# =============================================================================


class PathHighlighter(RegexHighlighter):
    """Highlights Unix file paths.

    Matches paths that:
    - Start with /
    - Contain typical PostgreSQL directories
    - Don't match IP addresses or other patterns

    Examples:
    - /var/lib/postgresql/data
    - /pg_wal/000000010000000000000001
    - /tmp/pg_stat_tmp
    """

    # Pattern: Unix paths starting with / and containing path characters
    # Must have at least one path segment (/) after the initial /
    PATTERN = r"\B(/(?:[\w.-]+/)+[\w.-]+)\b"

    def __init__(self) -> None:
        """Initialize path highlighter."""
        super().__init__(
            name="path",
            priority=1030,
            pattern=self.PATTERN,
            style="hl_path",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Unix file paths (/var/lib/postgresql/...)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_misc_highlighters() -> list[BooleanHighlighter | NullHighlighter | OIDHighlighter | PathHighlighter]:
    """Return all miscellaneous highlighters for registration.

    Returns:
        List of misc highlighter instances.
    """
    return [
        BooleanHighlighter(),
        NullHighlighter(),
        OIDHighlighter(),
        PathHighlighter(),
    ]


__all__ = [
    "BooleanHighlighter",
    "NullHighlighter",
    "OIDHighlighter",
    "PathHighlighter",
    "get_misc_highlighters",
]
