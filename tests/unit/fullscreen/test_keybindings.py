"""Unit tests for fullscreen keybindings."""

from unittest.mock import MagicMock

import pytest

from pgtail_py.fullscreen.keybindings import create_keybindings
from pgtail_py.fullscreen.state import DisplayMode, FullscreenState


class TestExitKeybinding:
    """Tests for the q (exit) keybinding."""

    def test_q_exits_app(self) -> None:
        """Pressing q calls app.exit()."""
        state = FullscreenState()
        kb = create_keybindings(state)

        # Find the q binding
        bindings = list(kb.bindings)
        q_bindings = [b for b in bindings if "q" in str(b.keys)]
        assert len(q_bindings) == 1

        # Create mock event
        event = MagicMock()
        event.app = MagicMock()

        # Execute the handler
        q_bindings[0].handler(event)

        # Verify app.exit() was called
        event.app.exit.assert_called_once()


class TestEscapeKeybinding:
    """Tests for the Escape keybinding (toggle follow/browse)."""

    def test_escape_toggles_follow_to_browse(self) -> None:
        """Pressing Escape in follow mode switches to browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        # Find the escape binding
        bindings = list(kb.bindings)
        escape_bindings = [b for b in bindings if "escape" in str(b.keys)]
        assert len(escape_bindings) == 1

        # Create mock event
        event = MagicMock()
        event.app = MagicMock()

        # Execute the handler
        escape_bindings[0].handler(event)

        # Verify mode toggled
        assert state.mode == DisplayMode.BROWSE
        event.app.invalidate.assert_called_once()

    def test_escape_toggles_browse_to_follow(self) -> None:
        """Pressing Escape in browse mode switches to follow mode."""
        state = FullscreenState()
        state.enter_browse()
        assert state.mode == DisplayMode.BROWSE

        kb = create_keybindings(state)

        # Find the escape binding
        bindings = list(kb.bindings)
        escape_bindings = [b for b in bindings if "escape" in str(b.keys)]
        assert len(escape_bindings) == 1

        # Create mock event
        event = MagicMock()
        event.app = MagicMock()

        # Execute the handler
        escape_bindings[0].handler(event)

        # Verify mode toggled
        assert state.mode == DisplayMode.FOLLOW
        event.app.invalidate.assert_called_once()


class TestFKeybinding:
    """Tests for the f keybinding (enter follow mode)."""

    def test_f_enters_follow_mode(self) -> None:
        """Pressing f enters follow mode."""
        state = FullscreenState()
        state.enter_browse()
        assert state.mode == DisplayMode.BROWSE

        kb = create_keybindings(state)

        # Find the f binding
        bindings = list(kb.bindings)
        f_bindings = [b for b in bindings if "f" in str(b.keys) and "c-" not in str(b.keys)]
        assert len(f_bindings) == 1

        # Create mock event
        event = MagicMock()
        event.app = MagicMock()

        # Execute the handler
        f_bindings[0].handler(event)

        # Verify entered follow mode
        assert state.mode == DisplayMode.FOLLOW
        event.app.invalidate.assert_called_once()

    def test_f_is_idempotent(self) -> None:
        """Pressing f when already in follow mode is a no-op."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        # Find the f binding
        bindings = list(kb.bindings)
        f_bindings = [b for b in bindings if "f" in str(b.keys) and "c-" not in str(b.keys)]
        assert len(f_bindings) == 1

        # Create mock event
        event = MagicMock()
        event.app = MagicMock()

        # Execute the handler
        f_bindings[0].handler(event)

        # Verify still in follow mode
        assert state.mode == DisplayMode.FOLLOW
        # Invalidate should still be called to refresh display
        event.app.invalidate.assert_called_once()


class TestScrollKeybindings:
    """Tests for j/k and arrow scroll keybindings."""

    def test_j_binding_exists(self) -> None:
        """j keybinding is registered."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        j_bindings = [b for b in bindings if "j" in str(b.keys)]
        assert len(j_bindings) == 1

    def test_k_binding_exists(self) -> None:
        """k keybinding is registered."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        k_bindings = [b for b in bindings if "k" in str(b.keys)]
        assert len(k_bindings) == 1

    def test_down_binding_exists(self) -> None:
        """Down arrow keybinding is registered."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        down_bindings = [b for b in bindings if "down" in str(b.keys)]
        assert len(down_bindings) == 1

    def test_up_binding_exists(self) -> None:
        """Up arrow keybinding is registered."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        up_bindings = [b for b in bindings if "up" in str(b.keys)]
        assert len(up_bindings) == 1

    def test_j_enters_browse_mode(self) -> None:
        """Pressing j in follow mode switches to browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        # Find the j binding
        bindings = list(kb.bindings)
        j_bindings = [b for b in bindings if "j" in str(b.keys)]

        # Create mock event with buffer
        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.cursor_position = 0
        event.current_buffer.document = MagicMock()
        event.current_buffer.document.get_cursor_down_position.return_value = 10

        # Execute the handler
        j_bindings[0].handler(event)

        # Verify switched to browse mode
        assert state.mode == DisplayMode.BROWSE

    def test_k_enters_browse_mode(self) -> None:
        """Pressing k in follow mode switches to browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        # Find the k binding
        bindings = list(kb.bindings)
        k_bindings = [b for b in bindings if "k" in str(b.keys)]

        # Create mock event with buffer
        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.cursor_position = 50
        event.current_buffer.document = MagicMock()
        event.current_buffer.document.get_cursor_up_position.return_value = -10

        # Execute the handler
        k_bindings[0].handler(event)

        # Verify switched to browse mode
        assert state.mode == DisplayMode.BROWSE
