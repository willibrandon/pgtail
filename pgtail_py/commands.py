"""Command definitions and completers for pgtail REPL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.instance import Instance

# Command definitions: name -> description
COMMANDS: dict[str, str] = {
    "list": "Show detected PostgreSQL instances",
    "tail": "Tail logs for an instance (by ID or path)",
    "levels": "Set log level filter (e.g., 'levels ERROR WARNING')",
    "filter": "Set regex filter (e.g., 'filter /pattern/')",
    "stop": "Stop current tail and return to prompt",
    "refresh": "Re-scan for PostgreSQL instances",
    "enable-logging": "Enable logging_collector for an instance",
    "clear": "Clear the screen",
    "help": "Show help message",
    "quit": "Exit pgtail",
    "exit": "Exit pgtail",
    "q": "Exit pgtail",
}


class PgtailCompleter(Completer):
    """Completer for pgtail REPL commands.

    Provides context-aware completion for:
    - Command names at the start of input
    - Instance IDs/paths for 'tail' and 'enable-logging' commands
    - Log level names for 'levels' command
    """

    def __init__(self, get_instances: callable | None = None) -> None:
        """Initialize the completer.

        Args:
            get_instances: Callback to get current list of instances.
        """
        self._get_instances = get_instances

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> list[Completion]:
        """Generate completions for the current input.

        Args:
            document: The current document being edited.
            complete_event: The completion event.

        Yields:
            Completion objects for matching completions.
        """
        text = document.text_before_cursor
        parts = text.split()

        # Empty or first word - complete command names
        if not parts or (len(parts) == 1 and not text.endswith(" ")):
            prefix = parts[0].lower() if parts else ""
            yield from self._complete_commands(prefix)
            return

        # Command followed by space - complete arguments
        cmd = parts[0].lower()
        arg_text = parts[-1] if len(parts) > 1 and not text.endswith(" ") else ""

        if cmd == "tail" or cmd == "enable-logging":
            yield from self._complete_instances(arg_text)
        elif cmd == "levels":
            yield from self._complete_levels(arg_text, parts[1:] if text.endswith(" ") else parts[1:-1])

    def _complete_commands(self, prefix: str) -> list[Completion]:
        """Complete command names.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for matching commands.
        """
        for name, description in COMMANDS.items():
            if name.startswith(prefix):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_instances(self, prefix: str) -> list[Completion]:
        """Complete instance IDs and paths.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for matching instances.
        """
        if self._get_instances is None:
            return

        instances: list[Instance] = self._get_instances()
        for inst in instances:
            # Complete by ID
            id_str = str(inst.id)
            if id_str.startswith(prefix):
                status = "running" if inst.running else "stopped"
                yield Completion(
                    id_str,
                    start_position=-len(prefix),
                    display_meta=f"v{inst.version} ({status})",
                )

            # Complete by path
            path_str = str(inst.data_dir)
            if prefix and path_str.startswith(prefix):
                yield Completion(
                    path_str,
                    start_position=-len(prefix),
                    display_meta=f"Instance {inst.id}",
                )

    def _complete_levels(self, prefix: str, already_selected: list[str]) -> list[Completion]:
        """Complete log level names.

        Args:
            prefix: The prefix to match.
            already_selected: Levels already selected (to avoid duplicates).

        Yields:
            Completions for matching log levels.
        """
        prefix_upper = prefix.upper()
        selected_upper = {s.upper() for s in already_selected}

        # Special case: ALL
        if "ALL".startswith(prefix_upper) and "ALL" not in selected_upper:
            yield Completion(
                "ALL",
                start_position=-len(prefix),
                display_meta="Show all log levels",
            )

        # Log levels
        for level in LogLevel:
            if level.name not in selected_upper and level.name.startswith(prefix_upper):
                yield Completion(
                    level.name,
                    start_position=-len(prefix),
                    display_meta=f"Severity {level.value}",
                )
