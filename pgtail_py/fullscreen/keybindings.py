"""Vim-style key bindings for fullscreen TUI mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings

if TYPE_CHECKING:
    from pgtail_py.fullscreen.state import FullscreenState


def create_keybindings(state: FullscreenState) -> KeyBindings:
    """Create vim-style key bindings for fullscreen mode.

    Bindings:
    - q: Exit fullscreen mode
    - Escape: Toggle follow/browse mode
    - f: Enter follow mode (resume auto-scroll)
    - j/Down: Scroll down one line (enters browse mode)
    - k/Up: Scroll up one line (enters browse mode)

    Args:
        state: FullscreenState for mode toggling

    Returns:
        Configured KeyBindings
    """
    kb = KeyBindings()

    @kb.add("q")
    def exit_fullscreen(event: object) -> None:
        """Exit fullscreen mode and return to REPL."""
        event.app.exit()  # type: ignore[attr-defined]

    @kb.add("escape")
    def toggle_follow_mode(event: object) -> None:
        """Toggle between follow and browse modes."""
        state.toggle_follow()
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("f")
    def enter_follow_mode(event: object) -> None:
        """Enter follow mode (resume auto-scroll to bottom)."""
        state.enter_follow()
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("j")
    def scroll_down(event: object) -> None:
        """Scroll down one line (enters browse mode)."""
        state.enter_browse()
        buffer = event.current_buffer  # type: ignore[attr-defined]
        offset = buffer.document.get_cursor_down_position()
        buffer.cursor_position += offset
        event.app.invalidate()  # type: ignore[attr-defined]

    @kb.add("k")
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

    return kb
