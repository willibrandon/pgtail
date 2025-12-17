"""PostgreSQL CSV log format (csvlog) parser.

Parses PostgreSQL CSV log files with 26 standard fields as documented in:
https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry

# CSV field indices (26 columns in PostgreSQL 14+)
# Older versions may have 22-25 fields; parser handles this gracefully
CSV_FIELD_ORDER: list[str] = [
    "log_time",  # 0
    "user_name",  # 1
    "database_name",  # 2
    "process_id",  # 3
    "connection_from",  # 4
    "session_id",  # 5
    "session_line_num",  # 6
    "command_tag",  # 7
    "session_start_time",  # 8
    "virtual_transaction_id",  # 9
    "transaction_id",  # 10
    "error_severity",  # 11
    "sql_state_code",  # 12
    "message",  # 13
    "detail",  # 14
    "hint",  # 15
    "internal_query",  # 16
    "internal_query_pos",  # 17
    "context",  # 18
    "query",  # 19
    "query_pos",  # 20
    "location",  # 21
    "application_name",  # 22
    "backend_type",  # 23
    "leader_pid",  # 24
    "query_id",  # 25
]

# Level name to LogLevel mapping (imported here to avoid circular imports)
_LEVEL_MAP = {
    "PANIC": "PANIC",
    "FATAL": "FATAL",
    "ERROR": "ERROR",
    "WARNING": "WARNING",
    "NOTICE": "NOTICE",
    "LOG": "LOG",
    "INFO": "INFO",
    "DEBUG1": "DEBUG1",
    "DEBUG2": "DEBUG2",
    "DEBUG3": "DEBUG3",
    "DEBUG4": "DEBUG4",
    "DEBUG5": "DEBUG5",
    "DEBUG": "DEBUG1",
    "STATEMENT": "LOG",
    "DETAIL": "LOG",
    "HINT": "LOG",
    "CONTEXT": "LOG",
}


def _parse_timestamp(ts_str: str) -> datetime | None:
    """Parse a PostgreSQL CSV timestamp string.

    Handles format: "2024-01-15 10:30:45.123 PST"

    Args:
        ts_str: Timestamp string from CSV log

    Returns:
        Parsed datetime or None if unparseable
    """
    if not ts_str:
        return None

    # Strip timezone suffix (we don't convert timezones, just parse the time)
    # Format: "2024-01-15 10:30:45.123 PST" -> "2024-01-15 10:30:45.123"
    parts = ts_str.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) <= 5:  # Timezone is typically 3-5 chars
        ts_str = parts[0]

    try:
        if "." in ts_str:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _safe_int(value: str) -> int | None:
    """Safely parse an integer from a string.

    Args:
        value: String to parse

    Returns:
        Integer value or None if empty/unparseable
    """
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _non_empty(value: str) -> str | None:
    """Return value if non-empty, else None.

    Args:
        value: String to check

    Returns:
        Value if non-empty, None otherwise
    """
    return value if value else None


def parse_csv_line(line: str) -> LogEntry:
    """Parse a PostgreSQL CSV log line.

    Args:
        line: Raw CSV log line (26 comma-separated fields)

    Returns:
        LogEntry with format=LogFormat.CSV and all fields populated.

    Raises:
        ValueError: If line cannot be parsed as valid CSV log entry.
    """
    # Import here to avoid circular imports
    from pgtail_py.filter import LogLevel
    from pgtail_py.format_detector import LogFormat
    from pgtail_py.parser import LogEntry

    line = line.rstrip("\n\r")

    try:
        reader = csv.reader(StringIO(line))
        fields = next(reader)
    except (csv.Error, StopIteration) as e:
        raise ValueError(f"Invalid CSV format: {e}") from e

    # PostgreSQL CSV logs have 22-26 fields depending on version
    if len(fields) < 14:  # Need at least through message field
        raise ValueError(f"CSV line has {len(fields)} fields, need at least 14")

    # Helper to get field by index with default
    def get_field(idx: int) -> str:
        return fields[idx] if idx < len(fields) else ""

    # Parse error_severity to LogLevel
    severity_str = get_field(11).upper()
    level_name = _LEVEL_MAP.get(severity_str, "LOG")
    level = LogLevel[level_name]

    # Build the LogEntry
    return LogEntry(
        # Core fields
        timestamp=_parse_timestamp(get_field(0)),
        level=level,
        message=get_field(13),
        raw=line,
        pid=_safe_int(get_field(3)),
        format=LogFormat.CSV,
        # Extended fields from CSV
        user_name=_non_empty(get_field(1)),
        database_name=_non_empty(get_field(2)),
        connection_from=_non_empty(get_field(4)),
        session_id=_non_empty(get_field(5)),
        session_line_num=_safe_int(get_field(6)),
        command_tag=_non_empty(get_field(7)),
        session_start=_parse_timestamp(get_field(8)),
        virtual_transaction_id=_non_empty(get_field(9)),
        transaction_id=_non_empty(get_field(10)),
        sql_state=_non_empty(get_field(12)),
        detail=_non_empty(get_field(14)),
        hint=_non_empty(get_field(15)),
        internal_query=_non_empty(get_field(16)),
        internal_query_pos=_safe_int(get_field(17)),
        context=_non_empty(get_field(18)),
        query=_non_empty(get_field(19)),
        query_pos=_safe_int(get_field(20)),
        location=_non_empty(get_field(21)),
        application_name=_non_empty(get_field(22)),
        backend_type=_non_empty(get_field(23)),
        leader_pid=_safe_int(get_field(24)),
        query_id=_safe_int(get_field(25)),
    )
