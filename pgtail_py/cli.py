"""REPL loop and command handlers for pgtail."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pgtail_py.config import get_history_path
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


def main() -> None:
    """Main entry point for pgtail."""
    print("pgtail - PostgreSQL log tailer")
    print("Type 'help' for available commands, 'quit' to exit.")
