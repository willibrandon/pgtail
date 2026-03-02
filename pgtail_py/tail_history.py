"""Command history with three-state cursor navigation for tail mode.

Provides TailCommandHistory for recording, navigating, and searching
previously entered tail mode commands. Navigation uses a three-state
cursor model: at-rest, at-history-entry, and past-newest (transitional).

File persistence: entries stored as one command per line in a UTF-8 text
file at a platform-specific location. Append-only writes with periodic
compaction. All I/O errors handled silently (FR-008).
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "pgtail"


def get_tail_history_path() -> Path:
    """Return platform-specific path for tail mode history file.

    Returns:
        macOS: ~/Library/Application Support/pgtail/tail_history
        Linux: ~/.local/share/pgtail/tail_history (XDG_DATA_HOME)
        Windows: %APPDATA%/pgtail/tail_history
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux and other Unix-like systems
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

    return base / APP_NAME / "tail_history"


class TailCommandHistory:
    """Ordered command history with three-state cursor navigation and file persistence.

    The cursor model has three derived states (no separate state field stored):

    - **at-rest**: cursor == len(entries) and saved_input is None.
      Default state. Up triggers navigation. Down is a no-op.
    - **at-history-entry**: 0 <= cursor < len(entries) and saved_input
      is preserved. Showing a history entry. Up/Down navigate.
    - **past-newest**: Transitional. cursor reaches len(entries) via Down,
      saved_input is restored and cleared, immediately becoming at-rest.

    Args:
        max_entries: Maximum entries in memory. Oldest dropped when exceeded.
        history_path: File path for persistence. None = in-memory only.
    """

    def __init__(
        self,
        max_entries: int = 500,
        history_path: Path | None = None,
    ) -> None:
        self._entries: list[str] = []
        self._cursor: int = 0  # == len(entries) when at-rest
        self._saved_input: str | None = None
        self._max_entries: int = max_entries
        self._history_path: Path | None = history_path
        self._max_line_bytes: int = 4096
        self._compact_threshold: int = max_entries * 2

    # ─── Properties ──────────────────────────────────────────────────────

    @property
    def at_rest(self) -> bool:
        """True when not navigating (cursor at end, no saved input)."""
        return self._cursor == len(self._entries) and self._saved_input is None

    @property
    def entries(self) -> list[str]:
        """Read-only copy of history entries (oldest first)."""
        return list(self._entries)

    def __len__(self) -> int:
        """Number of entries in history."""
        return len(self._entries)

    # ─── Recording ───────────────────────────────────────────────────────

    def add(self, command: str) -> bool:
        """Record a command.

        Rejects empty and whitespace-only strings. Deduplicates consecutive
        identical entries. Trims to max_entries by dropping oldest. Resets
        navigation to at-rest.

        Does NOT persist to file (call save() separately).

        Returns:
            True if the command was added, False if rejected (empty or
            consecutive duplicate).
        """
        if not command or not command.strip():
            return False

        # Consecutive dedup: skip if identical to most recent entry
        if self._entries and self._entries[-1] == command:
            self.reset_navigation()
            return False

        self._entries.append(command)

        # Trim oldest when exceeding max_entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

        # Reset navigation to at-rest
        self.reset_navigation()
        return True

    # ─── Navigation ──────────────────────────────────────────────────────

    def navigate_back(self, current_input: str) -> str | None:
        """Move cursor to an older entry.

        On first call from at-rest: saves current_input, cursor = len-1.
        On subsequent calls: cursor = max(0, cursor-1).
        At oldest entry (cursor 0): returns entries[0] unchanged (no-op clamp).

        Returns:
            The history entry at the new cursor position, or None if
            history is empty.
        """
        if not self._entries:
            return None

        if self.at_rest:
            # First backward navigation: save current input
            self._saved_input = current_input
            self._cursor = len(self._entries) - 1
        else:
            # Already navigating: move to older, clamped at 0
            self._cursor = max(0, self._cursor - 1)

        return self._entries[self._cursor]

    def navigate_forward(self) -> tuple[str | None, bool]:
        """Move cursor to a newer entry or restore saved input.

        Returns:
            Tuple of (text, is_restored):
            - (entry, False) when moving to a newer history entry
            - (saved_input, True) when moving past newest (restoring saved input)
            - (None, False) when already at-rest (no-op)
        """
        if self.at_rest:
            return (None, False)

        self._cursor += 1

        if self._cursor < len(self._entries):
            # Still within history entries
            return (self._entries[self._cursor], False)

        # Past newest: restore saved input and transition to at-rest
        saved = self._saved_input
        self._saved_input = None
        # cursor is now == len(entries) and saved_input is None → at_rest
        return (saved, True)

    def reset_navigation(self) -> None:
        """Reset to at-rest state.

        Clears cursor position and saved input. Does NOT change the
        input widget's value.
        """
        self._cursor = len(self._entries)
        self._saved_input = None

    # ─── Search ──────────────────────────────────────────────────────────

    def search_prefix(self, prefix: str) -> str | None:
        """Find the most recent entry matching prefix (case-sensitive).

        Searches backward from newest. Only returns entries where the
        entry is strictly longer than prefix (i.e., has a non-empty suffix
        beyond the prefix).

        Args:
            prefix: The prefix to match against entry starts.

        Returns:
            The full entry string, or None if no match.
        """
        for entry in reversed(self._entries):
            if entry.startswith(prefix) and entry != prefix:
                return entry
        return None

    # ─── File persistence ────────────────────────────────────────────────

    def load(self) -> None:
        """Load entries from history_path.

        Silently handles all errors (FR-008). Skips lines exceeding
        ``_max_line_bytes`` (FR-009). Uses ``errors="replace"`` for
        non-UTF-8 bytes (FR-009). Retains only last ``max_entries``
        entries (FR-007). Resets navigation state after loading.
        """
        if self._history_path is None:
            return

        try:
            if not self._history_path.exists():
                return
            entries: list[str] = []
            with open(self._history_path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    stripped = line.rstrip("\n")
                    if not stripped:
                        continue
                    if len(stripped.encode("utf-8")) > self._max_line_bytes:
                        continue
                    entries.append(stripped)
            # Retain only last max_entries
            if len(entries) > self._max_entries:
                entries = entries[-self._max_entries :]
            self._entries = entries
            self.reset_navigation()
        except Exception:
            logger.debug("Failed to load history from %s", self._history_path, exc_info=True)

    def save(self, command: str) -> None:
        """Append a single command to history_path.

        Creates parent directories if needed. Silently handles all
        errors (FR-008).
        """
        if self._history_path is None:
            return

        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_path, "a", encoding="utf-8") as f:
                f.write(command + "\n")
        except Exception:
            logger.debug("Failed to save history to %s", self._history_path, exc_info=True)

    def compact(self) -> None:
        """Rewrite history_path with last ``max_entries`` entries if file exceeds
        ``compact_threshold`` lines.

        Not atomic with respect to concurrent appenders (FR-006).
        Silently handles all errors (FR-008).
        """
        if self._history_path is None:
            return

        try:
            if not self._history_path.exists():
                return
            with open(self._history_path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            if len(lines) <= self._compact_threshold:
                return
            # Keep last max_entries non-empty lines
            entries = [line.rstrip("\n") for line in lines if line.strip()]
            entries = entries[-self._max_entries :]
            with open(self._history_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(entry + "\n")
        except Exception:
            logger.debug("Failed to compact history at %s", self._history_path, exc_info=True)
