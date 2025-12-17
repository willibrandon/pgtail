"""Command definitions and completers for pgtail REPL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from pgtail_py.config import SETTING_KEYS
from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.instance import Instance

# Command definitions: name -> description
COMMANDS: dict[str, str] = {
    "list": "Show detected PostgreSQL instances",
    "tail": "Tail logs for an instance (by ID or path)",
    "levels": "Set log level filter (e.g., 'levels ERROR WARNING')",
    "filter": "Set regex filter (e.g., 'filter /pattern/')",
    "highlight": "Highlight text matching regex (e.g., 'highlight /pattern/')",
    "since": "Filter logs since time (e.g., 'since 5m', 'since 14:30')",
    "until": "Filter logs until time (e.g., 'until 15:00', 'until 30m')",
    "between": "Filter logs in time range (e.g., 'between 14:30 15:00')",
    "display": "Control display mode (compact, full, fields)",
    "output": "Control output format (json, text)",
    "slow": "Configure slow query highlighting (e.g., 'slow 100 500 1000')",
    "stats": "Show query duration statistics",
    "set": "Set a config value (e.g., 'set slow.warn 50')",
    "unset": "Remove a config setting (e.g., 'unset slow.warn')",
    "config": "Show current configuration (subcommands: path, edit, reset)",
    "errors": "Show error statistics (--trend, --live, --code, --since, clear)",
    "export": "Export filtered logs to file (e.g., 'export errors.log')",
    "pipe": "Pipe filtered logs to command (e.g., 'pipe wc -l')",
    "stop": "Stop current tail and return to prompt",
    "refresh": "Re-scan for PostgreSQL instances",
    "enable-logging": "Enable logging_collector for an instance",
    "clear": "Clear the screen",
    "help": "Show help message",
    "quit": "Exit pgtail",
    "exit": "Exit pgtail",
    "q": "Exit pgtail",
}

# Field names for display command autocomplete
DISPLAY_FIELDS: list[str] = [
    "timestamp",
    "pid",
    "level",
    "message",
    "sql_state",
    "user",
    "database",
    "application",
    "query",
    "detail",
    "hint",
    "context",
    "location",
    "backend_type",
    "session_id",
    "command_tag",
]

# Field names for filter command autocomplete (canonical + aliases)
FILTER_FIELDS: list[str] = [
    "app",
    "application",
    "db",
    "database",
    "user",
    "pid",
    "backend",
]


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

        if cmd == "tail":
            yield from self._complete_tail(arg_text, parts)
        elif cmd == "enable-logging":
            yield from self._complete_instances(arg_text)
        elif cmd == "levels":
            yield from self._complete_levels(
                arg_text, parts[1:] if text.endswith(" ") else parts[1:-1]
            )
        elif cmd == "filter":
            yield from self._complete_filter(arg_text)
        elif cmd == "highlight":
            yield from self._complete_highlight(arg_text)
        elif cmd == "slow":
            yield from self._complete_slow(arg_text)
        elif cmd == "set":
            yield from self._complete_set(arg_text, len(parts))
        elif cmd == "unset":
            yield from self._complete_unset(arg_text, len(parts))
        elif cmd == "config":
            yield from self._complete_config(arg_text)
        elif cmd == "export":
            yield from self._complete_export(arg_text)
        elif cmd == "pipe":
            yield from self._complete_pipe(arg_text)
        elif cmd == "since":
            yield from self._complete_since(arg_text)
        elif cmd == "between":
            yield from self._complete_between(arg_text, len(parts))
        elif cmd == "until":
            yield from self._complete_until(arg_text)
        elif cmd == "display":
            yield from self._complete_display(arg_text, parts)
        elif cmd == "output":
            yield from self._complete_output(arg_text)
        elif cmd == "errors":
            yield from self._complete_errors(arg_text)

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

    def _complete_tail(self, prefix: str, parts: list[str]) -> list[Completion]:
        """Complete tail command arguments.

        Args:
            prefix: The prefix to match.
            parts: All command parts so far.

        Yields:
            Completions for tail arguments (instances and --since flag).
        """
        # Check if --since already used
        has_since = "--since" in parts

        # If previous arg was --since, complete with time values
        if len(parts) >= 2 and parts[-2] == "--since":
            yield from self._complete_since(prefix)
            return

        # Complete --since option if not already used
        if not has_since and prefix.startswith("-") and "--since".startswith(prefix):
            yield Completion(
                "--since",
                start_position=-len(prefix),
                display_meta="Filter from time (e.g., 5m, 14:30)",
            )

        # Complete instances
        yield from self._complete_instances(prefix)

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

    def _complete_filter(self, prefix: str) -> list[Completion]:
        """Complete filter subcommands and field names.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for filter subcommands and field filters.
        """
        prefix_lower = prefix.lower()

        if "clear".startswith(prefix_lower):
            yield Completion(
                "clear",
                start_position=-len(prefix),
                display_meta="Clear all filters",
            )

        # Complete field names for field=value syntax
        # Check if user is typing a field name (before the =)
        if "=" not in prefix:
            for field in FILTER_FIELDS:
                if field.startswith(prefix_lower):
                    yield Completion(
                        f"{field}=",
                        start_position=-len(prefix),
                        display_meta=f"Filter by {field}",
                    )

    def _complete_highlight(self, prefix: str) -> list[Completion]:
        """Complete highlight subcommands.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for highlight subcommands.
        """
        if "clear".startswith(prefix.lower()):
            yield Completion(
                "clear",
                start_position=-len(prefix),
                display_meta="Clear all highlights",
            )

    def _complete_slow(self, prefix: str) -> list[Completion]:
        """Complete slow query subcommands.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for slow query subcommands.
        """
        if "off".startswith(prefix.lower()):
            yield Completion(
                "off",
                start_position=-len(prefix),
                display_meta="Disable slow query highlighting",
            )

    def _complete_set(self, prefix: str, num_parts: int) -> list[Completion]:
        """Complete setting keys for 'set' command.

        Args:
            prefix: The prefix to match.
            num_parts: Number of parts in the command so far.

        Yields:
            Completions for matching setting keys.
        """
        # Only complete first argument (the key)
        if num_parts > 2:
            return

        prefix_lower = prefix.lower()
        for key in SETTING_KEYS:
            if key.startswith(prefix_lower):
                # Extract section and description from key
                section = key.split(".")[0]
                yield Completion(
                    key,
                    start_position=-len(prefix),
                    display_meta=f"{section} setting",
                )

    def _complete_unset(self, prefix: str, num_parts: int) -> list[Completion]:
        """Complete setting keys for 'unset' command.

        Args:
            prefix: The prefix to match.
            num_parts: Number of parts in the command so far.

        Yields:
            Completions for matching setting keys.
        """
        # Only complete first argument (the key)
        if num_parts > 2:
            return

        prefix_lower = prefix.lower()
        for key in SETTING_KEYS:
            if key.startswith(prefix_lower):
                # Extract section and description from key
                section = key.split(".")[0]
                yield Completion(
                    key,
                    start_position=-len(prefix),
                    display_meta=f"reset {section} setting to default",
                )

    def _complete_config(self, prefix: str) -> list[Completion]:
        """Complete config subcommands.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for config subcommands.
        """
        subcommands = {
            "path": "Show config file location",
            "edit": "Open config in $EDITOR",
            "reset": "Reset config to defaults (with backup)",
        }
        prefix_lower = prefix.lower()
        for name, description in subcommands.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_export(self, prefix: str) -> list[Completion]:
        """Complete export command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for export options.
        """
        options = {
            "--append": "Append to existing file",
            "--follow": "Continuous export (like tail -f | tee)",
            "--format": "Output format (text, json, csv)",
            "--since": "Only entries after time (1h, 30m, 2d)",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

        # Complete format values after --format
        if prefix_lower in ("text", "json", "csv") or any(
            fmt.startswith(prefix_lower) for fmt in ("text", "json", "csv")
        ):
            formats = {
                "text": "Raw log lines",
                "json": "JSON Lines format",
                "csv": "CSV with headers",
            }
            for name, description in formats.items():
                if name.startswith(prefix_lower):
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                        display_meta=description,
                    )

    def _complete_pipe(self, prefix: str) -> list[Completion]:
        """Complete pipe command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for pipe options.
        """
        options = {
            "--format": "Output format (text, json, csv)",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

        # Complete format values after --format
        if prefix_lower in ("text", "json", "csv") or any(
            fmt.startswith(prefix_lower) for fmt in ("text", "json", "csv")
        ):
            formats = {
                "text": "Raw log lines",
                "json": "JSON Lines format",
                "csv": "CSV with headers",
            }
            for name, description in formats.items():
                if name.startswith(prefix_lower):
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                        display_meta=description,
                    )

    def _complete_since(self, prefix: str) -> list[Completion]:
        """Complete since command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for since options and time examples.
        """
        options = {
            "clear": "Remove time filter",
            "5m": "Last 5 minutes",
            "30m": "Last 30 minutes",
            "1h": "Last hour",
            "2h": "Last 2 hours",
            "1d": "Last day",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_between(self, prefix: str, num_parts: int) -> list[Completion]:
        """Complete between command options.

        Args:
            prefix: The prefix to match.
            num_parts: Number of parts in the command so far.

        Yields:
            Completions for between time examples.
        """
        # First arg: start time examples
        if num_parts <= 2:
            options = {
                "5m": "5 minutes ago (start)",
                "30m": "30 minutes ago (start)",
                "1h": "1 hour ago (start)",
                "14:00": "2 PM today (start)",
                "14:30": "2:30 PM today (start)",
            }
        # Second arg: end time examples
        else:
            options = {
                "15:00": "3 PM today (end)",
                "15:30": "3:30 PM today (end)",
                "16:00": "4 PM today (end)",
            }

        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_until(self, prefix: str) -> list[Completion]:
        """Complete until command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for until options and time examples.
        """
        options = {
            "clear": "Remove time filter",
            "15:00": "3 PM today",
            "15:30": "3:30 PM today",
            "16:00": "4 PM today",
            "17:00": "5 PM today",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_output(self, prefix: str) -> list[Completion]:
        """Complete output command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for output format options.
        """
        options = {
            "json": "Output as JSON (one object per line)",
            "text": "Output as colored text (default)",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

    def _complete_display(self, prefix: str, parts: list[str]) -> list[Completion]:
        """Complete display command options.

        Args:
            prefix: The prefix to match.
            parts: All command parts so far.

        Yields:
            Completions for display subcommands and field names.
        """
        # First argument: display mode
        if len(parts) <= 2:
            modes = {
                "compact": "Single line per entry (default)",
                "full": "All available fields with labels",
                "fields": "Show only specified fields",
            }
            prefix_lower = prefix.lower()
            for name, description in modes.items():
                if name.startswith(prefix_lower):
                    yield Completion(
                        name,
                        start_position=-len(prefix),
                        display_meta=description,
                    )
            return

        # After "fields": complete field names
        if len(parts) >= 2 and parts[1].lower() == "fields":
            # Parse already-selected fields from comma-separated arg
            if len(parts) >= 3:
                selected = {f.strip().lower() for f in parts[2].split(",") if f.strip()}
            else:
                selected = set()

            prefix_lower = prefix.lower()
            # Handle comma continuation
            if "," in prefix:
                # Complete after the last comma
                base, partial = prefix.rsplit(",", 1)
                partial = partial.strip().lower()
                for field in DISPLAY_FIELDS:
                    if field.lower().startswith(partial) and field.lower() not in selected:
                        yield Completion(
                            f"{base},{field}",
                            start_position=-len(prefix),
                            display_meta=f"Add {field} field",
                        )
            else:
                for field in DISPLAY_FIELDS:
                    if field.lower().startswith(prefix_lower) and field.lower() not in selected:
                        yield Completion(
                            field,
                            start_position=-len(prefix),
                            display_meta=f"Show {field} field",
                        )

    def _complete_errors(self, prefix: str) -> list[Completion]:
        """Complete errors command options.

        Args:
            prefix: The prefix to match.

        Yields:
            Completions for errors subcommands and options.
        """
        options = {
            "clear": "Reset all error statistics",
            "--trend": "Show error rate sparkline",
            "--live": "Live updating counter",
            "--code": "Filter by SQLSTATE code",
            "--since": "Filter by time window",
        }
        prefix_lower = prefix.lower()
        for name, description in options.items():
            if name.startswith(prefix_lower):
                yield Completion(
                    name,
                    start_position=-len(prefix),
                    display_meta=description,
                )

        # Complete common SQLSTATE codes after --code
        if prefix_lower and not prefix_lower.startswith("-"):
            sqlstate_codes = {
                "23505": "unique_violation",
                "23503": "foreign_key_violation",
                "42P01": "undefined_table",
                "42601": "syntax_error",
                "42703": "undefined_column",
                "57014": "query_canceled",
                "53300": "too_many_connections",
            }
            for code, name in sqlstate_codes.items():
                if code.startswith(prefix):
                    yield Completion(
                        code,
                        start_position=-len(prefix),
                        display_meta=name,
                    )
