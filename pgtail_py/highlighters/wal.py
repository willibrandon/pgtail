"""WAL (Write-Ahead Log) highlighters for PostgreSQL log output.

Highlighters in this module:
- LSNHighlighter: Log Sequence Numbers (priority 500)
- WALSegmentHighlighter: WAL segment filenames (priority 510)
- TxidHighlighter: Transaction IDs (priority 520)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import GroupedRegexHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# LSNHighlighter
# =============================================================================


class LSNHighlighter(GroupedRegexHighlighter):
    """Highlights Log Sequence Numbers (LSN).

    LSNs identify positions in the WAL stream:
    - Format: segment/offset (e.g., 0/12345678)
    - Segment is a hex number
    - Offset is a hex number within the segment
    """

    # Pattern: LSN format (hex/hex)
    # Common contexts: "redo starts at 0/12345678", "consistent recovery state reached at 0/ABCDEF12"
    PATTERN = r"""
        \b
        (?P<segment>[0-9A-Fa-f]{1,8})
        /
        (?P<offset>[0-9A-Fa-f]{1,8})
        \b
    """

    GROUP_STYLES = {
        "segment": "hl_lsn_segment",
        "offset": "hl_lsn_offset",
    }

    def __init__(self) -> None:
        """Initialize LSN highlighter."""
        super().__init__(
            name="lsn",
            priority=500,
            pattern=self.PATTERN,
            group_styles=self.GROUP_STYLES,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Log Sequence Numbers (0/12345678)"


# =============================================================================
# WALSegmentHighlighter
# =============================================================================


class WALSegmentHighlighter(RegexHighlighter):
    """Highlights WAL segment filenames.

    WAL segment files are 24-character hex strings:
    - Format: TTTTTTTTSSSSSSSSNNNNNNNN
    - T: Timeline ID (8 hex digits)
    - S: Segment high (8 hex digits)
    - N: Segment low (8 hex digits)

    Example: 000000010000000000000001
    """

    # Pattern: 24 hex characters (WAL segment filename)
    # Must be standalone (not part of longer hex string)
    PATTERN = r"\b[0-9A-Fa-f]{24}\b"

    def __init__(self) -> None:
        """Initialize WAL segment highlighter."""
        super().__init__(
            name="wal_segment",
            priority=510,
            pattern=self.PATTERN,
            style="hl_wal_segment",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "WAL segment filenames (24-char hex)"


# =============================================================================
# TxidHighlighter
# =============================================================================


class TxidHighlighter(RegexHighlighter):
    """Highlights transaction IDs.

    Matches transaction-related identifiers:
    - xid: Transaction ID
    - xmin/xmax: Visibility bounds
    - transaction: Named transaction reference

    Formats:
    - xid 12345678
    - xmin: 12345678
    - transaction 12345678
    """

    # Pattern: transaction ID keywords followed by number
    PATTERN = r"\b(xid|xmin|xmax|transaction)\s*:?\s*(\d+)\b"

    def __init__(self) -> None:
        """Initialize txid highlighter."""
        super().__init__(
            name="txid",
            priority=520,
            pattern=self.PATTERN,
            style="hl_txid",
            flags=re.IGNORECASE,
        )
        self._extract_pattern = re.compile(self.PATTERN, re.IGNORECASE)

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Transaction IDs (xid, xmin, xmax, transaction N)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all transaction ID matches.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects for the full match including keyword and ID.
        """
        matches: list[Match] = []

        for m in self._extract_pattern.finditer(text):
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


def get_wal_highlighters() -> list[LSNHighlighter | WALSegmentHighlighter | TxidHighlighter]:
    """Return all WAL highlighters for registration.

    Returns:
        List of WAL highlighter instances.
    """
    return [
        LSNHighlighter(),
        WALSegmentHighlighter(),
        TxidHighlighter(),
    ]


__all__ = [
    "LSNHighlighter",
    "WALSegmentHighlighter",
    "TxidHighlighter",
    "get_wal_highlighters",
]
