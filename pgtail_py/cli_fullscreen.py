"""Fullscreen command handler for pgtail."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.cli_utils import warn
from pgtail_py.fullscreen.app import run_fullscreen

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def fullscreen_command(args: str, state: AppState) -> None:
    """Handle 'fullscreen' / 'fs' command.

    Enters fullscreen TUI mode to view buffered log content.
    Buffer is preserved across mode switches and tail stop/start.

    Args:
        args: Command arguments (unused)
        state: Application state

    Behavior:
    - If no buffer content: Print error message
    - Otherwise: Enter fullscreen mode to view buffer
    - On 'q' exit: Return to REPL with buffer preserved
    """
    buffer = state.get_or_create_buffer()

    if len(buffer) == 0:
        warn("No log content. Use 'tail <id>' first to capture some logs.")
        return

    fs_state = state.get_or_create_fullscreen_state()
    run_fullscreen(buffer, fs_state)
