"""Contract: TailApp interface for Status Bar Tail Mode.

This module defines the interface for the main application coordinator
that manages the layout, buffer, status, and log streaming.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance


class TailAppProtocol(Protocol):
    """Protocol for the main tail mode application coordinator."""

    @property
    def is_running(self) -> bool:
        """True if the application is currently running."""
        ...

    def start(
        self,
        state: AppState,
        instance: Instance,
        log_path: Path,
    ) -> None:
        """Start the tail mode application.

        This method blocks until the user exits tail mode.

        Args:
            state: pgtail AppState with filter settings
            instance: PostgreSQL instance being tailed
            log_path: Path to the log file

        Side effects:
            - Creates LogTailer for background streaming
            - Creates TailBuffer and TailStatus
            - Builds TailLayout
            - Runs prompt_toolkit Application event loop
            - Returns control to caller when user exits
        """
        ...

    def stop(self) -> None:
        """Stop the tail mode application.

        Called by exit commands (stop, exit, q) or Ctrl+C.

        Side effects:
            - Stops background entry consumer
            - Stops LogTailer
            - Exits Application event loop
        """
        ...


class TailCommandHandler(Protocol):
    """Protocol for handling commands within tail mode."""

    def handle_command(self, command: str, args: list[str]) -> bool:
        """Handle a command entered in tail mode.

        Args:
            command: Command name (e.g., 'level', 'filter', 'stop')
            args: Command arguments

        Returns:
            True if command was handled, False if unknown command

        Side effects:
            - May update filter state
            - May insert command output inline
            - May trigger application exit
        """
        ...


# Supported tail mode commands
TAIL_MODE_COMMANDS: list[str] = [
    # Filter commands (modify what's shown)
    'level',      # level error,warning
    'filter',     # filter /pattern/
    'since',      # since 5m
    'until',      # until 14:30
    'between',    # between 14:00 14:30
    'slow',       # slow 100
    'clear',      # clear all filters

    # Display commands (inline output)
    'errors',     # show error summary
    'connections', # show connection summary

    # Mode commands
    'pause',      # enter PAUSED mode
    'follow',     # enter FOLLOW mode

    # Exit commands
    'stop',       # return to REPL
    'exit',       # return to REPL
    'q',          # return to REPL
]


# Key bindings for tail mode
TAIL_MODE_KEYS: dict[str, str] = {
    'up': 'Scroll up 1 line',
    'down': 'Scroll down 1 line',
    'pageup': 'Scroll up 1 page',
    'pagedown': 'Scroll down 1 page',
    'home': 'Scroll to buffer start',
    'end': 'Resume follow mode',
    'c-l': 'Redraw screen',
    'c-c': 'Exit to REPL',
}
