"""Contract: TailBuffer interface for Status Bar Tail Mode.

This module defines the interface for the ring buffer that stores
formatted log entries with scroll position management.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from prompt_toolkit.formatted_text import FormattedText

# Forward reference - actual LogEntry from pgtail_py.parser
from pgtail_py.parser import LogEntry


@dataclass
class FormattedLogEntry:
    """Pre-processed log entry ready for display.

    Attributes:
        entry: Original parsed log entry (None for command output/separators)
        formatted: Pre-styled FormattedText with colors
        matches_filter: Whether entry passes current filter criteria
    """

    entry: LogEntry | None
    formatted: FormattedText
    matches_filter: bool = True


class TailBufferProtocol(Protocol):
    """Protocol for ring buffer with scroll position management."""

    @property
    def max_size(self) -> int:
        """Maximum number of entries the buffer can hold."""
        ...

    @property
    def follow_mode(self) -> bool:
        """True if auto-scrolling to new entries."""
        ...

    @property
    def new_since_pause(self) -> int:
        """Count of entries added while paused."""
        ...

    @property
    def total_entries(self) -> int:
        """Total entries currently in buffer."""
        ...

    @property
    def filtered_count(self) -> int:
        """Count of entries that pass current filters."""
        ...

    def append(self, entry: FormattedLogEntry) -> None:
        """Add entry to buffer, evict oldest if at capacity.

        If in PAUSED mode, increments new_since_pause.
        Triggers scroll position adjustment if oldest entry evicted.
        """
        ...

    def get_visible_lines(self, height: int) -> FormattedText:
        """Return visible entries based on scroll position and filters.

        Args:
            height: Number of lines that fit in the display window

        Returns:
            FormattedText containing visible entries joined by newlines
        """
        ...

    def scroll_up(self, lines: int) -> None:
        """Scroll up by specified lines, entering PAUSED mode.

        Args:
            lines: Number of lines to scroll (clamped to valid range)
        """
        ...

    def scroll_down(self, lines: int) -> None:
        """Scroll down by specified lines.

        If scrolling past bottom, resumes FOLLOW mode.

        Args:
            lines: Number of lines to scroll (clamped to valid range)
        """
        ...

    def scroll_to_top(self) -> None:
        """Scroll to beginning of buffer, entering PAUSED mode."""
        ...

    def resume_follow(self) -> None:
        """Jump to end of buffer, entering FOLLOW mode.

        Resets scroll_offset to 0 and new_since_pause to 0.
        """
        ...

    def refilter(self) -> None:
        """Re-evaluate all entries against current filter predicates.

        Updates matches_filter on all entries.
        Adjusts scroll position if filtered content changes.
        """
        ...

    def update_filters(
        self, filter_funcs: list[Callable[[LogEntry], bool]]
    ) -> None:
        """Set new filter predicates and trigger refilter.

        Args:
            filter_funcs: List of filter functions (all must return True to show)
        """
        ...

    def insert_command_output(self, output: FormattedText) -> None:
        """Insert command output inline with visual separators.

        Adds separator, output, separator as three entries.
        These entries always match filter (shown regardless of filters).
        """
        ...

    def clear(self) -> None:
        """Clear all entries from buffer and reset scroll state."""
        ...
