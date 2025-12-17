"""Error statistics tracking for PostgreSQL logs.

Tracks ERROR, FATAL, PANIC, and WARNING log entries and provides
statistics, trends, and breakdowns by SQLSTATE code.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry

# Error levels to track
ERROR_LEVELS: frozenset[LogLevel] = frozenset({LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR})
WARNING_LEVELS: frozenset[LogLevel] = frozenset({LogLevel.WARNING})
TRACKED_LEVELS: frozenset[LogLevel] = ERROR_LEVELS | WARNING_LEVELS

# SQLSTATE code categories (first 2 chars)
SQLSTATE_CATEGORIES: dict[str, str] = {
    "00": "Successful Completion",
    "01": "Warning",
    "02": "No Data",
    "03": "SQL Statement Not Yet Complete",
    "08": "Connection Exception",
    "09": "Triggered Action Exception",
    "0A": "Feature Not Supported",
    "0B": "Invalid Transaction Initiation",
    "0F": "Locator Exception",
    "0L": "Invalid Grantor",
    "0P": "Invalid Role Specification",
    "0Z": "Diagnostics Exception",
    "20": "Case Not Found",
    "21": "Cardinality Violation",
    "22": "Data Exception",
    "23": "Integrity Constraint Violation",
    "24": "Invalid Cursor State",
    "25": "Invalid Transaction State",
    "26": "Invalid SQL Statement Name",
    "27": "Triggered Data Change Violation",
    "28": "Invalid Authorization Specification",
    "2B": "Dependent Privilege Descriptors Still Exist",
    "2D": "Invalid Transaction Termination",
    "2F": "SQL Routine Exception",
    "34": "Invalid Cursor Name",
    "38": "External Routine Exception",
    "39": "External Routine Invocation Exception",
    "3B": "Savepoint Exception",
    "3D": "Invalid Catalog Name",
    "3F": "Invalid Schema Name",
    "40": "Transaction Rollback",
    "42": "Syntax Error or Access Rule Violation",
    "44": "WITH CHECK OPTION Violation",
    "53": "Insufficient Resources",
    "54": "Program Limit Exceeded",
    "55": "Object Not In Prerequisite State",
    "57": "Operator Intervention",
    "58": "System Error",
    "72": "Snapshot Failure",
    "F0": "Configuration File Error",
    "HV": "Foreign Data Wrapper Error",
    "P0": "PL/pgSQL Error",
    "XX": "Internal Error",
}

# Common SQLSTATE codes with human-readable names
SQLSTATE_NAMES: dict[str, str] = {
    "23502": "not_null_violation",
    "23503": "foreign_key_violation",
    "23505": "unique_violation",
    "23514": "check_violation",
    "23P01": "exclusion_violation",
    "42501": "insufficient_privilege",
    "42601": "syntax_error",
    "42602": "invalid_name",
    "42703": "undefined_column",
    "42704": "undefined_object",
    "42710": "duplicate_object",
    "42P01": "undefined_table",
    "42P02": "undefined_parameter",
    "53100": "disk_full",
    "53200": "out_of_memory",
    "53300": "too_many_connections",
    "57014": "query_canceled",
    "57P01": "admin_shutdown",
    "57P02": "crash_shutdown",
    "57P03": "cannot_connect_now",
    "58030": "io_error",
    "40001": "serialization_failure",
    "40P01": "deadlock_detected",
}


def get_sqlstate_name(code: str) -> str:
    """Get human-readable name for SQLSTATE code.

    Args:
        code: 5-character SQLSTATE code (e.g., "23505")

    Returns:
        Human-readable name if known, otherwise the code itself.
    """
    return SQLSTATE_NAMES.get(code, code)


def get_sqlstate_category(code: str) -> str:
    """Get category for SQLSTATE code class.

    Args:
        code: 5-character SQLSTATE code (e.g., "23505")

    Returns:
        Category name if known, otherwise "Unknown".
    """
    if len(code) >= 2:
        return SQLSTATE_CATEGORIES.get(code[:2], "Unknown")
    return "Unknown"


@dataclass(frozen=True)
class ErrorEvent:
    """A tracked error or warning event."""

    timestamp: datetime
    level: LogLevel
    sql_state: str | None
    message: str
    pid: int | None
    database: str | None
    user: str | None

    @classmethod
    def from_entry(cls, entry: LogEntry) -> ErrorEvent:
        """Create ErrorEvent from a LogEntry.

        Args:
            entry: Parsed log entry with error/warning level.

        Returns:
            ErrorEvent with relevant fields extracted.
        """
        return cls(
            timestamp=entry.timestamp or datetime.now(),
            level=entry.level,
            sql_state=entry.sql_state,
            message=(entry.message or "")[:200],
            pid=entry.pid,
            database=entry.database_name,
            user=entry.user_name,
        )


@dataclass
class ErrorStats:
    """Session-scoped error statistics aggregator."""

    _events: deque[ErrorEvent] = field(default_factory=lambda: deque(maxlen=10000))
    session_start: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    warning_count: int = 0
    last_error_time: datetime | None = None

    def add(self, entry: LogEntry) -> None:
        """Add a log entry if it's an error/warning.

        Args:
            entry: Parsed log entry to potentially track.
        """
        if entry.level not in TRACKED_LEVELS:
            return

        event = ErrorEvent.from_entry(entry)
        self._events.append(event)

        if entry.level in ERROR_LEVELS:
            self.error_count += 1
            self.last_error_time = event.timestamp
        else:
            self.warning_count += 1

    def clear(self) -> None:
        """Reset all statistics."""
        self._events.clear()
        self.error_count = 0
        self.warning_count = 0
        self.last_error_time = None
        self.session_start = datetime.now()

    def is_empty(self) -> bool:
        """Check if any events tracked.

        Returns:
            True if no events have been recorded.
        """
        return len(self._events) == 0

    def get_by_level(self) -> dict[LogLevel, int]:
        """Get error counts by severity level.

        Returns:
            Dictionary mapping LogLevel to count.
        """
        counts: dict[LogLevel, int] = defaultdict(int)
        for event in self._events:
            counts[event.level] += 1
        return dict(counts)

    def get_by_code(self) -> dict[str, int]:
        """Get error counts by SQLSTATE code, sorted by frequency.

        Returns:
            Dictionary mapping SQLSTATE code to count, sorted descending.
        """
        counts: dict[str, int] = defaultdict(int)
        for event in self._events:
            code = event.sql_state or "UNKNOWN"
            counts[code] += 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def get_events_since(self, since: datetime) -> list[ErrorEvent]:
        """Get events after a specific timestamp.

        Args:
            since: Only return events after this time.

        Returns:
            List of events in chronological order.
        """
        return [e for e in self._events if e.timestamp >= since]

    def get_events_by_code(self, code: str) -> list[ErrorEvent]:
        """Get events with a specific SQLSTATE code.

        Args:
            code: SQLSTATE code to filter by.

        Returns:
            List of matching events in chronological order.
        """
        return [e for e in self._events if e.sql_state == code]

    def get_trend_buckets(self, minutes: int = 60) -> list[int]:
        """Get per-minute error counts for trend visualization.

        Args:
            minutes: Number of minutes to bucket (default 60).

        Returns:
            List of counts per minute, oldest first.
        """
        from pgtail_py.error_trend import bucket_events

        return bucket_events(list(self._events), minutes)
