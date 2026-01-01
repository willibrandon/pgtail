"""Time-based filtering for PostgreSQL log entries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


# Relative time pattern: number followed by s/m/h/d
_RELATIVE_TIME_PATTERN = re.compile(r"^(\d+)([smhd])$", re.IGNORECASE)

# Time-only patterns: HH:MM or HH:MM:SS
_TIME_ONLY_PATTERN = re.compile(r"^(\d{2}):(\d{2})(?::(\d{2}))?$")


def _now_utc() -> datetime:
    """Return current time in UTC with timezone info."""
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC.

    If naive (no timezone), assumes local time and converts to UTC.
    If already timezone-aware, converts to UTC.

    Args:
        dt: Datetime to convert.

    Returns:
        UTC-aware datetime.
    """
    if dt.tzinfo is None:
        # Naive datetime - assume local time
        local_dt = dt.astimezone()  # Add local timezone
        return local_dt.astimezone(timezone.utc)
    else:
        # Already timezone-aware - convert to UTC
        return dt.astimezone(timezone.utc)


def parse_time(value: str) -> datetime:
    """Parse time string into UTC-aware datetime.

    Supported formats:
    - Relative: 5m, 30s, 2h, 1d (duration from now)
    - Time only: 14:30, 14:30:45 (today at specified time)
    - Date-time: 2024-01-15T14:30, 2024-01-15T14:30:00Z (ISO 8601)

    Args:
        value: Time specification string.

    Returns:
        UTC-aware datetime. All returned datetimes are timezone-aware
        to enable safe comparison with log entry timestamps.

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
        return _now_utc() - delta

    # Try time-only format (HH:MM or HH:MM:SS)
    match = _TIME_ONLY_PATTERN.match(value)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        second = int(match.group(3)) if match.group(3) else 0

        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError(
                f"Invalid time '{value}'. Hours must be 0-23, minutes and seconds must be 0-59."
            )

        # Combine with today's date in local timezone, then convert to UTC
        today = datetime.now().date()
        naive_dt = datetime.combine(today, time(hour, minute, second))
        return _to_utc(naive_dt)

    # Try ISO 8601 format (with or without Z suffix)
    try:
        # Handle Z suffix for UTC
        if value.endswith("Z"):
            # fromisoformat doesn't handle Z directly in older Python
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        # Always return UTC-aware datetime
        return _to_utc(parsed)
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
        dt: Datetime to check (can be naive or timezone-aware).

    Returns:
        True if dt > now.
    """
    # Normalize both to UTC for comparison
    dt_utc = _to_utc(dt)
    return dt_utc > _now_utc()


def format_time_range(
    since: datetime | None,
    until: datetime | None,
    original_input: str = "",
) -> str:
    """Format time range for human-readable display.

    Args:
        since: Start time or None (can be naive or timezone-aware).
        until: End time or None (can be naive or timezone-aware).
        original_input: Original user input for context.

    Returns:
        Human-readable string describing the time range.
    """
    if since is None and until is None:
        return ""

    time_fmt = "%H:%M:%S"
    date_time_fmt = "%Y-%m-%d %H:%M:%S"
    today = datetime.now().date()

    def format_dt(dt: datetime, include_today: bool = False) -> str:
        """Format datetime, using time only if today.

        Converts to local time for display.
        """
        # Convert to local time for display
        if dt.tzinfo is not None:
            local_dt = dt.astimezone()  # Convert to local timezone
        else:
            local_dt = dt

        if local_dt.date() == today:
            time_str = local_dt.strftime(time_fmt)
            return f"{time_str} today" if include_today else time_str
        return local_dt.strftime(date_time_fmt)

    if since is not None and until is not None:
        return f"between {format_dt(since)} and {format_dt(until)}"
    elif since is not None:
        return f"since {format_dt(since, include_today=True)}"
    else:  # until is not None
        return f"until {format_dt(until, include_today=True)}"


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
        if self.since is not None and self.until is not None and self.since > self.until:
            raise ValueError(
                f"Start time ({self.since.strftime('%H:%M:%S')}) must be "
                f"before end time ({self.until.strftime('%H:%M:%S')})"
            )

    def matches(self, entry: LogEntry) -> bool:
        """Check if a log entry falls within the time filter.

        Handles both naive and timezone-aware timestamps by normalizing
        to UTC for comparison.

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

        # Normalize entry timestamp to UTC for comparison
        entry_ts = _to_utc(entry.timestamp)

        # Check lower bound (self.since is already UTC-aware from parse_time)
        if self.since is not None:
            since_utc = _to_utc(self.since) if self.since.tzinfo is None else self.since
            if entry_ts < since_utc:
                return False

        # Check upper bound (self.until is already UTC-aware from parse_time)
        if self.until is not None:
            until_utc = _to_utc(self.until) if self.until.tzinfo is None else self.until
            if entry_ts > until_utc:
                return False

        return True

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
