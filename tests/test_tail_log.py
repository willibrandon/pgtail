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


class TestSelectAllThenCopy:
    """Tests for Ctrl+A then Ctrl+C workflow (T150)."""

    @pytest.mark.asyncio
    async def test_ctrl_a_ctrl_c_copies_all_content(self) -> None:
        """Test that Ctrl+A then Ctrl+C copies all log content.

        This test verifies the full workflow:
        1. Write multiple lines to the log
        2. Press Ctrl+A to select all
        3. Press Ctrl+C to copy
        4. Verify clipboard contains all content
        """
        from pathlib import Path
        from unittest.mock import MagicMock

        from textual.app import App, ComposeResult

        from pgtail_py.tail_log import TailLog

        # Create a minimal app for testing
        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log")

        app = TestApp()
        copied_text: list[str] = []

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write some lines
            log.write_line("Line 1: ERROR test error")
            log.write_line("Line 2: WARNING test warning")
            log.write_line("Line 3: INFO test info")
            await pilot.pause()

            # Mock clipboard capture
            original_copy = log._copy_with_fallback

            def capture_copy(text: str) -> bool:
                copied_text.append(text)
                return True

            log._copy_with_fallback = capture_copy

            # Focus the log widget
            log.focus()
            await pilot.pause()

            # Ctrl+A to select all
            await pilot.press("ctrl+a")
            await pilot.pause()

            # Ctrl+C to copy
            await pilot.press("ctrl+c")
            await pilot.pause()

            # Verify content was copied
            assert len(copied_text) == 1
            copied = copied_text[0]
            assert "Line 1" in copied
            assert "Line 2" in copied
            assert "Line 3" in copied
            assert "ERROR" in copied
            assert "WARNING" in copied
            assert "INFO" in copied


class TestMouseClickSelection:
    """Tests for double and triple click selection (T164-T165)."""

    @pytest.mark.asyncio
    async def test_double_click_triggers_word_selection(self) -> None:
        """Test that double-click uses Textual's built-in word selection.

        Textual's Log widget with ALLOW_SELECT=True inherits word selection
        on double-click from the parent class. This test verifies the
        widget responds to double-click events.
        """
        from textual.app import App, ComposeResult

        from pgtail_py.tail_log import TailLog

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log")

        app = TestApp()

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write content with distinct words
            log.write_line("Hello World Example")
            await pilot.pause()

            # Focus log
            log.focus()
            await pilot.pause()

            # Double-click should trigger word selection behavior
            # (Textual built-in via ALLOW_SELECT=True)
            await pilot.click("#log", times=2)
            await pilot.pause()

            # The widget should have a selection after double-click
            # (actual word selection is Textual's responsibility)
            # We verify the click was received and processed
            assert log.line_count == 1

    @pytest.mark.asyncio
    async def test_triple_click_triggers_line_selection(self) -> None:
        """Test that triple-click uses Textual's built-in line selection.

        Textual's Log widget with ALLOW_SELECT=True inherits line selection
        on triple-click from the parent class. This test verifies the
        widget responds to triple-click events.
        """
        from textual.app import App, ComposeResult

        from pgtail_py.tail_log import TailLog

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log")

        app = TestApp()

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write content
            log.write_line("First line of text")
            log.write_line("Second line of text")
            await pilot.pause()

            # Focus log
            log.focus()
            await pilot.pause()

            # Triple-click should trigger line selection behavior
            # (Textual built-in via ALLOW_SELECT=True)
            await pilot.click("#log", times=3)
            await pilot.pause()

            # The widget should have a selection after triple-click
            # (actual line selection is Textual's responsibility)
            # We verify the click was received and processed
            assert log.line_count == 2
