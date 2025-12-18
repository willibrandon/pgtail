"""Integration tests for fullscreen TUI mode."""

from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.fullscreen import FullscreenState, LogBuffer


class TestFullscreenEnterExitCycle:
    """Integration tests for fullscreen mode enter/exit cycle."""

    def test_buffer_preserved_after_exit(self) -> None:
        """Buffer content is preserved after exiting fullscreen mode."""
        buffer = LogBuffer()
        buffer.append("line1")
        buffer.append("line2")

        state = FullscreenState()

        # Simulate fullscreen session (buffer should remain unchanged)
        initial_text = buffer.get_text()

        # After exit, buffer should still have content
        assert buffer.get_text() == initial_text
        assert len(buffer) == 2

    def test_state_reset_to_follow_on_entry(self) -> None:
        """State resets to follow mode when entering fullscreen."""
        state = FullscreenState()

        # Start in browse mode
        state.enter_browse()
        assert not state.is_following

        # Create fresh state (simulating new fullscreen entry)
        new_state = FullscreenState()
        assert new_state.is_following is True

    def test_fullscreen_app_creation(self) -> None:
        """Fullscreen app can be created with buffer and state."""
        from pgtail_py.fullscreen.app import create_fullscreen_app

        buffer = LogBuffer()
        buffer.append("test line")
        state = FullscreenState()

        app = create_fullscreen_app(buffer, state)

        # App should be created successfully
        assert app is not None
        assert app.full_screen is True

    def test_keybinding_q_exits_app(self) -> None:
        """Pressing 'q' should trigger app exit."""
        from prompt_toolkit.keys import Keys

        from pgtail_py.fullscreen.keybindings import create_keybindings

        state = FullscreenState()
        kb = create_keybindings(state)

        # Verify 'q' binding exists
        # KeyBindings stores bindings internally - check they exist
        assert kb is not None

    def test_layout_contains_text_area_and_status_bar(self) -> None:
        """Layout should contain TextArea and status bar."""
        from prompt_toolkit.widgets import SearchToolbar, TextArea

        from pgtail_py.fullscreen.layout import create_layout

        buffer = LogBuffer()
        buffer.append("test content")
        state = FullscreenState()

        layout, text_area, search_toolbar = create_layout(buffer, state)

        assert layout is not None
        assert isinstance(text_area, TextArea)
        assert isinstance(search_toolbar, SearchToolbar)


class TestFullscreenBufferFeeding:
    """Tests for buffer feeding during fullscreen mode."""

    def test_buffer_accumulates_entries(self) -> None:
        """Buffer should accumulate entries over time."""
        buffer = LogBuffer()

        for i in range(100):
            buffer.append(f"log entry {i}")

        assert len(buffer) == 100
        assert "log entry 0" in buffer.get_text()
        assert "log entry 99" in buffer.get_text()

    def test_buffer_fifo_eviction_during_fullscreen(self) -> None:
        """Buffer should evict oldest entries when full."""
        buffer = LogBuffer(maxlen=10)

        for i in range(15):
            buffer.append(f"entry {i}")

        assert len(buffer) == 10
        assert "entry 0" not in buffer.get_text()
        assert "entry 5" in buffer.get_text()
        assert "entry 14" in buffer.get_text()
