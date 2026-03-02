# API Contracts: Tail Mode Command History & Autocomplete

**Feature Branch**: `024-tail-history-completion`
**Date**: 2026-03-01

These contracts define the public interfaces for the three new modules. Implementation must conform to these signatures and behaviors.

## 1. TailCommandHistory (`tail_history.py`)

```python
from pathlib import Path

class TailCommandHistory:
    """Ordered command history with three-state cursor navigation and file persistence."""

    def __init__(
        self,
        max_entries: int = 500,
        history_path: Path | None = None,
    ) -> None:
        """Initialize history.

        Args:
            max_entries: Maximum entries in memory. Oldest dropped when exceeded.
            history_path: File path for persistence. None = in-memory only.
        """

    @property
    def at_rest(self) -> bool:
        """True when not navigating (cursor at end, no saved input)."""

    @property
    def entries(self) -> list[str]:
        """Read-only view of history entries (oldest first)."""

    def __len__(self) -> int:
        """Number of entries in history."""

    def add(self, command: str) -> None:
        """Record a command. Rejects empty/whitespace. Deduplicates consecutive repeats.
        Trims to max_entries. Resets navigation to at-rest.

        Does NOT persist to file (call save() separately).
        """

    def navigate_back(self, current_input: str) -> str | None:
        """Move cursor to an older entry.

        On first call from at-rest: saves current_input, cursor = len-1.
        On subsequent calls: cursor = max(0, cursor-1).
        At oldest entry (cursor 0): no-op, returns current entry.

        Returns:
            The history entry at the new cursor position, or None if history is empty.
        """

    def navigate_forward(self) -> tuple[str | None, bool]:
        """Move cursor to a newer entry or restore saved input.

        Returns:
            Tuple of (text, is_restored):
            - (entry, False) when moving to a newer history entry
            - (saved_input, True) when moving past newest (restoring saved input)
            - (None, False) when already at-rest (no-op)
        """

    def reset_navigation(self) -> None:
        """Reset to at-rest. Clears cursor position and saved input.
        Does NOT change the input widget's value.
        """

    def search_prefix(self, prefix: str) -> str | None:
        """Find the most recent entry matching prefix (case-sensitive, FR-018).

        Returns:
            The full entry string, or None if no match.
            Only returns entries where entry != prefix (non-empty suffix).
        """

    def load(self) -> None:
        """Load entries from history_path. Silently handles all errors (FR-008).
        Skips lines > 4096 bytes (FR-009). Skips non-UTF-8 content (FR-009).
        Retains only last max_entries entries (FR-007).
        """

    def save(self, command: str) -> None:
        """Append a single command to history_path. Silently handles errors (FR-008).
        Creates parent directories if needed.
        """

    def compact(self) -> None:
        """Rewrite history_path with last max_entries entries if file exceeds
        compact_threshold (2× max_entries). Silently handles errors (FR-008).
        Not atomic with respect to concurrent appenders (FR-006).
        """


def get_tail_history_path() -> Path:
    """Return platform-specific path for tail mode history file.

    Returns:
        macOS: ~/Library/Application Support/pgtail/tail_history
        Linux: ~/.local/share/pgtail/tail_history (XDG_DATA_HOME)
        Windows: %APPDATA%/pgtail/tail_history
    """
```

## 2. TailCommandSuggester (`tail_suggester.py`)

```python
from textual.suggester import Suggester
from pgtail_py.tail_history import TailCommandHistory

class TailCommandSuggester(Suggester):
    """Context-aware ghost text suggester combining structural and history completions.

    Extends Textual's Suggester with use_cache=False (FR-020) and case_sensitive=True
    (mixed case handling per FR-018).
    """

    def __init__(
        self,
        history: TailCommandHistory,
        completion_data: dict[str, CompletionSpec],
        dynamic_sources: dict[str, Callable[[], list[str]]],
    ) -> None:
        """Initialize suggester.

        Args:
            history: Command history for prefix search fallback (FR-016).
            completion_data: Per-command completion specs.
            dynamic_sources: Named callables returning dynamic value lists (FR-015).
        """

    async def get_suggestion(self, value: str) -> str | None:
        """Return full-line suggestion for the given input value, or None.

        Pipeline:
        1. Parse input into command, complete tokens, partial word
        2. Resolve structural completion from completion_data
        3. Fall back to history.search_prefix() if structural yields nothing
        4. Return full input line with suggestion appended (FR-017)

        Args:
            value: The current input value (raw, not casefolded).

        Returns:
            Full suggested input line, or None if no suggestion.
        """

    def _parse_input(self, value: str) -> tuple[str | None, list[str], str]:
        """Parse input into (command, completed_args, partial_word).

        Uses str.split() semantics (FR-021). Handles trailing whitespace detection.
        Handles --flag=value token splitting (FR-021).

        Returns:
            - command: first completed token (casefolded), or None if still typing command
            - completed_args: list of completed argument tokens (after command)
            - partial: the partial word being typed (may be empty string)
        """

    def _resolve_structural(
        self,
        command: str,
        completed_args: list[str],
        partial: str,
    ) -> str | None:
        """Resolve structural completion for command arguments.

        Applies composition rules (flag vs positional vs subcommand resolution).
        Applies flag scanning algorithm (FR-014).

        Returns:
            Suggested value (full value, not just suffix), or None.
        """

    def _match_values(
        self,
        values: list[str],
        partial: str,
        case_sensitive: bool,
    ) -> str | None:
        """Find first value matching partial prefix.

        Args:
            values: Sorted list of candidate values.
            partial: Prefix to match against.
            case_sensitive: Whether to use case-sensitive matching.

        Returns:
            First matching value (original casing), or None.
        """
```

