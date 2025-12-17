"""PostgreSQL JSON log format (jsonlog) parser.

Parses PostgreSQL JSON log files introduced in PostgreSQL 15 with up to 29 fields
as documented in: https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

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


def _parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse a PostgreSQL JSON timestamp string.

    Handles format: "2024-01-15 10:30:45.123 PST"

    Args:
        ts_str: Timestamp string from JSON log

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
        data: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("JSON log entry must be an object")

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
        timestamp=_parse_timestamp(data.get("timestamp")),
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
        session_start=_parse_timestamp(data.get("session_start")),
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
