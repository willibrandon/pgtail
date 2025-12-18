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
    """Tests for the Escape keybinding (toggle follow/browse when not searching)."""

    def test_escape_bindings_exist(self) -> None:
        """Escape keybindings are registered (one for toggle, one for cancel search)."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        escape_bindings = [b for b in bindings if "escape" in str(b.keys)]
        # Should have 2: one for toggle (not searching), one for cancel (searching)
        assert len(escape_bindings) == 2

    def test_escape_toggles_follow_to_browse(self) -> None:
        """Pressing Escape in follow mode switches to browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        # Find the escape binding for non-search (has escape_handler in handler name)
        bindings = list(kb.bindings)
        escape_bindings = [
            b for b in bindings
            if "escape" in str(b.keys) and "escape_handler" in str(b.handler)
        ]
        assert len(escape_bindings) == 1

        # Create mock event with no search pattern
        event = MagicMock()
        event.app = MagicMock()
        event.app.layout.current_control = MagicMock()
        event.app.layout.current_control.search_state = MagicMock()
        event.app.layout.current_control.search_state.text = ""  # No search pattern

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

        # Find the escape binding for non-search (has escape_handler in handler name)
        bindings = list(kb.bindings)
        escape_bindings = [
            b for b in bindings
            if "escape" in str(b.keys) and "escape_handler" in str(b.handler)
        ]
        assert len(escape_bindings) == 1

        # Create mock event with no search pattern
        event = MagicMock()
        event.app = MagicMock()
        event.app.layout.current_control = MagicMock()
        event.app.layout.current_control.search_state = MagicMock()
        event.app.layout.current_control.search_state.text = ""  # No search pattern

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


class TestSearchKeybindings:
    """Tests for search keybindings (/, ?, n, N)."""

    def test_forward_slash_binding_exists(self) -> None:
        """/ keybinding is registered for forward search."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        slash_bindings = [b for b in bindings if "/" in str(b.keys)]
        assert len(slash_bindings) == 1

    def test_question_mark_binding_exists(self) -> None:
        """? keybinding is registered for backward search."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        question_bindings = [b for b in bindings if "?" in str(b.keys)]
        assert len(question_bindings) == 1

    def test_n_binding_exists(self) -> None:
        """n keybinding is registered for next match."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        # Check for 'n' key binding (not containing 'N' or 'down')
        n_bindings = [
            b for b in bindings
            if "'n'" in str(b.keys).lower() and "'n'" in str(b.keys) and "down" not in str(b.keys)
        ]
        assert len(n_bindings) >= 1

    def test_N_binding_exists(self) -> None:
        """N keybinding is registered for previous match."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        # Check for 'N' (shift+n) key binding
        N_bindings = [b for b in bindings if "'N'" in str(b.keys)]
        assert len(N_bindings) >= 1


class TestPageNavigationKeybindings:
    """Tests for page navigation keybindings (Ctrl+D/U, g/G)."""

    def test_ctrl_d_binding_exists(self) -> None:
        """Ctrl+D keybinding is registered for half-page down."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        ctrl_d_bindings = [b for b in bindings if "c-d" in str(b.keys)]
        assert len(ctrl_d_bindings) == 1

    def test_ctrl_u_binding_exists(self) -> None:
        """Ctrl+U keybinding is registered for half-page up."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        ctrl_u_bindings = [b for b in bindings if "c-u" in str(b.keys)]
        assert len(ctrl_u_bindings) == 1

    def test_g_binding_exists(self) -> None:
        """g keybinding is registered for jump to top."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        g_bindings = [b for b in bindings if "'g'" in str(b.keys)]
        assert len(g_bindings) == 1

    def test_G_binding_exists(self) -> None:
        """G keybinding is registered for jump to bottom."""
        state = FullscreenState()
        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        G_bindings = [b for b in bindings if "'G'" in str(b.keys)]
        assert len(G_bindings) == 1

    def test_ctrl_d_enters_browse_mode(self) -> None:
        """Ctrl+D enters browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        ctrl_d_bindings = [b for b in bindings if "c-d" in str(b.keys)]

        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.document = MagicMock()
        event.current_buffer.document.line_count = 100
        event.current_buffer.document.cursor_position_row = 10

        ctrl_d_bindings[0].handler(event)

        assert state.mode == DisplayMode.BROWSE

    def test_g_enters_browse_mode(self) -> None:
        """g enters browse mode and moves to top."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        g_bindings = [b for b in bindings if "'g'" in str(b.keys)]

        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.cursor_position = 500

        g_bindings[0].handler(event)

        assert state.mode == DisplayMode.BROWSE
        assert event.current_buffer.cursor_position == 0


class TestMouseScrollBehavior:
    """Tests for mouse scroll behavior.

    Mouse scroll triggers browse mode through two mechanisms:
    1. Some terminals send scroll as Up/Down key presses (tested via arrow handlers)
    2. Mouse events are intercepted via wrapped Window._scroll_up/_scroll_down methods
    """

    def test_down_arrow_enters_browse_mode_for_mouse_scroll(self) -> None:
        """Down arrow (used for mouse scroll down in some terminals) enters browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        down_bindings = [b for b in bindings if "down" in str(b.keys)]
        assert len(down_bindings) == 1

        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.cursor_position = 0
        event.current_buffer.document = MagicMock()
        event.current_buffer.document.get_cursor_down_position.return_value = 10

        down_bindings[0].handler(event)

        # Mouse scroll (via down arrow) should enter browse mode
        assert state.mode == DisplayMode.BROWSE

    def test_up_arrow_enters_browse_mode_for_mouse_scroll(self) -> None:
        """Up arrow (used for mouse scroll up in some terminals) enters browse mode."""
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        kb = create_keybindings(state)

        bindings = list(kb.bindings)
        up_bindings = [b for b in bindings if "up" in str(b.keys)]
        assert len(up_bindings) == 1

        event = MagicMock()
        event.app = MagicMock()
        event.current_buffer = MagicMock()
        event.current_buffer.cursor_position = 50
        event.current_buffer.document = MagicMock()
        event.current_buffer.document.get_cursor_up_position.return_value = -10

        up_bindings[0].handler(event)

        # Mouse scroll (via up arrow) should enter browse mode
        assert state.mode == DisplayMode.BROWSE


