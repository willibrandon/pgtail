"""Contract: TailStatus interface for Status Bar Tail Mode.

This module defines the interface for the status bar state container
that tracks counts, filters, and mode for display.
"""

from __future__ import annotations

from typing import Protocol

from prompt_toolkit.formatted_text import FormattedText

# Forward references
from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry


class TailStatusProtocol(Protocol):
    """Protocol for status bar state management."""

    @property
    def error_count(self) -> int:
        """Total ERROR entries seen since tail started."""
        ...

    @property
    def warning_count(self) -> int:
        """Total WARNING entries seen since tail started."""
        ...

    @property
    def total_lines(self) -> int:
        """Current number of entries in buffer."""
        ...

    @property
    def follow_mode(self) -> bool:
        """True if following new entries, False if paused."""
        ...

    @property
    def new_since_pause(self) -> int:
        """Entries added while in paused mode."""
        ...

    @property
    def active_levels(self) -> set[LogLevel]:
        """Currently filtered log levels."""
        ...

    @property
    def regex_pattern(self) -> str | None:
        """Active regex filter pattern, or None if no regex filter."""
        ...

    @property
    def time_filter_display(self) -> str | None:
        """Human-readable time filter string (e.g., 'since:5m')."""
        ...

    @property
    def slow_threshold(self) -> int | None:
        """Slow query threshold in milliseconds, or None if not set."""
        ...

    @property
    def pg_version(self) -> str:
        """PostgreSQL major version (e.g., '17')."""
        ...

    @property
    def pg_port(self) -> int:
        """PostgreSQL port number."""
        ...

    def update_from_entry(self, entry: LogEntry) -> None:
        """Update counts based on a new log entry.

        Increments error_count or warning_count based on entry level.
        Called for all entries, not just filtered ones.

        Args:
            entry: Parsed log entry to count
        """
        ...

    def set_total_lines(self, count: int) -> None:
        """Update total lines count from buffer size."""
        ...

    def set_follow_mode(self, following: bool, new_count: int = 0) -> None:
        """Update follow/paused mode state.

        Args:
            following: True for FOLLOW mode, False for PAUSED
            new_count: Number of new entries since pause (only used when paused)
        """
        ...

    def set_level_filter(self, levels: set[LogLevel]) -> None:
        """Update active level filter for display."""
        ...

    def set_regex_filter(self, pattern: str | None) -> None:
        """Update active regex filter pattern for display."""
        ...

    def set_time_filter(self, display: str | None) -> None:
        """Update time filter display string."""
        ...

    def set_slow_threshold(self, threshold: int | None) -> None:
        """Update slow query threshold for display."""
        ...

    def set_instance_info(self, version: str, port: int) -> None:
        """Set PostgreSQL instance information."""
        ...

    def format(self) -> FormattedText:
        """Render status bar as FormattedText.

        Format: MODE | E:N W:N | N lines | [filters...] | PGver:port

        Returns:
            FormattedText with styled status bar content
        """
        ...

    def reset_counts(self) -> None:
        """Reset error and warning counts to zero."""
        ...