## 3. CompletionSpec (`tail_completion_data.py`)

```python
from dataclasses import dataclass, field
from typing import Callable

# Sentinel for free-form positional slots
FREE_FORM: None = None

@dataclass(frozen=True)
class CompletionSpec:
    """Completion specification for a command or argument position."""

    static_values: list[str] | None = None
    dynamic_source: str | None = None          # Key into TailCommandSuggester's dynamic_sources dict
    # Resolved at suggestion time: suggester._dynamic_sources[key]() → list[str]
    subcommands: dict[str, CompletionSpec] | None = None
    flags: dict[str, CompletionSpec | None] | None = None  # None = boolean
    positionals: list[CompletionSpec | None] | None = None  # None = free-form
    no_args: bool = False

# The canonical completion data dictionary
TAIL_COMPLETION_DATA: dict[str, CompletionSpec]

# Static value constants (for testing and reference)
LEVEL_VALUES: list[str]          # ["debug", "error", "fatal", ...]
TIME_PRESETS: list[str]          # ["5m", "10m", "15m", ...]
THRESHOLD_PRESETS: list[str]     # ["50", "100", "200", ...]
FORMAT_VALUES: list[str]         # ["text", "json", "csv"]
BUILTIN_THEME_NAMES: list[str]  # ["dark", "light", ...]
```

## 4. TailInput Modifications (`tail_input.py`)

```python
from textual.suggester import Suggester
from pgtail_py.tail_history import TailCommandHistory

class TailInput(Input):
    """Extended with history navigation and ghost text suggestions."""

    # New bindings added to existing BINDINGS list
    BINDINGS = [
        # ... existing bindings ...
        Binding("up", "history_back", "History back", show=False),
        Binding("down", "history_forward", "History forward", show=False),
    ]

    def __init__(
        self,
        *,
        history: TailCommandHistory | None = None,
        suggester: Suggester | None = None,
        placeholder: str = ...,
        name: str | None = None,
        id: str | None = ...,
        classes: str | None = None,
    ) -> None:
        """Extended constructor (FR-023).

        Args:
            history: Optional command history for Up/Down navigation.
            suggester: Optional ghost text suggester.
            ... existing params ...
        """

    def watch_value(self, value: str) -> None:
        """Reset history navigation on non-guarded value changes (FR-004, FR-025).

        Checks _navigating guard: if True (programmatic change from navigation),
        skips reset. If False (user typing, deletion, or ghost acceptance), resets.
        """

    def action_history_back(self) -> None:
        """Navigate to older history entry (FR-002).

        Sets _navigating guard, updates value, clears guard.
        """

    def action_history_forward(self) -> None:
        """Navigate to newer history entry or restore saved input (FR-003).

        Sets _navigating guard, updates value, clears guard.
        """
```

## 5. TailApp Integration (`tail_textual.py`)

```python
# New imports
from pgtail_py.tail_history import TailCommandHistory, get_tail_history_path
from pgtail_py.tail_suggester import TailCommandSuggester

class TailApp(App[None]):

    def compose(self) -> ComposeResult:
        # ... existing widgets ...
        yield TailInput(
            history=self._history,       # NEW
            suggester=self._suggester,   # NEW
        )
        # ...

    def on_mount(self) -> None:
        # ... existing setup ...
        # NEW: Load history and compact if needed
        self._history.load()
        self._history.compact()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if command:
            self._history.add(command)     # NEW: Record in memory
            self._history.save(command)    # NEW: Persist to file
            self._handle_command(command)
        # ...
```
