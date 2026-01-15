"""Tests for WAL highlighters (T058).

Tests cover:
- LSNHighlighter: Log Sequence Numbers
- WALSegmentHighlighter: 24-char WAL segment filenames
- TxidHighlighter: Transaction IDs
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.wal import (
    LSNHighlighter,
    TxidHighlighter,
    WALSegmentHighlighter,
    get_wal_highlighters,
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
            "hl_lsn_segment": ColorStyle(fg="blue"),
            "hl_lsn_offset": ColorStyle(fg="blue", dim=True),
            "hl_wal_segment": ColorStyle(fg="blue"),
            "hl_txid": ColorStyle(fg="magenta"),
        },
    )


# =============================================================================
# Test LSNHighlighter
# =============================================================================


class TestLSNHighlighter:
    """Tests for LSNHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = LSNHighlighter()
        assert h.name == "lsn"
        assert h.priority == 500
        assert "lsn" in h.description.lower() or "sequence" in h.description.lower()

    def test_simple_lsn(self, test_theme: Theme) -> None:
        """Should match simple LSN format."""
        h = LSNHighlighter()
        text = "0/12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1
        styles = {m.style for m in matches}
        assert "hl_lsn_segment" in styles or "hl_lsn_offset" in styles

    def test_lsn_with_large_segment(self, test_theme: Theme) -> None:
        """Should match LSN with large segment number."""
        h = LSNHighlighter()
        text = "1A/ABCDEF00"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_lsn_in_context(self, test_theme: Theme) -> None:
        """Should match LSN in log message context."""
        h = LSNHighlighter()
        text = "redo starts at 0/12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_multiple_lsns(self, test_theme: Theme) -> None:
        """Should match multiple LSNs in text."""
        h = LSNHighlighter()
        text = "redo starts at 0/12345678 and ends at 0/ABCDEF00"
        matches = h.find_matches(text, test_theme)

        # Should have matches for both LSNs
        assert len(matches) >= 2


# =============================================================================
# Test WALSegmentHighlighter
# =============================================================================


class TestWALSegmentHighlighter:
    """Tests for WALSegmentHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = WALSegmentHighlighter()
        assert h.name == "wal_segment"
        assert h.priority == 510
        assert "wal" in h.description.lower() or "segment" in h.description.lower()

    def test_wal_segment_filename(self, test_theme: Theme) -> None:
        """Should match 24-character WAL segment filename."""
        h = WALSegmentHighlighter()
        text = "000000010000000000000001"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "000000010000000000000001"
        assert matches[0].style == "hl_wal_segment"

    def test_wal_segment_in_context(self, test_theme: Theme) -> None:
        """Should match WAL segment in log message."""
        h = WALSegmentHighlighter()
        text = "restored log file 000000010000000000000001"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_mixed_case_hex(self, test_theme: Theme) -> None:
        """Should match mixed case hex segment."""
        h = WALSegmentHighlighter()
        text = "00000001000000000000ABCD"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_no_match_short_hex(self, test_theme: Theme) -> None:
        """Should not match shorter hex strings."""
        h = WALSegmentHighlighter()
        text = "0000000100000000"  # 16 chars, not 24
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 0


# =============================================================================
# Test TxidHighlighter
# =============================================================================


class TestTxidHighlighter:
    """Tests for TxidHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = TxidHighlighter()
        assert h.name == "txid"
        assert h.priority == 520
        assert "transaction" in h.description.lower() or "txid" in h.description.lower()

    def test_xid(self, test_theme: Theme) -> None:
        """Should match xid keyword."""
        h = TxidHighlighter()
        text = "xid 12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_txid"

    def test_xmin(self, test_theme: Theme) -> None:
        """Should match xmin keyword."""
        h = TxidHighlighter()
        text = "xmin: 12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_xmax(self, test_theme: Theme) -> None:
        """Should match xmax keyword."""
        h = TxidHighlighter()
        text = "xmax: 87654321"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_transaction(self, test_theme: Theme) -> None:
        """Should match transaction keyword."""
        h = TxidHighlighter()
        text = "transaction 12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = TxidHighlighter()
        text = "XID 12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_wal_highlighters(self) -> None:
        """get_wal_highlighters should return all highlighters."""
        highlighters = get_wal_highlighters()

        assert len(highlighters) == 3
        names = {h.name for h in highlighters}
        assert names == {"lsn", "wal_segment", "txid"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 500-599 range."""
        highlighters = get_wal_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(500 <= p < 600 for p in priorities)
