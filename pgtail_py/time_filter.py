"""Time-based filtering for PostgreSQL log entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


# Relative time pattern: number followed by s/m/h/d
_RELATIVE_TIME_PATTERN = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)

# Time-only patterns: HH:MM or HH:MM:SS
_TIME_ONLY_PATTERN = re.compile(r"^(\d{2}):(\d{2})(?::(\d{2}))?$")


def parse_time(value: str) -> datetime:
    """Parse time string into datetime.

    Supported formats:
    - Relative: 5m, 30s, 2h, 1d (duration from now)
    - Time only: 14:30, 14:30:45 (today at specified time)
    - Date-time: 2024-01-15T14:30, 2024-01-15T14:30:00Z (ISO 8601)

    Args:
        value: Time specification string.

    Returns:
        Resolved datetime.

    Raises:
        ValueError: If value cannot be parsed.
    """
    value = value.strip()
    if not value:
        raise ValueError("Time value cannot be empty")

    # Try relative time first (e.g., 5m, 2h, 1d, 30s)
    match = _RELATIVE_TIME_PATTERN.match(value)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        delta = {
            "s": timedelta(seconds=amount),
            "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount),
            "d": timedelta(days=amount),
        }[unit]
        return datetime.now() - delta

    # Try time-only format (HH:MM or HH:MM:SS)
    match = _TIME_ONLY_PATTERN.match(value)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3)) if match.group(3) else 0

        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError(
                f"Invalid time '{value}'. Hours must be 0-23, "
                "minutes and seconds must be 0-59."
            )

        today = datetime.now().date()
        return datetime.combine(today, time(hour, minute, second))

    # Try ISO 8601 format (with or without Z suffix)
    try:
        # Handle Z suffix for UTC
        if value.endswith("Z"):
            # fromisoformat doesn't handle Z directly in older Python
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    # Provide helpful error message
    raise ValueError(
        f"Invalid time format '{value}'. Supported formats:\n"
        "  - Relative: 5m, 30s, 2h, 1d (from now)\n"
        "  - Time only: 14:30, 14:30:45 (today)\n"
        "  - ISO 8601: 2024-01-15T14:30, 2024-01-15T14:30:00Z"
    )


def is_future_time(dt: datetime) -> bool:
    """Check if datetime is in the future.

    Args:
        dt: Datetime to check.

    Returns:
        True if dt > now.
    """
    return dt > datetime.now()


def format_time_range(
    since: datetime | None,
    until: datetime | None,
    original_input: str = "",
) -> str:
    """Format time range for human-readable display.

    Args:
        since: Start time or None.
        until: End time or None.
        original_input: Original user input for context.

    Returns:
        Human-readable string describing the time range.
    """
    if since is None and until is None:
        return ""

    time_fmt = "%H:%M:%S"
    date_time_fmt = "%Y-%m-%d %H:%M:%S"

    def format_dt(dt: datetime) -> str:
        """Format datetime, using time only if today."""
        if dt.date() == datetime.now().date():
            return dt.strftime(time_fmt)
        return dt.strftime(date_time_fmt)

    if since is not None and until is not None:
        return f"between {format_dt(since)} and {format_dt(until)}"
    elif since is not None:
        return f"since {format_dt(since)}"
    else:  # until is not None
        return f"until {format_dt(until)}"


@dataclass
class TimeFilter:
    """Time-based filter for log entries.

    Attributes:
        since: Include entries at or after this time. None means no lower bound.
        until: Include entries at or before this time. None means no upper bound.
        original_input: Original user input string for display purposes.
    """

    since: datetime | None = None
    until: datetime | None = None
    original_input: str = ""

    def __post_init__(self) -> None:
        """Validate that since <= until when both are set."""
        if (
            self.since is not None
            and self.until is not None
            and self.since > self.until
        ):
            raise ValueError(
                f"Start time ({self.since.strftime('%H:%M:%S')}) must be "
                f"before end time ({self.until.strftime('%H:%M:%S')})"
            )

    def matches(self, entry: LogEntry) -> bool:
        """Check if a log entry falls within the time filter.

        Args:
            entry: Log entry to check.

        Returns:
            True if entry matches filter, False otherwise.
            Entries without timestamps return False when any time filter is active.
        """
        # If no filter is active, all entries match
        if not self.is_active():
            return True

        # Entries without timestamps are filtered out when time filter is active
        if entry.timestamp is None:
            return False

        # Check lower bound
        if self.since is not None and entry.timestamp < self.since:
            return False

        # Check upper bound
        return not (self.until is not None and entry.timestamp > self.until)

    def is_active(self) -> bool:
        """Check if any time constraint is set."""
        return self.since is not None or self.until is not None

    def format_description(self) -> str:
        """Return human-readable description of active filter."""
        return format_time_range(self.since, self.until, self.original_input)

    @classmethod
    def empty(cls) -> TimeFilter:
        """Return an empty (inactive) time filter."""
        return cls()
