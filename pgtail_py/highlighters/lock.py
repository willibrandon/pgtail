"""Lock highlighters for PostgreSQL log output.

Highlighters in this module:
- LockTypeHighlighter: Lock type names with severity coloring (priority 800)
- LockWaitHighlighter: Lock wait information (priority 810)
"""

from __future__ import annotations

import re

from pgtail_py.highlighter import KeywordHighlighter, RegexHighlighter

# =============================================================================
# LockTypeHighlighter
# =============================================================================


class LockTypeHighlighter(KeywordHighlighter):
    """Highlights PostgreSQL lock type names.

    Uses Aho-Corasick for efficient matching. Lock types are colored
    based on their severity:
    - Share locks (less contention): hl_lock_share
    - Exclusive locks (more contention): hl_lock_exclusive
    """

    # Share-level locks (lower contention)
    SHARE_LOCKS = {
        "AccessShareLock": "hl_lock_share",
        "RowShareLock": "hl_lock_share",
        "ShareLock": "hl_lock_share",
        "ShareRowExclusiveLock": "hl_lock_share",
        "ShareUpdateExclusiveLock": "hl_lock_share",
    }

    # Exclusive locks (higher contention)
    EXCLUSIVE_LOCKS = {
        "RowExclusiveLock": "hl_lock_exclusive",
        "ExclusiveLock": "hl_lock_exclusive",
        "AccessExclusiveLock": "hl_lock_exclusive",
    }

    def __init__(self) -> None:
        """Initialize lock type highlighter."""
        all_locks = {**self.SHARE_LOCKS, **self.EXCLUSIVE_LOCKS}
        super().__init__(
            name="lock_type",
            priority=800,
            keywords=all_locks,
            case_sensitive=True,  # Lock names are case-sensitive
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Lock type names (share vs exclusive)"


# =============================================================================
# LockWaitHighlighter
# =============================================================================


class LockWaitHighlighter(RegexHighlighter):
    """Highlights lock wait information in log messages.

    Matches patterns like:
    - "waiting for ShareLock"
    - "acquired AccessShareLock"
    - "still waiting for ShareLock after 1000.000 ms"
    - "process 12345 still waiting"
    """

    # Pattern: lock wait/acquired messages
    PATTERN = r"\b(waiting for|acquired|still waiting for|deadlock detected|process \d+ still waiting|lock timeout)\b"

    def __init__(self) -> None:
        """Initialize lock wait highlighter."""
        super().__init__(
            name="lock_wait",
            priority=810,
            pattern=self.PATTERN,
            style="hl_lock_wait",
            flags=re.IGNORECASE,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Lock wait information (waiting for, acquired, deadlock)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_lock_highlighters() -> list[LockTypeHighlighter | LockWaitHighlighter]:
    """Return all lock highlighters for registration.

    Returns:
        List of lock highlighter instances.
    """
    return [
        LockTypeHighlighter(),
        LockWaitHighlighter(),
    ]


__all__ = [
    "LockTypeHighlighter",
    "LockWaitHighlighter",
    "get_lock_highlighters",
]
