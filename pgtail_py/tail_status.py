"""Status bar state management for tail mode.

This module provides the TailStatus class for tracking error/warning counts,
active filters, PostgreSQL instance information, and follow/paused mode state
for rendering the status bar in the split-screen tail interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prompt_toolkit.formatted_text import FormattedText
from rich.text import Text

from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry


@dataclass
class TailStatus:
    """State container for status bar display.

    Tracks counts, active filters, and mode for the status bar in tail mode.
    Provides format() method to render the status bar as FormattedText.

    Attributes:
        error_count: Total ERROR entries seen since tail started
        warning_count: Total WARNING entries seen since tail started
        total_lines: Current number of entries in buffer
        follow_mode: True if following new entries, False if paused
        new_since_pause: Entries added while in paused mode
        active_levels: Currently filtered log levels
        regex_pattern: Active regex filter pattern, or None
        time_filter_display: Human-readable time filter string
        slow_threshold: Slow query threshold in ms, or None
        pg_version: PostgreSQL major version
        pg_port: PostgreSQL port number
    """

    error_count: int = 0
    warning_count: int = 0
    total_lines: int = 0
    follow_mode: bool = True
    new_since_pause: int = 0
    active_levels: set[LogLevel] = field(default_factory=LogLevel.all_levels)
    regex_pattern: str | None = None
    time_filter_display: str | None = None
    slow_threshold: int | None = None
    pg_version: str = ""
    pg_port: int = 5432

    def update_from_entry(self, entry: LogEntry) -> None:
        """Update counts based on a new log entry.

        Increments error_count or warning_count based on entry level.
        Called for all entries, not just filtered ones.

        Args:
            entry: Parsed log entry to count
        """
        if entry.level == LogLevel.ERROR:
            self.error_count += 1
        elif entry.level == LogLevel.WARNING:
            self.warning_count += 1
        # FATAL and PANIC also count as errors
        elif entry.level in (LogLevel.FATAL, LogLevel.PANIC):
            self.error_count += 1

    def set_total_lines(self, count: int) -> None:
        """Update total lines count from buffer size.

        Args:
            count: Current number of entries in the buffer
        """
        self.total_lines = count

    def set_follow_mode(self, following: bool, new_count: int = 0) -> None:
        """Update follow/paused mode state.

        Args:
            following: True for FOLLOW mode, False for PAUSED
            new_count: Number of new entries since pause (only used when paused)
        """
        self.follow_mode = following
        self.new_since_pause = new_count if not following else 0

    def set_level_filter(self, levels: set[LogLevel]) -> None:
        """Update active level filter for display.

        Args:
            levels: Set of log levels currently being shown
        """
        self.active_levels = levels

    def set_regex_filter(self, pattern: str | None) -> None:
        """Update active regex filter pattern for display.

        Args:
            pattern: Regex pattern string, or None if no regex filter
        """
        self.regex_pattern = pattern

    def set_time_filter(self, display: str | None) -> None:
        """Update time filter display string.

        Args:
            display: Human-readable time filter (e.g., 'since:5m'), or None
        """
        self.time_filter_display = display

    def set_slow_threshold(self, threshold: int | None) -> None:
        """Update slow query threshold for display.

        Args:
            threshold: Threshold in milliseconds, or None if not set
        """
        self.slow_threshold = threshold

    def set_instance_info(self, version: str, port: int) -> None:
        """Set PostgreSQL instance information.

        Args:
            version: PostgreSQL major version (e.g., '17')
            port: PostgreSQL port number
        """
        self.pg_version = version
        self.pg_port = port

    def reset_counts(self) -> None:
        """Reset error and warning counts to zero."""
        self.error_count = 0
        self.warning_count = 0

    def format(self) -> FormattedText:
        """Render status bar as FormattedText.

        Format: MODE | E:N W:N | N lines | [filters...] | PGver:port

        Returns:
            FormattedText with styled status bar content
        """
        parts: list[tuple[str, str]] = []

        # Mode indicator
        if self.follow_mode:
            parts.append(("class:status.follow", "FOLLOW"))
        else:
            if self.new_since_pause > 0:
                parts.append(("class:status.paused", f"PAUSED +{self.new_since_pause} new"))
            else:
                parts.append(("class:status.paused", "PAUSED"))

        # Separator
        parts.append(("class:status.sep", " | "))

        # Error/Warning counts
        parts.append(("class:status.error", f"E:{self.error_count}"))
        parts.append(("class:status.sep", " "))
        parts.append(("class:status.warning", f"W:{self.warning_count}"))

        # Separator
        parts.append(("class:status.sep", " | "))

        # Total lines
        parts.append(("class:status", f"{self.total_lines:,} lines"))

        # Separator
        parts.append(("class:status.sep", " | "))

        # Active filters
        filter_parts: list[str] = []

        # Level filter
        if self.active_levels == LogLevel.all_levels():
            filter_parts.append("levels:ALL")
        else:
            level_names = ",".join(sorted(lvl.name for lvl in self.active_levels))
            filter_parts.append(f"levels:{level_names}")

        # Regex filter
        if self.regex_pattern:
            filter_parts.append(f"filter:/{self.regex_pattern}/")

        # Time filter
        if self.time_filter_display:
            filter_parts.append(self.time_filter_display)

        # Slow query threshold
        if self.slow_threshold is not None:
            filter_parts.append(f"slow:>{self.slow_threshold}ms")

        # Add filter parts with styling
        for i, fp in enumerate(filter_parts):
            if i > 0:
                parts.append(("class:status.sep", " "))
            parts.append(("class:status.filter", fp))

        # Separator
        parts.append(("class:status.sep", " | "))

        # PostgreSQL instance info
        if self.pg_version:
            parts.append(("class:status.instance", f"PG{self.pg_version}:{self.pg_port}"))
        else:
            parts.append(("class:status.instance", f":{self.pg_port}"))

        return FormattedText(parts)

    def format_plain(self) -> str:
        """Render status bar as plain text string.

        Format: MODE | E:N W:N | N lines | [filters...] | PGver:port

        This is used for Textual's Static widget which doesn't support
        prompt_toolkit FormattedText.

        Returns:
            Plain text status bar content.
        """
        parts: list[str] = []

        # Mode indicator
        if self.follow_mode:
            parts.append("FOLLOW")
        else:
            if self.new_since_pause > 0:
                parts.append(f"PAUSED +{self.new_since_pause} new")
            else:
                parts.append("PAUSED")

        # Separator
        parts.append("|")

        # Error/Warning counts
        parts.append(f"E:{self.error_count} W:{self.warning_count}")

        # Separator
        parts.append("|")

        # Total lines
        parts.append(f"{self.total_lines:,} lines")

        # Separator
        parts.append("|")

        # Active filters
        filter_parts: list[str] = []

        # Level filter
        if self.active_levels == LogLevel.all_levels():
            filter_parts.append("levels:ALL")
        else:
            level_names = ",".join(sorted(lvl.name for lvl in self.active_levels))
            filter_parts.append(f"levels:{level_names}")

        # Regex filter
        if self.regex_pattern:
            filter_parts.append(f"filter:/{self.regex_pattern}/")

        # Time filter
        if self.time_filter_display:
            filter_parts.append(self.time_filter_display)

        # Slow query threshold
        if self.slow_threshold is not None:
            filter_parts.append(f"slow:>{self.slow_threshold}ms")

        parts.append(" ".join(filter_parts))

        # Separator
        parts.append("|")

        # PostgreSQL instance info
        if self.pg_version:
            parts.append(f"PG{self.pg_version}:{self.pg_port}")
        else:
            parts.append(f":{self.pg_port}")

        return " ".join(parts)

    def format_rich(self) -> Text:
        """Render status bar as styled Rich Text (2 lines).

        Line 1: MODE | E:N W:N | N lines | [filters...] | PGver:port
        Line 2: Footer hints for key bindings

        The status bar background is set by CSS ($panel) which is typically
        a dark surface color. Text colors use bright variants for high
        contrast visibility.

        Returns:
            Rich Text object with styled 2-line status bar content.
        """
        text = Text()

        # === Line 1: Status info ===

        # Left margin for breathing room
        text.append(" ")

        # Mode indicator - bright green for FOLLOW, bright yellow for PAUSED
        if self.follow_mode:
            text.append("FOLLOW", style="bold bright_green")
        else:
            if self.new_since_pause > 0:
                text.append(f"PAUSED +{self.new_since_pause} new", style="bold bright_yellow")
            else:
                text.append("PAUSED", style="bold bright_yellow")

        # Separator - dim to not distract
        text.append(" | ", style="dim")

        # Error/Warning counts - bright red for errors, bright yellow for warnings
        text.append(f"E:{self.error_count}", style="bold bright_red")
        text.append(" ", style="dim")
        text.append(f"W:{self.warning_count}", style="bold bright_yellow")

        # Separator
        text.append(" | ", style="dim")

        # Total lines - standard text
        text.append(f"{self.total_lines:,} lines")

        # Separator
        text.append(" | ", style="dim")

        # Active filters - cyan for filter info
        filter_parts: list[str] = []

        # Level filter
        if self.active_levels == LogLevel.all_levels():
            filter_parts.append("levels:ALL")
        else:
            level_names = ",".join(sorted(lvl.name for lvl in self.active_levels))
            filter_parts.append(f"levels:{level_names}")

        # Regex filter
        if self.regex_pattern:
            filter_parts.append(f"filter:/{self.regex_pattern}/")

        # Time filter
        if self.time_filter_display:
            filter_parts.append(self.time_filter_display)

        # Slow query threshold
        if self.slow_threshold is not None:
            filter_parts.append(f"slow:>{self.slow_threshold}ms")

        text.append(" ".join(filter_parts), style="bright_cyan")

        # Separator
        text.append(" | ", style="dim")

        # PostgreSQL instance info - bright white for emphasis
        if self.pg_version:
            text.append(f"PG{self.pg_version}:{self.pg_port}", style="bright_white")
        else:
            text.append(f":{self.pg_port}", style="bright_white")

        return text

    def format_header(self) -> Text:
        """Render header bar with keybinding hints as Rich Text.

        Returns:
            Rich Text object with styled keybinding hints.
        """
        text = Text()
        text.append(" ")

        # Key hints - bright keys, dim descriptions
        hints = [
            ("q", "Quit"),
            ("?", "Help"),
            ("/", "Cmd"),
            ("v", "Visual"),
            ("y", "Yank"),
            ("p", "Pause"),
            ("f", "Follow"),
            ("g/G", "Top/End"),
        ]

        for i, (key, desc) in enumerate(hints):
            if i > 0:
                text.append("  ", style="dim")
            text.append(key, style="bold bright_white")
            text.append(" ", style="dim")
            text.append(desc, style="dim")

        return text
