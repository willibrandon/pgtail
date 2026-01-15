"""Tests for checkpoint highlighters (T080).

Tests cover:
- CheckpointHighlighter: Checkpoint-related messages
- RecoveryHighlighter: Recovery/startup messages
"""

from __future__ import annotations

import pytest

from pgtail_py.highlighters.checkpoint import (
    CheckpointHighlighter,
    RecoveryHighlighter,
    get_checkpoint_highlighters,
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
            "hl_checkpoint": ColorStyle(fg="cyan"),
            "hl_recovery": ColorStyle(fg="green"),
        },
    )


# =============================================================================
# Test CheckpointHighlighter
# =============================================================================


class TestCheckpointHighlighter:
    """Tests for CheckpointHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = CheckpointHighlighter()
        assert h.name == "checkpoint"
        assert h.priority == 900
        assert "checkpoint" in h.description.lower()

    def test_checkpoint_starting(self, test_theme: Theme) -> None:
        """Should match 'checkpoint starting' phrase."""
        h = CheckpointHighlighter()
        text = "LOG: checkpoint starting: time"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1
        assert any(m.style == "hl_checkpoint" for m in matches)

    def test_checkpoint_complete(self, test_theme: Theme) -> None:
        """Should match 'checkpoint complete' phrase."""
        h = CheckpointHighlighter()
        text = "LOG: checkpoint complete: wrote 100 buffers"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_checkpoint_keyword(self, test_theme: Theme) -> None:
        """Should match standalone 'checkpoint' keyword."""
        h = CheckpointHighlighter()
        text = "checkpoint complete"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_checkpointer(self, test_theme: Theme) -> None:
        """Should match 'checkpointer' keyword."""
        h = CheckpointHighlighter()
        text = "checkpointer: flushing buffers"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1
        assert any("checkpointer" in m.text for m in matches)

    def test_restartpoint(self, test_theme: Theme) -> None:
        """Should match 'restartpoint' keyword."""
        h = CheckpointHighlighter()
        text = "restartpoint complete"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_wrote_keyword(self, test_theme: Theme) -> None:
        """Should match 'wrote' keyword in checkpoint context."""
        h = CheckpointHighlighter()
        text = "checkpoint complete: wrote 500 buffers"
        matches = h.find_matches(text, test_theme)

        assert any("wrote" in m.text for m in matches)

    def test_sync_keyword(self, test_theme: Theme) -> None:
        """Should match 'sync' keyword."""
        h = CheckpointHighlighter()
        text = "sync files: 10"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = CheckpointHighlighter()
        text = "CHECKPOINT STARTING"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1


# =============================================================================
# Test RecoveryHighlighter
# =============================================================================


class TestRecoveryHighlighter:
    """Tests for RecoveryHighlighter."""

    def test_properties(self) -> None:
        """Highlighter should have correct name, priority, description."""
        h = RecoveryHighlighter()
        assert h.name == "recovery"
        assert h.priority == 910
        assert "recovery" in h.description.lower()

    def test_redo_starts_at(self, test_theme: Theme) -> None:
        """Should match 'redo starts at' phrase."""
        h = RecoveryHighlighter()
        text = "LOG: redo starts at 0/12345678"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1
        assert any(m.style == "hl_recovery" for m in matches)

    def test_redo_done_at(self, test_theme: Theme) -> None:
        """Should match 'redo done at' phrase."""
        h = RecoveryHighlighter()
        text = "LOG: redo done at 0/ABCDEF00"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_recovery_keyword(self, test_theme: Theme) -> None:
        """Should match 'recovery' keyword."""
        h = RecoveryHighlighter()
        text = "starting archive recovery"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_ready_to_accept_connections(self, test_theme: Theme) -> None:
        """Should match 'ready to accept connections' phrase."""
        h = RecoveryHighlighter()
        text = "database system is ready to accept connections"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_entering_standby_mode(self, test_theme: Theme) -> None:
        """Should match 'entering standby mode' phrase."""
        h = RecoveryHighlighter()
        text = "entering standby mode"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_database_system_ready(self, test_theme: Theme) -> None:
        """Should match 'database system is ready' phrase."""
        h = RecoveryHighlighter()
        text = "LOG: database system is ready to accept connections"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_restored_log_file(self, test_theme: Theme) -> None:
        """Should match 'restored log file' phrase."""
        h = RecoveryHighlighter()
        text = "restored log file 000000010000000000000001"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_startup_keyword(self, test_theme: Theme) -> None:
        """Should match 'startup' keyword."""
        h = RecoveryHighlighter()
        text = "startup process starting"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_shut_down(self, test_theme: Theme) -> None:
        """Should match 'shut down' phrase."""
        h = RecoveryHighlighter()
        text = "database system was shut down at 2024-01-15"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_standby_keyword(self, test_theme: Theme) -> None:
        """Should match 'standby' keyword."""
        h = RecoveryHighlighter()
        text = "standby mode active"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_streaming_replication(self, test_theme: Theme) -> None:
        """Should match 'streaming replication' phrase."""
        h = RecoveryHighlighter()
        text = "streaming replication started"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1

    def test_case_insensitive(self, test_theme: Theme) -> None:
        """Should match case-insensitively."""
        h = RecoveryHighlighter()
        text = "RECOVERY in progress"
        matches = h.find_matches(text, test_theme)

        assert len(matches) >= 1


# =============================================================================
# Test Module Functions
# =============================================================================


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_checkpoint_highlighters(self) -> None:
        """get_checkpoint_highlighters should return all highlighters."""
        highlighters = get_checkpoint_highlighters()

        assert len(highlighters) == 2
        names = {h.name for h in highlighters}
        assert names == {"checkpoint", "recovery"}

    def test_priority_order(self) -> None:
        """Highlighters should have priorities in 900-999 range."""
        highlighters = get_checkpoint_highlighters()
        priorities = [h.priority for h in highlighters]

        assert all(900 <= p < 1000 for p in priorities)
