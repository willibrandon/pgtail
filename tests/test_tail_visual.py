"""Tests for TailLog visual mode navigation."""

from __future__ import annotations

import pytest

from pgtail_py.tail_log import TailLog


class TestVisualModeBoundaries:
    """Tests for visual mode navigation at buffer boundaries.

    Note: Tests that require widget.write_line() need an active app context.
    These are tested via async tests in test_tail_textual.py or by testing
    the state management logic directly.
    """

    def test_visual_anchor_initialized_none(self) -> None:
        """Test that visual anchor starts as None."""
        widget = TailLog()
        assert widget._visual_anchor_line is None

    def test_empty_buffer_visual_mode_no_crash(self) -> None:
        """Test visual mode with empty buffer doesn't crash."""
        widget = TailLog()
        # Should not raise - empty buffer returns early from actions
        widget.action_visual_mode()
        widget.action_scroll_up()
        widget.action_scroll_down()
        # No assertion needed - just verify no exception

    def test_cursor_line_starts_at_zero(self) -> None:
        """Test that cursor line is initialized to 0."""
        widget = TailLog()
        assert widget._cursor_line == 0

    def test_visual_mode_flags_independent(self) -> None:
        """Test visual_mode and visual_line_mode are independent."""
        widget = TailLog()
        widget._visual_mode = True
        widget._visual_line_mode = False
        assert widget.visual_mode is True
        assert widget.visual_line_mode is False

        widget._visual_line_mode = True
        assert widget.visual_line_mode is True

    def test_visual_state_can_be_cleared(self) -> None:
        """Test visual state can be cleared directly."""
        widget = TailLog()
        widget._visual_mode = True
        widget._visual_line_mode = True
        widget._visual_anchor_line = 10
        widget._visual_anchor_col = 5

        # Clear directly (avoid _exit_visual_mode which posts message)
        widget._visual_mode = False
        widget._visual_line_mode = False
        widget._visual_anchor_line = None

        assert widget._visual_mode is False
        assert widget._visual_line_mode is False
        assert widget._visual_anchor_line is None

    def test_cursor_col_initial_value(self) -> None:
        """Test cursor column starts at 0."""
        widget = TailLog()
        assert widget._cursor_col == 0

    def test_visual_anchor_col_initial_value(self) -> None:
        """Test visual anchor column starts at 0."""
        widget = TailLog()
        assert widget._visual_anchor_col == 0
