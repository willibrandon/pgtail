"""Full-screen Application setup for pgtail."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from prompt_toolkit.application import Application

from pgtail_py.fullscreen.keybindings import create_keybindings
from pgtail_py.fullscreen.layout import create_layout

if TYPE_CHECKING:
    from pgtail_py.fullscreen.buffer import LogBuffer
    from pgtail_py.fullscreen.state import FullscreenState


def create_fullscreen_app(
    buffer: LogBuffer,
    state: FullscreenState,
) -> Application[None]:
    """Create prompt_toolkit Application for fullscreen mode.

    Args:
        buffer: LogBuffer to display (shared with REPL mode)
        state: FullscreenState for mode management

    Returns:
        Configured Application ready to run
    """
    layout, text_area, search_toolbar = create_layout(buffer, state)
    kb = create_keybindings(state)

    app: Application[None] = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        enable_page_navigation_bindings=True,
    )

    # Store references for live updates
    app._pgtail_buffer = buffer  # type: ignore[attr-defined]
    app._pgtail_state = state  # type: ignore[attr-defined]
    app._pgtail_text_area = text_area  # type: ignore[attr-defined]

    return app


async def _update_display_loop(
    app: Application[None],
    buffer: LogBuffer,
    text_area: object,
    state: FullscreenState,
) -> None:
    """Background task to update display with new buffer content.

    Args:
        app: The running Application
        buffer: LogBuffer to read from
        text_area: TextArea widget to update
        state: FullscreenState for mode checking
    """
    last_len = len(buffer)

    while True:
        await asyncio.sleep(0.1)  # Update every 100ms

        current_len = len(buffer)
        if current_len != last_len:
            new_text = buffer.get_text()
            text_area.text = new_text  # type: ignore[attr-defined]

            if state.is_following:
                # Auto-scroll to bottom in follow mode
                text_area.buffer.cursor_position = len(new_text)  # type: ignore[attr-defined]

            app.invalidate()
            last_len = current_len


def run_fullscreen(
    buffer: LogBuffer,
    state: FullscreenState,
) -> None:
    """Run fullscreen mode (blocking).

    Creates and runs the fullscreen Application. Returns when
    user presses 'q' to exit.

    Args:
        buffer: LogBuffer to display
        state: FullscreenState for mode management
    """
    app = create_fullscreen_app(buffer, state)
    text_area = app._pgtail_text_area  # type: ignore[attr-defined]

    async def run_with_updates() -> None:
        """Run app with background update task."""
        update_task = asyncio.create_task(
            _update_display_loop(app, buffer, text_area, state)
        )
        try:
            await app.run_async()
        finally:
            update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await update_task

    asyncio.run(run_with_updates())
