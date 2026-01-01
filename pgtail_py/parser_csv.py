"""PostgreSQL CSV log format (csvlog) parser.

Parses PostgreSQL CSV log files with 26 standard fields as documented in:
https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta, timezone
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


# Common timezone abbreviation offsets (hours from UTC)
# PostgreSQL uses these when log_timezone is set
_TZ_OFFSETS: dict[str, int] = {
    "UTC": 0,
    "GMT": 0,
    "Z": 0,
    # US timezones
    "EST": -5,
    "EDT": -4,
    "CST": -6,
    "CDT": -5,
    "MST": -7,
    "MDT": -6,
    "PST": -8,
    "PDT": -7,
    "AKST": -9,
    "AKDT": -8,
    "HST": -10,
    # European timezones
    "WET": 0,
    "WEST": 1,
    "CET": 1,
    "CEST": 2,
    "EET": 2,
    "EEST": 3,
    # Other common timezones
    "JST": 9,
    "KST": 9,
    "IST": 5,  # India (5:30, approximated to 5)
    "AEST": 10,
    "AEDT": 11,
    "NZST": 12,
    "NZDT": 13,
}

# Regex for ISO 8601 offset: +HH:MM, -HH:MM, +HH, -HH
_ISO_OFFSET_RE = re.compile(r"([+-])(\d{2}):?(\d{2})?$")


def parse_timestamp(ts_str: str) -> datetime | None:
    """Parse a PostgreSQL CSV timestamp string to UTC-aware datetime.

    Handles formats:
    - "2024-01-15 10:30:45.123 PST" (PostgreSQL with named timezone)
    - "2024-01-15 10:30:45.123+00" (ISO 8601 offset)
    - "2024-01-15 10:30:45.123+00:00" (ISO 8601 offset with colon)
    - "2024-01-15T10:30:45.123Z" (ISO 8601 with Z)

    Args:
        ts_str: Timestamp string from CSV log

    Returns:
        UTC-aware datetime or None if unparseable
    """
    if not ts_str:
        return None

    ts_str = ts_str.strip()
    tz_offset: timedelta | None = None

    # Check if this looks like ISO 8601 format (has T as date/time separator)
    # The T must be preceded by a digit (from date) and followed by a digit (from time)
    is_iso_format = bool(re.search(r"\dT\d", ts_str))

    # Check for ISO 8601 T separator and Z suffix
    if is_iso_format and ts_str.endswith("Z"):
        ts_str = ts_str[:-1]  # Remove Z
        tz_offset = timedelta(0)
    elif is_iso_format or _ISO_OFFSET_RE.search(ts_str):
        # Check for ISO 8601 offset format (+HH:MM or +HH)
        match = _ISO_OFFSET_RE.search(ts_str)
        if match:
            sign = 1 if match.group(1) == "+" else -1
            hours = int(match.group(2))
            minutes = int(match.group(3)) if match.group(3) else 0
            tz_offset = timedelta(hours=sign * hours, minutes=sign * minutes)
            ts_str = ts_str[: match.start()].strip()
    else:
        # PostgreSQL format: "2024-01-15 10:30:45.123 PST"
        parts = ts_str.rsplit(" ", 1)
        if len(parts) == 2 and len(parts[1]) <= 5:
            tz_name = parts[1].upper()
            if tz_name in _TZ_OFFSETS:
                tz_offset = timedelta(hours=_TZ_OFFSETS[tz_name])
                ts_str = parts[0]
            elif parts[1].isalpha():
                # Unknown timezone abbreviation, assume UTC
                ts_str = parts[0]
                tz_offset = timedelta(0)

    # Parse the datetime portion
    try:
        # Handle T separator for ISO 8601
        ts_str = ts_str.replace("T", " ")
        if "." in ts_str:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    # Apply timezone offset and convert to UTC
    if tz_offset is not None:
        # Create a fixed offset timezone and convert to UTC
        local_tz = timezone(tz_offset)
        dt = dt.replace(tzinfo=local_tz).astimezone(timezone.utc)
    else:
        # No timezone info - assume local time, convert to UTC
        local_dt = dt.astimezone()  # Attach local timezone
        dt = local_dt.astimezone(timezone.utc)

    return dt


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
        timestamp=parse_timestamp(get_field(0)),
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
        session_start=parse_timestamp(get_field(8)),
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
