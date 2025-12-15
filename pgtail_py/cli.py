"""REPL loop and command handlers for pgtail."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from pgtail_py.config import ensure_history_dir, get_history_path
from pgtail_py.detector import detect_all
from pgtail_py.filter import LogLevel
from pgtail_py.instance import Instance


@dataclass
class AppState:
    """Runtime state for the REPL session.

    Attributes:
        instances: List of detected PostgreSQL instances
        current_instance: Currently selected instance for tailing
        active_levels: Set of log levels to display (all by default)
        tailing: Whether actively tailing a log file
        history_path: Path to command history file
    """

    instances: list[Instance] = field(default_factory=list)
    current_instance: Optional[Instance] = None
    active_levels: set[LogLevel] = field(default_factory=LogLevel.all_levels)
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)


def format_instances_table(instances: list[Instance]) -> str:
    """Format instances as an aligned table.

    Args:
        instances: List of instances to format.

    Returns:
        Formatted table string with ID, Version, Status, Path, and Log columns.
    """
    if not instances:
        return "No PostgreSQL instances found."

    # Calculate column widths
    headers = ["ID", "Version", "Status", "Path", "Log"]
    rows = []
    for inst in instances:
        log_str = str(inst.log_path) if inst.log_path else "disabled"
        # Truncate long paths
        path_str = str(inst.data_dir)
        if len(path_str) > 40:
            path_str = "..." + path_str[-37:]
        if len(log_str) > 30:
            log_str = "..." + log_str[-27:]

        rows.append([
            str(inst.id),
            inst.version,
            inst.status_str,
            path_str,
            log_str,
        ])

    # Calculate max width for each column
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    # Build table
    lines = []
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-" * len(header_line))

    for row in rows:
        line = "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
        lines.append(line)

    return "\n".join(lines)


def list_command(state: AppState) -> None:
    """Handle the 'list' command - show detected instances."""
    print(format_instances_table(state.instances))


def help_command() -> None:
    """Handle the 'help' command - show available commands."""
    help_text = """
Available commands:
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (by ID or data directory path)
  levels [LEVEL...] Set log level filter (e.g., 'levels ERROR WARNING')
                    With no args, shows current filter settings
                    Use 'levels ALL' to show all levels
  stop              Stop current tail and return to prompt
  refresh           Re-scan for PostgreSQL instances
  enable-logging <id>  Enable logging_collector for an instance
  clear             Clear the screen
  help              Show this help message
  quit / exit       Exit pgtail

Keyboard shortcuts:
  Tab       Autocomplete commands and arguments
  Up/Down   Navigate command history
  Ctrl+C    Stop current tail
  Ctrl+D    Exit pgtail
"""
    print(help_text.strip())


def clear_command() -> None:
    """Handle the 'clear' command - clear terminal screen."""
    os.system("cls" if sys.platform == "win32" else "clear")


def refresh_command(state: AppState) -> None:
    """Handle the 'refresh' command - re-scan for instances."""
    print("Scanning for PostgreSQL instances...")
    state.instances = detect_all()
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found.")
    elif count == 1:
        print("Found 1 PostgreSQL instance.")
    else:
        print(f"Found {count} PostgreSQL instances.")


def handle_command(state: AppState, line: str) -> bool:
    """Process a command line and execute the appropriate handler.

    Args:
        state: Current application state.
        line: The command line to process.

    Returns:
        True to continue the REPL loop, False to exit.
    """
    parts = line.strip().split()
    if not parts:
        return True

    cmd = parts[0].lower()
    # args = parts[1:]

    if cmd in ("quit", "exit", "q"):
        return False
    elif cmd == "list":
        list_command(state)
    elif cmd == "help":
        help_command()
    elif cmd == "clear":
        clear_command()
    elif cmd == "refresh":
        refresh_command(state)
    elif cmd == "tail":
        print("Tail command not yet implemented. Coming in Phase 4.")
    elif cmd == "levels":
        print("Levels command not yet implemented. Coming in Phase 5.")
    elif cmd == "stop":
        print("Not currently tailing.")
    elif cmd == "enable-logging":
        print("Enable-logging command not yet implemented. Coming in Phase 7.")
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands.")

    return True


def main() -> None:
    """Main entry point for pgtail."""
    print("pgtail - PostgreSQL log tailer")
    print()

    # Initialize state with detected instances
    state = AppState()
    state.instances = detect_all()

    # Show instance count on startup
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found. Use 'refresh' to scan again.")
    elif count == 1:
        print("Found 1 PostgreSQL instance. Type 'list' to see details.")
    else:
        print(f"Found {count} PostgreSQL instances. Type 'list' to see details.")

    print("Type 'help' for available commands, 'quit' to exit.")
    print()

    # Set up prompt session with history
    history_path = ensure_history_dir()
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
    )

    # REPL loop
    while True:
        try:
            line = session.prompt("pgtail> ")
            if not handle_command(state, line):
                break
        except KeyboardInterrupt:
            # Ctrl+C - ignore and show new prompt
            print()
            continue
        except EOFError:
            # Ctrl+D - exit
            print()
            break

    print("Goodbye!")
