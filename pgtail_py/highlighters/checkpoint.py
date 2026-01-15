"""Checkpoint and recovery highlighters for PostgreSQL log output.

Highlighters in this module:
- CheckpointHighlighter: Checkpoint-related messages (priority 900)
- RecoveryHighlighter: Recovery/startup messages (priority 910)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import KeywordHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# CheckpointHighlighter
# =============================================================================


class CheckpointHighlighter(KeywordHighlighter):
    """Highlights checkpoint-related messages.

    Uses Aho-Corasick for efficient matching of checkpoint keywords
    and phrases.
    """

    # Checkpoint-related keywords and phrases
    CHECKPOINT_KEYWORDS = {
        # Checkpoint states
        "checkpoint starting": "hl_checkpoint",
        "checkpoint complete": "hl_checkpoint",
        "checkpoint": "hl_checkpoint",
        # Checkpoint triggers
        "time": "hl_checkpoint",  # checkpoint due to time
        "xlog": "hl_checkpoint",  # checkpoint due to xlog
        "wal": "hl_checkpoint",  # checkpoint due to WAL
        "shutdown": "hl_checkpoint",
        "immediate": "hl_checkpoint",
        "force": "hl_checkpoint",
        # Checkpoint operations
        "checkpointer": "hl_checkpoint",
        "restartpoint": "hl_checkpoint",
        "wrote": "hl_checkpoint",  # "wrote N buffers"
        "sync": "hl_checkpoint",
        "synced": "hl_checkpoint",
        "total": "hl_checkpoint",
        "longest": "hl_checkpoint",
        "average": "hl_checkpoint",
    }

    def __init__(self) -> None:
        """Initialize checkpoint highlighter."""
        super().__init__(
            name="checkpoint",
            priority=900,
            keywords=self.CHECKPOINT_KEYWORDS,
            case_sensitive=False,
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Checkpoint messages (starting, complete, stats)"


# =============================================================================
# RecoveryHighlighter
# =============================================================================


class RecoveryHighlighter(KeywordHighlighter):
    """Highlights recovery and startup messages.

    Uses Aho-Corasick for efficient matching of recovery-related
    keywords and phrases.
    """

    # Recovery-related keywords and phrases
    RECOVERY_KEYWORDS = {
        # Recovery states
        "redo starts at": "hl_recovery",
        "redo done at": "hl_recovery",
        "redo": "hl_recovery",
        "recovery": "hl_recovery",
        "recovering": "hl_recovery",
        "recovered": "hl_recovery",
        # Recovery events
        "consistent recovery state": "hl_recovery",
        "ready to accept connections": "hl_recovery",
        "ready to accept read only connections": "hl_recovery",
        "entering standby mode": "hl_recovery",
        "starting point-in-time recovery": "hl_recovery",
        "requested": "hl_recovery",
        # Startup events
        "database system was interrupted": "hl_recovery",
        "database system was not properly shut down": "hl_recovery",
        "database system is ready": "hl_recovery",
        "database system was shut down": "hl_recovery",
        "database system is starting up": "hl_recovery",
        "startup": "hl_recovery",
        "starting up": "hl_recovery",
        "shutting down": "hl_recovery",
        "shut down": "hl_recovery",
        # Archive recovery
        "archive recovery": "hl_recovery",
        "restored log file": "hl_recovery",
        "selected new timeline": "hl_recovery",
        # Replication
        "streaming replication": "hl_recovery",
        "primary": "hl_recovery",
        "standby": "hl_recovery",
        "replica": "hl_recovery",
    }

    def __init__(self) -> None:
        """Initialize recovery highlighter."""
        super().__init__(
            name="recovery",
            priority=910,
            keywords=self.RECOVERY_KEYWORDS,
            case_sensitive=False,
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Recovery messages (redo, startup, standby)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_checkpoint_highlighters() -> list[CheckpointHighlighter | RecoveryHighlighter]:
    """Return all checkpoint/recovery highlighters for registration.

    Returns:
        List of checkpoint/recovery highlighter instances.
    """
    return [
        CheckpointHighlighter(),
        RecoveryHighlighter(),
    ]


__all__ = [
    "CheckpointHighlighter",
    "RecoveryHighlighter",
    "get_checkpoint_highlighters",
]
