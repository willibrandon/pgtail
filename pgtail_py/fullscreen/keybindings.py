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

    return kb
