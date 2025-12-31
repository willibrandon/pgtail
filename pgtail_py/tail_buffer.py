"""Ring buffer for tail mode log entries with scroll position management.

This module provides the TailBuffer class for storing formatted log entries
in a fixed-size deque, supporting scroll position tracking, follow/paused modes,
and filter-aware views for the status bar tail mode interface.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


def _empty_filter_list() -> list[Callable[..., bool]]:
    """Return empty filter list with proper type."""
    return []


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


# Separator style for command output
SEPARATOR_CHAR = "·"
SEPARATOR_WIDTH = 60


def create_separator() -> FormattedText:
    """Create a visual separator line for command output."""
    return FormattedText([("class:separator", SEPARATOR_CHAR * SEPARATOR_WIDTH)])


@dataclass
class TailBuffer:
    """Deque-based buffer storing formatted log entries with scroll position management.

    Provides FOLLOW and PAUSED modes for viewing live log streams with the ability
    to scroll back through history while new entries continue to arrive.

    Attributes:
        _entries: Fixed-size deque holding FormattedLogEntry objects
        _max_size: Maximum buffer capacity (default 10000)
        _scroll_offset: Lines from bottom (0 = at end, viewing latest)
        _follow_mode: True = auto-scroll to new entries, False = paused
        _new_since_pause: Count of entries added while in paused mode
        _filter_funcs: List of active filter predicates
    """

    _entries: deque[FormattedLogEntry] = field(default_factory=lambda: deque(maxlen=10000))
    _max_size: int = 10000
    _scroll_offset: int = 0
    _follow_mode: bool = True
    _new_since_pause: int = 0
    _filter_funcs: list[Callable[..., bool]] = field(default_factory=_empty_filter_list)

    def __post_init__(self) -> None:
        """Ensure deque has correct maxlen."""
        # Check maxlen since default_factory creates deque with fixed maxlen
        if self._entries.maxlen != self._max_size:
            self._entries = deque(maxlen=self._max_size)

    @property
    def max_size(self) -> int:
        """Maximum number of entries the buffer can hold."""
        return self._max_size

    @property
    def follow_mode(self) -> bool:
        """True if auto-scrolling to new entries."""
        return self._follow_mode

    @property
    def new_since_pause(self) -> int:
        """Count of entries added while paused."""
        return self._new_since_pause

    @property
    def total_entries(self) -> int:
        """Total entries currently in buffer."""
        return len(self._entries)

    @property
    def filtered_count(self) -> int:
        """Count of entries that pass current filters."""
        return sum(1 for e in self._entries if e.matches_filter)

    def get_filtered_error_warning_counts(self) -> tuple[int, int]:
        """Count errors and warnings among filtered entries.

        Returns:
            Tuple of (error_count, warning_count) for entries where matches_filter=True
        """
        from pgtail_py.filter import LogLevel

        error_count = 0
        warning_count = 0

        for e in self._entries:
            if e.matches_filter and e.entry is not None:
                if e.entry.level == LogLevel.ERROR:
                    error_count += 1
                elif e.entry.level == LogLevel.WARNING:
                    warning_count += 1
                elif e.entry.level in (LogLevel.FATAL, LogLevel.PANIC):
                    error_count += 1

        return error_count, warning_count

    def _get_filtered_entries(self) -> list[FormattedLogEntry]:
        """Get list of entries that pass current filters."""
        return [e for e in self._entries if e.matches_filter]

    @property
    def total_visual_lines(self) -> int:
        """Total visual lines of filtered entries (for scroll calculations)."""
        total = 0
        for e in self._entries:
            if e.matches_filter:
                total += self._count_visual_lines(e)
        return total

    def append(self, entry: FormattedLogEntry) -> None:
        """Add entry to buffer, evict oldest if at capacity.

        If in PAUSED mode, increments new_since_pause.
        Handles scroll position adjustment if oldest entry evicted while paused.

        Args:
            entry: FormattedLogEntry to add to the buffer
        """
        was_at_capacity = len(self._entries) == self._max_size

        # Handle eviction of oldest entry when at capacity
        if was_at_capacity:
            evicted = self._entries[0]
            evicted_passes_filter = evicted.matches_filter

            # Adjust scroll offset if evicted entry passed filter and we're paused
            if evicted_passes_filter and not self._follow_mode and self._scroll_offset > 0:
                evicted_lines = self._count_visual_lines(evicted)
                self._scroll_offset = max(0, self._scroll_offset - evicted_lines)

        # Apply filter to new entry
        if entry.entry is not None and self._filter_funcs:
            entry.matches_filter = all(f(entry.entry) for f in self._filter_funcs)
        # Command output (entry.entry is None) always matches

        self._entries.append(entry)

        # Track new entries while paused and adjust scroll to keep view stable
        if not self._follow_mode:
            self._new_since_pause += 1
            # If new entry passes filter, increment scroll offset by its visual line count
            if entry.matches_filter:
                self._scroll_offset += self._count_visual_lines(entry)

    def _count_visual_lines(self, entry: FormattedLogEntry) -> int:
        """Count the number of visual lines in a formatted entry.

        Args:
            entry: The formatted log entry

        Returns:
            Number of visual lines (1 + number of newlines in content)
        """
        line_count = 1
        for _, text in entry.formatted:
            line_count += text.count("\n")
        return line_count

    def get_visible_lines(self, height: int) -> FormattedText:
        """Return visible entries based on scroll position and filters.

        Content is bottom-aligned: newest content appears at the bottom.
        Works backwards from the end to collect exactly `height` visual lines.

        Args:
            height: Number of visual lines that fit in the display window

        Returns:
            FormattedText containing visible entries joined by newlines
        """
        # Get only filtered entries
        filtered = self._get_filtered_entries()

        if not filtered:
            # Return empty lines to fill the space
            if height > 0:
                return FormattedText([("", "\n" * (height - 1))])
            return FormattedText([("", "")])

        # Build list of entries with their visual line counts
        entries_with_lines: list[tuple[FormattedLogEntry, int]] = []
        for entry in filtered:
            entries_with_lines.append((entry, self._count_visual_lines(entry)))

        # Work backwards from the end, skipping scroll_offset lines,
        # then collecting up to height lines

        # Skip scroll_offset lines from the end
        lines_to_skip = self._scroll_offset
        lines_to_show = height

        # Collect entries from the end, working backwards
        visible_entries: list[FormattedLogEntry] = []
        accumulated_lines = 0

        for entry, line_count in reversed(entries_with_lines):
            if lines_to_skip > 0:
                # Skip this entry (or part of it) due to scroll offset
                if line_count <= lines_to_skip:
                    lines_to_skip -= line_count
                    continue
                else:
                    # Partial skip - we'd need to truncate, but for now include whole entry
                    lines_to_skip = 0

            # Add this entry if we have room
            if accumulated_lines + line_count <= lines_to_show:
                visible_entries.insert(0, entry)  # Insert at front to maintain order
                accumulated_lines += line_count
            else:
                # This entry would exceed our height - stop here
                # But include it if we have nothing yet (entry larger than height)
                if not visible_entries:
                    visible_entries.insert(0, entry)
                    accumulated_lines += line_count
                break

        if not visible_entries:
            if height > 0:
                return FormattedText([("", "\n" * (height - 1))])
            return FormattedText([("", "")])

        # Join formatted entries with newlines
        from prompt_toolkit.formatted_text import OneStyleAndTextTuple

        result: list[OneStyleAndTextTuple] = []

        # Add padding at top to push content to bottom (bottom-align)
        if accumulated_lines < height:
            padding_lines = height - accumulated_lines
            result.append(("", "\n" * padding_lines))

        for i, entry in enumerate(visible_entries):
            if i > 0:
                result.append(("", "\n"))
            result.extend(list(entry.formatted))

        return FormattedText(result)

    def scroll_up(self, lines: int) -> None:
        """Scroll up by specified lines (visual lines), entering PAUSED mode.

        Args:
            lines: Number of visual lines to scroll (clamped to valid range)
        """
        if lines <= 0:
            return

        # Enter paused mode
        if self._follow_mode:
            self._follow_mode = False
            self._new_since_pause = 0

        # Calculate max scroll offset (can't scroll past beginning)
        # Use visual lines for max offset calculation
        max_offset = max(0, self.total_visual_lines - 1)

        self._scroll_offset = min(self._scroll_offset + lines, max_offset)

    def scroll_down(self, lines: int) -> None:
        """Scroll down by specified lines.

        If scrolling past bottom, resumes FOLLOW mode.

        Args:
            lines: Number of lines to scroll (clamped to valid range)
        """
        if lines <= 0:
            return

        new_offset = self._scroll_offset - lines

        if new_offset <= 0:
            # Scrolled to bottom - resume follow mode
            self.resume_follow()
        else:
            self._scroll_offset = new_offset

    def scroll_to_top(self) -> None:
        """Scroll to beginning of buffer, entering PAUSED mode."""
        if self._follow_mode:
            self._follow_mode = False
            self._new_since_pause = 0

        # Set offset to show oldest entries (use visual lines)
        self._scroll_offset = max(0, self.total_visual_lines - 1)

    def resume_follow(self) -> None:
        """Jump to end of buffer, entering FOLLOW mode.

        Resets scroll_offset to 0 and new_since_pause to 0.
        """
        self._follow_mode = True
        self._scroll_offset = 0
        self._new_since_pause = 0

    def set_paused(self) -> None:
        """Explicitly enter PAUSED mode without scrolling."""
        self._follow_mode = False

    def refilter(self) -> None:
        """Re-evaluate all entries against current filter predicates.

        Updates matches_filter on all entries.
        Adjusts scroll position if filtered content changes.
        """
        old_filtered_count = self.filtered_count

        for entry in self._entries:
            if entry.entry is not None:
                # Real log entry - apply filters
                if self._filter_funcs:
                    entry.matches_filter = all(f(entry.entry) for f in self._filter_funcs)
                else:
                    entry.matches_filter = True
            # Command output always matches (entry.entry is None)

        new_filtered_count = self.filtered_count

        # Adjust scroll position if filtered count changed
        if not self._follow_mode and self._scroll_offset > 0:
            # Scale offset proportionally or clamp
            if old_filtered_count > 0:
                ratio = self._scroll_offset / old_filtered_count
                self._scroll_offset = min(
                    int(ratio * new_filtered_count), max(0, new_filtered_count - 1)
                )
            else:
                self._scroll_offset = 0

    def update_filters(self, filter_funcs: list[Callable[..., bool]]) -> None:
        """Set new filter predicates and trigger refilter.

        Args:
            filter_funcs: List of filter functions (all must return True to show)
        """
        self._filter_funcs = list(filter_funcs)
        self.refilter()

    def insert_command_output(self, output: FormattedText) -> None:
        """Insert command output inline with visual separators.

        Adds separator, output, separator as three entries.
        These entries always match filter (shown regardless of filters).

        Args:
            output: FormattedText containing the command output
        """
        # Opening separator
        self._entries.append(
            FormattedLogEntry(entry=None, formatted=create_separator(), matches_filter=True)
        )

        # Command output
        self._entries.append(FormattedLogEntry(entry=None, formatted=output, matches_filter=True))

        # Closing separator
        self._entries.append(
            FormattedLogEntry(entry=None, formatted=create_separator(), matches_filter=True)
        )

        # Track new entries while paused
        if not self._follow_mode:
            self._new_since_pause += 3

    def clear(self) -> None:
        """Clear all entries from buffer and reset scroll state."""
        self._entries.clear()
        self._scroll_offset = 0
        self._new_since_pause = 0
        # Keep follow_mode as-is
