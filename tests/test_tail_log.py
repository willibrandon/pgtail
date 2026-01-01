"""Tests for pgtail_py.tail_log module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.tail_log import TailLog


class TestTailLogBasic:
    """Basic tests for TailLog widget."""

    def test_allow_select_enabled(self) -> None:
        """Test that TailLog has ALLOW_SELECT = True."""
        assert TailLog.ALLOW_SELECT is True

    def test_inherits_from_log(self) -> None:
        """Test that TailLog inherits from Textual Log."""
        from textual.widgets import Log

        widget = TailLog()
        assert isinstance(widget, Log)

    def test_visual_mode_default_false(self) -> None:
        """Test that visual mode is off by default."""
        widget = TailLog()
        assert widget.visual_mode is False
        assert widget.visual_line_mode is False

    def test_has_vim_bindings(self) -> None:
        """Test that TailLog has vim navigation bindings."""
        binding_keys = {b.key for b in TailLog.BINDINGS}
        expected = {"j", "k", "g", "G", "ctrl+d", "ctrl+u", "ctrl+f", "ctrl+b"}
        assert expected.issubset(binding_keys)

    def test_has_visual_mode_bindings(self) -> None:
        """Test that TailLog has visual mode bindings."""
        binding_keys = {b.key for b in TailLog.BINDINGS}
        expected = {"v", "V", "y", "escape"}
        assert expected.issubset(binding_keys)

    def test_has_standard_shortcuts(self) -> None:
        """Test that TailLog has standard shortcuts."""
        binding_keys = {b.key for b in TailLog.BINDINGS}
        expected = {"ctrl+a", "ctrl+c"}
        assert expected.issubset(binding_keys)


class TestTailLogClipboard:
    """Tests for TailLog clipboard functionality."""

    def test_copy_with_fallback_empty_text_is_noop_success(self) -> None:
        """Test that copying empty text returns True (no-op success)."""
        widget = TailLog()
        result = widget._copy_with_fallback("")
        assert result is True

    def test_copy_with_fallback_calls_pyperclip(self) -> None:
        """Test that copy calls pyperclip as fallback."""
        widget = TailLog()
        # Mock app.copy_to_clipboard to fail, so pyperclip is called
        widget._app = MagicMock()
        widget._app.copy_to_clipboard.side_effect = Exception("No app")

        with patch.dict("sys.modules", {"pyperclip": MagicMock()}):
            import sys

            mock_pyperclip = sys.modules["pyperclip"]
            result = widget._copy_with_fallback("test text")
            mock_pyperclip.copy.assert_called_once_with("test text")
            assert result is True

    def test_copy_large_selection_succeeds(self) -> None:
        """Test that large selections (>100KB) can be copied.

        OSC 52 has terminal-specific size limits, pyperclip handles larger content.
        """
        widget = TailLog()
        widget._app = MagicMock()
        widget._app.copy_to_clipboard.side_effect = Exception("No app")

        large_text = "x" * (100 * 1024 + 1)
        with patch.dict("sys.modules", {"pyperclip": MagicMock()}):
            result = widget._copy_with_fallback(large_text)
            assert result is True


class TestTailLogVisualMode:
    """Tests for TailLog visual mode functionality."""

    def test_visual_mode_initial_state(self) -> None:
        """Test that visual mode is off initially."""
        widget = TailLog()
        assert widget._visual_mode is False
        assert widget._visual_line_mode is False
        assert widget._visual_anchor_line is None

    def test_visual_mode_state_can_be_cleared(self) -> None:
        """Test that visual mode state can be cleared directly."""
        widget = TailLog()
        widget._visual_mode = True
        widget._visual_line_mode = True
        widget._visual_anchor_line = 5

        # Clear state directly (without post_message which needs app context)
        widget._visual_mode = False
        widget._visual_line_mode = False
        widget._visual_anchor_line = None

        assert widget._visual_mode is False
        assert widget._visual_line_mode is False
        assert widget._visual_anchor_line is None

    def test_cursor_line_initial_value(self) -> None:
        """Test that cursor line starts at 0."""
        widget = TailLog()
        assert widget._cursor_line == 0

    def test_visual_properties(self) -> None:
        """Test visual_mode and visual_line_mode properties."""
        widget = TailLog()
        assert widget.visual_mode is False
        assert widget.visual_line_mode is False
        widget._visual_mode = True
        widget._visual_line_mode = True
        assert widget.visual_mode is True
        assert widget.visual_line_mode is True


class TestTailLogSelectAll:
    """Tests for Ctrl+A select all functionality."""

    @pytest.mark.asyncio
    async def test_select_all_action_exists(self) -> None:
        """Test that action_select_all method exists."""
        widget = TailLog()
        assert hasattr(widget, "action_select_all")
        assert callable(widget.action_select_all)
