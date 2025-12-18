"""Vim-style key bindings for fullscreen TUI mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import search
from prompt_toolkit.filters import is_searching
from prompt_toolkit.key_binding import KeyBindings

if TYPE_CHECKING:
    from pgtail_py.fullscreen.state import FullscreenState


def create_keybindings(state: FullscreenState) -> KeyBindings:
    """Create vim-style key bindings for fullscreen mode.

    Bindings:
    - q: Exit fullscreen mode
    - Escape: Toggle follow/browse mode (or cancel search if searching)
    - f: Enter follow mode (resume auto-scroll)
    - j/Down: Scroll down one line (enters browse mode)
    - k/Up: Scroll up one line (enters browse mode)
    - Ctrl+D: Half-page down (enters browse mode)
    - Ctrl+U: Half-page up (enters browse mode)
    - g: Jump to top (enters browse mode)
    - G: Jump to bottom (enters follow mode)
    - /: Start forward search
    - ?: Start backward search
    - n: Next search match
    - N: Previous search match

    Args:
        state: FullscreenState for mode toggling

    Returns:
        Configured KeyBindings
    """
    kb = KeyBindings()

    @kb.add("q", filter=~is_searching)
    def exit_fullscreen(event: object) -> None:
        """Exit fullscreen mode and return to REPL."""
        event.app.exit()  # type: ignore[attr-defined]

    @kb.add("escape", filter=~is_searching)
    def escape_handler(event: object) -> None:
        """Clear search highlights, or toggle follow/browse if no search active."""
        buffer_control = event.app.layout.current_control  # type: ignore[attr-defined]
        # If there's an active search pattern, clear it first
        if hasattr(buffer_control, "search_state") and buffer_control.search_state.text:
            buffer_control.search_state.text = ""
            event.app.invalidate()  # type: ignore[attr-defined]
        else:
            # No search active, toggle follow/browse mode
            state.toggle_follow()
            event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("escape", filter=is_searching)
    def cancel_search(event: object) -> None:
        """Cancel search and return to log view."""
        search.stop_search()
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("f", filter=~is_searching)
    def enter_follow_mode(event: object) -> None:
        """Enter follow mode (resume auto-scroll to bottom)."""
        state.enter_follow()
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("j", filter=~is_searching)
    def scroll_down(event: object) -> None:
        """Scroll down one line (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        offset = buffer.document.get_cursor_down_position()
        buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("k", filter=~is_searching)
    def scroll_up(event: object) -> None:
        """Scroll up one line (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        offset = buffer.document.get_cursor_up_position()
        buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("down")
    def arrow_down(event: object) -> None:
        """Scroll down one line with arrow key (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        offset = buffer.document.get_cursor_down_position()
        buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("up")
    def arrow_up(event: object) -> None:
        """Scroll up one line with arrow key (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        offset = buffer.document.get_cursor_up_position()
        buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    # Search keybindings
    @kb.add("/", filter=~is_searching)
    def start_forward_search(event: object) -> None:
        """Start forward search (vim-style /)."""
        state.enter_browse()  # Switch to browse mode for searching
        search.start_search(direction=search.SearchDirection.FORWARD)

    @kb.add("?", filter=~is_searching)
    def start_backward_search(event: object) -> None:
        """Start backward search (vim-style ?)."""
        state.enter_browse()  # Switch to browse mode for searching
        search.start_search(direction=search.SearchDirection.BACKWARD)

    @kb.add("n", filter=~is_searching)
    def next_match(event: object) -> None:
        """Jump to next search match."""
        buffer_control = event.app.layout.current_control  # type: ignore[attr-defined]
        if hasattr(buffer_control, "search_state") and buffer_control.search_state.text:
            buffer_control.buffer.apply_search(
                buffer_control.search_state, include_current_position=False, count=1
            )

    @kb.add("N", filter=~is_searching)
    def prev_match(event: object) -> None:
        """Jump to previous search match."""
        buffer_control = event.app.layout.current_control  # type: ignore[attr-defined]
        if hasattr(buffer_control, "search_state") and buffer_control.search_state.text:
            # Invert direction for previous match
            inverted = ~buffer_control.search_state
            buffer_control.buffer.apply_search(
                inverted, include_current_position=False, count=1
            )

    # Page navigation keybindings
    @kb.add("c-d", filter=~is_searching)
    def half_page_down(event: object) -> None:
        """Scroll down half a page (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        # Move cursor down by half the visible lines (estimate ~20 lines)
        lines_to_move = max(1, buffer.document.line_count // 20)
        for _ in range(lines_to_move):
            offset = buffer.document.get_cursor_down_position()
            if offset == 0:
                break
            buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("c-u", filter=~is_searching)
    def half_page_up(event: object) -> None:
        """Scroll up half a page (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        # Move cursor up by half the visible lines (estimate ~20 lines)
        lines_to_move = max(1, buffer.document.line_count // 20)
        for _ in range(lines_to_move):
            offset = buffer.document.get_cursor_up_position()
            if offset == 0:
                break
            buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("g", filter=~is_searching)
    def jump_to_top(event: object) -> None:
        """Jump to top of buffer (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        buffer.cursor_position = 0
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("G", filter=~is_searching)
    def jump_to_bottom(event: object) -> None:
        """Jump to bottom of buffer (enters follow mode)."""
        state.enter_follow()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        buffer.cursor_position = len(buffer.text)
        event.app.invalidate()  # type: ignore[attr-defined]

    return kb
