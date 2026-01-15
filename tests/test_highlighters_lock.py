"""Tests for lock highlighters (T076).

Tests cover:
- LockTypeHighlighter: Lock type names with severity coloring
- LockWaitHighlighter: Lock wait information
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.lock import (
    LockTypeHighlighter,
    LockWaitHighlighter,
    get_lock_highlighters,
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
            "hl_lock_share": ColorStyle(fg="yellow"),
            "hl_lock_exclusive": ColorStyle(fg="red"),
            "hl_lock_wait": ColorStyle(fg="red", bold=True),
        },
    )


# =============================================================================
# Test LockTypeHighlighter
# =============================================================================


class TestLockTypeHighlighter:
    """Tests for LockTypeHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = LockTypeHighlighter()
        assert h.name == "lock_type"
        assert h.priority == 800
        assert "lock" in h.description.lower()

    def test_access_share_lock(self, test_theme: Theme) -> None:
        """Should match AccessShareLock as share lock."""
        h = LockTypeHighlighter()
        text = "acquired AccessShareLock on relation"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "AccessShareLock"
        assert matches[0].style == "hl_lock_share"

    def test_row_share_lock(self, test_theme: Theme) -> None:
        """Should match RowShareLock as share lock."""
        h = LockTypeHighlighter()
        text = "waiting for RowShareLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_lock_share"

    def test_share_lock(self, test_theme: Theme) -> None:
        """Should match ShareLock as share lock."""
        h = LockTypeHighlighter()
        text = "acquired ShareLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_lock_share"

    def test_row_exclusive_lock(self, test_theme: Theme) -> None:
        """Should match RowExclusiveLock as exclusive lock."""
        h = LockTypeHighlighter()
        text = "waiting for RowExclusiveLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "RowExclusiveLock"
        assert matches[0].style == "hl_lock_exclusive"

    def test_exclusive_lock(self, test_theme: Theme) -> None:
        """Should match ExclusiveLock as exclusive lock."""
        h = LockTypeHighlighter()
        text = "acquired ExclusiveLock on table"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_lock_exclusive"

    def test_access_exclusive_lock(self, test_theme: Theme) -> None:
        """Should match AccessExclusiveLock as exclusive lock."""
        h = LockTypeHighlighter()
        text = "waiting for AccessExclusiveLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].style == "hl_lock_exclusive"

    def test_case_sensitive(self, test_theme: Theme) -> None:
        """Lock names are case-sensitive."""
        h = LockTypeHighlighter()
        text = "accesssharelock"  # lowercase
        matches = h.find_matches(text, test_theme)

        # Should not match lowercase
        assert len(matches) == 0

    def test_multiple_locks(self, test_theme: Theme) -> None:
        """Should match multiple lock types in text."""
        h = LockTypeHighlighter()
        text = "process holding AccessShareLock blocks AccessExclusiveLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 2
        styles = {m.style for m in matches}
        assert "hl_lock_share" in styles
        assert "hl_lock_exclusive" in styles


# =============================================================================
# Test LockWaitHighlighter
# =============================================================================


class TestLockWaitHighlighter:
    """Tests for LockWaitHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = LockWaitHighlighter()
        assert h.name == "lock_wait"
        assert h.priority == 810
        assert "wait" in h.description.lower()

    def test_waiting_for(self, test_theme: Theme) -> None:
        """Should match 'waiting for' phrase."""
        h = LockWaitHighlighter()
        text = "process 12345 waiting for ShareLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "waiting for"
        assert matches[0].style == "hl_lock_wait"

    def test_acquired(self, test_theme: Theme) -> None:
        """Should match 'acquired' keyword."""
        h = LockWaitHighlighter()
        text = "acquired AccessShareLock on relation"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "acquired"

    def test_still_waiting_for(self, test_theme: Theme) -> None:
        """Should match 'still waiting for' phrase."""
        h = LockWaitHighlighter()
        text = "still waiting for ShareLock after 1000.000 ms"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "still waiting for"

    def test_deadlock_detected(self, test_theme: Theme) -> None:
        """Should match 'deadlock detected' phrase."""
        h = LockWaitHighlighter()
        text = "ERROR: deadlock detected"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "deadlock detected"

    def test_process_still_waiting(self, test_theme: Theme) -> None:
        """Should match 'process N still waiting' phrase."""
        h = LockWaitHighlighter()
        text = "LOG: process 12345 still waiting for ShareLock"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_lock_timeout(self, test_theme: Theme) -> None:
        """Should match 'lock timeout' phrase."""
        h = LockWaitHighlighter()
        text = "ERROR: lock timeout after 30 seconds"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1
        assert matches[0].text == "lock timeout"

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = LockWaitHighlighter()
        text = "DEADLOCK DETECTED while processing"
        matches = h.find_matches(text, test_theme)

        assert len(matches) == 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_lock_highlighters(self) -> None:
        """get_lock_highlighters should return all highlighters."""
        highlighters = get_lock_highlighters()

        assert len(highlighters) == 2
        names = {h.name for h in highlighters}
        assert names == {"lock_type", "lock_wait"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 800-899 range."""
        highlighters = get_lock_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(800 <= p < 900 for p in priorities)