class TestWindowScrollWrapping:
    """Tests for Window scroll method wrapping (for mouse wheel events)."""

    def test_window_scroll_down_enters_browse_mode(self) -> None:
        """Window._scroll_down (called by mouse wheel) enters browse mode."""
        from pgtail_py.fullscreen.buffer import LogBuffer
        from pgtail_py.fullscreen.layout import create_layout

        buffer = LogBuffer()
        buffer.append("Line 1")
        buffer.append("Line 2")
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        # Create layout which wraps the window's scroll methods
        _layout, text_area, _search = create_layout(buffer, state)

        # Call the wrapped scroll method (simulating mouse wheel down)
        text_area.window._scroll_down()

        # Should have entered browse mode
        assert state.mode == DisplayMode.BROWSE

    def test_window_scroll_up_enters_browse_mode(self) -> None:
        """Window._scroll_up (called by mouse wheel) enters browse mode."""
        from pgtail_py.fullscreen.buffer import LogBuffer
        from pgtail_py.fullscreen.layout import create_layout

        buffer = LogBuffer()
        buffer.append("Line 1")
        buffer.append("Line 2")
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        # Create layout which wraps the window's scroll methods
        _layout, text_area, _search = create_layout(buffer, state)

        # Call the wrapped scroll method (simulating mouse wheel up)
        text_area.window._scroll_up()

        # Should have entered browse mode
        assert state.mode == DisplayMode.BROWSE


class TestMouseClickBehavior:
    """Tests for mouse click behavior (triggers browse mode)."""

    def test_mouse_click_enters_browse_mode(self) -> None:
        """Mouse click (MOUSE_DOWN) enters browse mode."""
        from prompt_toolkit.data_structures import Point
        from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

        from pgtail_py.fullscreen.buffer import LogBuffer
        from pgtail_py.fullscreen.layout import create_layout

        buffer = LogBuffer()
        buffer.append("Line 1")
        buffer.append("Line 2")
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        # Create layout which wraps the control's mouse handler
        _layout, text_area, _search = create_layout(buffer, state)

        # Create a mock mouse down event
        mouse_event = MouseEvent(
            position=Point(x=0, y=0),
            event_type=MouseEventType.MOUSE_DOWN,
            button=MouseButton.LEFT,
            modifiers=frozenset(),
        )

        # Call the wrapped mouse handler
        text_area.control.mouse_handler(mouse_event)

        # Should have entered browse mode
        assert state.mode == DisplayMode.BROWSE

    def test_mouse_move_does_not_enter_browse_mode(self) -> None:
        """Mouse move (without click) does not enter browse mode."""
        from prompt_toolkit.data_structures import Point
        from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType

        from pgtail_py.fullscreen.buffer import LogBuffer
        from pgtail_py.fullscreen.layout import create_layout

        buffer = LogBuffer()
        buffer.append("Line 1")
        state = FullscreenState()
        assert state.mode == DisplayMode.FOLLOW

        _layout, text_area, _search = create_layout(buffer, state)

        # Create a mouse move event (not a click)
        mouse_event = MouseEvent(
            position=Point(x=0, y=0),
            event_type=MouseEventType.MOUSE_MOVE,
            button=MouseButton.NONE,
            modifiers=frozenset(),
        )

        text_area.control.mouse_handler(mouse_event)

        # Should still be in follow mode
        assert state.mode == DisplayMode.FOLLOW
