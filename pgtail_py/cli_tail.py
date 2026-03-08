"""Command handlers for tail mode.

This module provides command parsing and handling for commands executed
within the status bar tail mode interface, including filter commands,
display commands, and exit commands.

The implementation is split across multiple modules for maintainability:
- cli_tail.py: Main dispatcher and command routing
- cli_tail_filters.py: Filter command handlers (level, filter, since, etc.)
- cli_tail_display.py: Display command handlers (errors, connections)
- cli_tail_help.py: Help command handlers and COMMAND_HELP dictionary
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

# Re-export COMMAND_HELP for backward compatibility
from pgtail_py.cli_tail_help import COMMAND_HELP, handle_help_command, show_command_help

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus
    from pgtail_py.tailer import LogTailer

# Re-export for backward compatibility
__all__ = [
    "TAIL_MODE_COMMANDS",
    "COMMAND_HELP",
    "handle_tail_command",
]


# Supported tail mode commands
TAIL_MODE_COMMANDS: list[str] = [
    # Filter commands (modify what's shown)
    "level",  # level error,warning
    "filter",  # filter /pattern/
    "since",  # since 5m
    "until",  # until 14:30
    "between",  # between 14:00 14:30
    "slow",  # slow 100
    "clear",  # clear all filters
    # Display commands (inline output)
    "errors",  # show error summary
    "connections",  # show connection summary
    "highlight",  # highlight list/enable/disable
    # Notification commands
    "notify",  # configure notifications
    # Config commands
    "set",  # set config values
    # Export commands
    "export",  # export entries to file
    # Mode commands
    "pause",  # enter PAUSED mode
    "p",  # alias for pause
    "follow",  # enter FOLLOW mode
    "f",  # alias for follow
    # Help
    "help",  # show help
    # Exit commands
    "stop",  # return to REPL
    "exit",  # return to REPL
    "q",  # return to REPL
]


def handle_tail_command(
    cmd: str,
    args: list[str],
    status: TailStatus,
    state: AppState,
    tailer: LogTailer,
    stop_callback: Callable[[], None],
    log_widget: TailLog | None = None,
) -> bool:
    """Handle a command entered in tail mode.

    Args:
        cmd: Command name (e.g., 'level', 'filter', 'stop')
        args: Command arguments
        status: TailStatus instance
        state: AppState with filter settings
        tailer: LogTailer instance
        stop_callback: Callback to stop the application
        log_widget: TailLog widget (Textual mode) or None

    Returns:
        True if command was handled, False if unknown command
    """
    # Handle '<cmd> help' or '<cmd> ?' variant - e.g., 'level help', 'filter ?'
    if args and args[0].lower() in ("help", "?") and cmd in COMMAND_HELP:
        return show_command_help(cmd, log_widget)

    # Exit commands
    if cmd in ("stop", "exit", "q"):
        stop_callback()
        return True

    # Mode commands
    if cmd in ("pause", "p"):
        status.set_follow_mode(False, 0)
        return True

    if cmd in ("follow", "f"):
        status.set_follow_mode(True, 0)
        return True

    # Filter commands - import handlers from cli_tail_filters
    if cmd == "level":
        from pgtail_py.cli_tail_filters import handle_level_command

        return handle_level_command(args, status, state, tailer, log_widget)

    if cmd == "filter":
        from pgtail_py.cli_tail_filters import handle_filter_command

        return handle_filter_command(args, status, state, tailer, log_widget)

    if cmd == "since":
        from pgtail_py.cli_tail_filters import handle_since_command

        return handle_since_command(args, status, state, tailer, log_widget)

    if cmd == "until":
        from pgtail_py.cli_tail_filters import handle_until_command

        return handle_until_command(args, status, state, tailer, log_widget)

    if cmd == "between":
        from pgtail_py.cli_tail_filters import handle_between_command

        return handle_between_command(args, status, state, tailer, log_widget)

    if cmd == "slow":
        from pgtail_py.cli_tail_filters import handle_slow_command

        return handle_slow_command(args, status, state, log_widget)

    if cmd == "clear":
        from pgtail_py.cli_tail_filters import handle_clear_command

        return handle_clear_command(status, state, tailer, log_widget)

    # Display commands - import handlers from cli_tail_display
    if cmd == "errors":
        from pgtail_py.cli_tail_display import handle_errors_command

        return handle_errors_command(args, state, log_widget)

    if cmd == "connections":
        from pgtail_py.cli_tail_display import handle_connections_command

        return handle_connections_command(args, state, log_widget)

    if cmd == "highlight":
        from pgtail_py.cli_tail_display import handle_highlight_command

        return handle_highlight_command(args, status, state, log_widget)

    # Notification commands
    if cmd == "notify":
        from pgtail_py.cli_notify import notify_command

        notify_command(state, args, log_widget=log_widget)
        return True

    # Config commands - import handlers from cli_tail_display
    if cmd == "set":
        from pgtail_py.cli_tail_display import handle_set_command

        return handle_set_command(args, state, log_widget)

    # Help command
    if cmd == "help":
        return handle_help_command(args, log_widget)

    return False
