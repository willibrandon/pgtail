"""PostgreSQL JSON log format (jsonlog) parser.

Parses PostgreSQL JSON log files introduced in PostgreSQL 15 with up to 29 fields
as documented in: https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry

# JSON field key mapping to LogEntry attributes
# Maps PostgreSQL JSON log keys to canonical LogEntry field names
JSON_FIELD_MAP: dict[str, str] = {
    "timestamp": "timestamp",
    "user": "user_name",
    "dbname": "database_name",
    "pid": "pid",
    "remote_host": "remote_host",
    "remote_port": "remote_port",
    "session_id": "session_id",
    "line_num": "session_line_num",
    "session_start": "session_start",
    "vxid": "virtual_transaction_id",
    "txid": "transaction_id",
    "error_severity": "level",
    "state_code": "sql_state",
    "message": "message",
    "detail": "detail",
    "hint": "hint",
    "internal_query": "internal_query",
    "internal_position": "internal_query_pos",
    "context": "context",
    "statement": "query",
    "cursor_position": "query_pos",
    "func_name": "func_name",
    "file_name": "file_name",
    "file_line_num": "file_line_num",
    "application_name": "application_name",
    "backend_type": "backend_type",
    "leader_pid": "leader_pid",
    "query_id": "query_id",
}

# Level name to LogLevel mapping
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


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse a PostgreSQL JSON timestamp string to UTC-aware datetime.

    Handles formats:
    - "2024-01-15 10:30:45.123 PST" (PostgreSQL with named timezone)
    - "2024-01-15 10:30:45.123+00" (ISO 8601 offset)
    - "2024-01-15 10:30:45.123+00:00" (ISO 8601 offset with colon)
    - "2024-01-15T10:30:45.123Z" (ISO 8601 with Z)

    Args:
        ts_str: Timestamp string from JSON log

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


def parse_json_line(line: str) -> LogEntry:
    """Parse a PostgreSQL JSON log line.

    Args:
        line: Raw JSON log line (single JSON object)

    Returns:
        LogEntry with format=LogFormat.JSON and available fields populated.

    Raises:
        ValueError: If line cannot be parsed as valid JSON log entry.
    """
    # Import here to avoid circular imports
    from pgtail_py.filter import LogLevel
    from pgtail_py.format_detector import LogFormat
    from pgtail_py.parser import LogEntry

    line = line.rstrip("\n\r")

    try:
        raw_data = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") from e

    if not isinstance(raw_data, dict):
        raise ValueError("JSON log entry must be an object")
    data: dict[str, Any] = cast(dict[str, Any], raw_data)

    # Parse error_severity to LogLevel
    severity_str = data.get("error_severity", "LOG")
    if isinstance(severity_str, str):
        severity_str = severity_str.upper()
    else:
        severity_str = "LOG"
    level_name = _LEVEL_MAP.get(severity_str, "LOG")
    level = LogLevel[level_name]

    # Get message (required field)
    message = data.get("message", "")
    if not isinstance(message, str):
        message = str(message)

    # Helper to get string or None
    def get_str(key: str) -> str | None:
        val = data.get(key)
        return str(val) if val is not None else None

    # Helper to get int or None
    def get_int(key: str) -> int | None:
        val = data.get(key)
        if val is None:
            return None
        if isinstance(val, int):
            return val
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # Build the LogEntry
    return LogEntry(
        # Core fields
        timestamp=parse_timestamp(data.get("timestamp")),
        level=level,
        message=message,
        raw=line,
        pid=get_int("pid"),
        format=LogFormat.JSON,
        # Extended fields from JSON
        user_name=get_str("user"),
        database_name=get_str("dbname"),
        remote_host=get_str("remote_host"),
        remote_port=get_int("remote_port"),
        session_id=get_str("session_id"),
        session_line_num=get_int("line_num"),
        session_start=parse_timestamp(data.get("session_start")),
        virtual_transaction_id=get_str("vxid"),
        transaction_id=get_str("txid"),
        sql_state=get_str("state_code"),
        detail=get_str("detail"),
        hint=get_str("hint"),
        internal_query=get_str("internal_query"),
        internal_query_pos=get_int("internal_position"),
        context=get_str("context"),
        query=get_str("statement"),
        query_pos=get_int("cursor_position"),
        func_name=get_str("func_name"),
        file_name=get_str("file_name"),
        file_line_num=get_int("file_line_num"),
        application_name=get_str("application_name"),
        backend_type=get_str("backend_type"),
        leader_pid=get_int("leader_pid"),
        query_id=get_int("query_id"),
    )
