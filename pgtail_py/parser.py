"""PostgreSQL log line parsing.

Supports TEXT (stderr), CSV (csvlog), and JSON (jsonlog) log formats.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat

if TYPE_CHECKING:
    pass

# Canonical field aliases for LogEntry.get_field()
_FIELD_ALIASES: dict[str, str] = {
    "app": "application_name",
    "application": "application_name",
    "db": "database_name",
    "database": "database_name",
    "user": "user_name",
    "backend": "backend_type",
}


@dataclass
class LogEntry:
    """A parsed PostgreSQL log entry supporting text, CSV, and JSON formats.

    Attributes:
        timestamp: Parsed timestamp, or None if unparseable
        level: Log severity level
        message: The log message content
        raw: Original line (preserved for fallback display)
        pid: Process ID from log line, if present
        format: Detected format of this entry (TEXT, CSV, JSON)

    Extended fields (structured formats only):
        user_name: Database user name
        database_name: Database name
        application_name: Client application name
        sql_state: SQLSTATE error code (e.g., 42P01)
        detail: Error detail message
        hint: Error hint message
        context: Error context
        query: User query that caused the error
        internal_query: Internal query that caused the error
        location: PostgreSQL source code location
        session_id: Session identifier
        session_line_num: Line number within session
        command_tag: Command tag (SELECT, INSERT, etc.) - CSV only
        virtual_transaction_id: Virtual transaction ID
        transaction_id: Transaction ID
        backend_type: Backend type (client backend, autovacuum, etc.)
        leader_pid: Parallel group leader PID
        query_id: Query ID
        connection_from: Client host:port - CSV only
        remote_host: Client host - JSON only
        remote_port: Client port - JSON only
        session_start: Session start time
        query_pos: Error position in query
        internal_query_pos: Error position in internal query
        func_name: Error location function name - JSON only
        file_name: Error location file name - JSON only
        file_line_num: Error location line number - JSON only
    """

    # Core fields (always present)
    timestamp: datetime | None
    level: LogLevel
    message: str
    raw: str
    pid: int | None = None
    format: LogFormat = field(default=LogFormat.TEXT)

    # Multi-file tailing support
    source_file: str | None = None  # Filename (not full path) for multi-file display

    # Extended fields (structured formats only)
    user_name: str | None = None
    database_name: str | None = None
    application_name: str | None = None
    sql_state: str | None = None
    detail: str | None = None
    hint: str | None = None
    context: str | None = None
    query: str | None = None
    internal_query: str | None = None
    location: str | None = None
    session_id: str | None = None
    session_line_num: int | None = None
    command_tag: str | None = None
    virtual_transaction_id: str | None = None
    transaction_id: str | None = None
    backend_type: str | None = None
    leader_pid: int | None = None
    query_id: int | None = None
    connection_from: str | None = None
    remote_host: str | None = None
    remote_port: int | None = None
    session_start: datetime | None = None
    query_pos: int | None = None
    internal_query_pos: int | None = None
    func_name: str | None = None
    file_name: str | None = None
    file_line_num: int | None = None

    def get_field(self, name: str) -> str | int | datetime | None:
        """Get a field value by canonical name.

        Supports aliases like 'app' for 'application_name', 'db' for
        'database_name', etc.

        Args:
            name: Canonical field name (e.g., "app", "db", "user")

        Returns:
            Field value or None if not available.
        """
        # Resolve alias to actual field name
        field_name = _FIELD_ALIASES.get(name, name)

        # Get the attribute value
        return getattr(self, field_name, None)

    def available_fields(self) -> list[str]:
        """Get list of field names that have non-None values.

        Returns:
            Sorted list of field names with values set.
        """
        result: list[str] = []
        for field_name in [
            "timestamp",
            "level",
            "message",
            "raw",
            "pid",
            "format",
            "source_file",
            "user_name",
            "database_name",
            "application_name",
            "sql_state",
            "detail",
            "hint",
            "context",
            "query",
            "internal_query",
            "location",
            "session_id",
            "session_line_num",
            "command_tag",
            "virtual_transaction_id",
            "transaction_id",
            "backend_type",
            "leader_pid",
            "query_id",
            "connection_from",
            "remote_host",
            "remote_port",
            "session_start",
            "query_pos",
            "internal_query_pos",
            "func_name",
            "file_name",
            "file_line_num",
        ]:
            value = getattr(self, field_name, None)
            if value is not None:
                result.append(field_name)
        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for JSON serialization.

        Returns:
            Dictionary with all non-None fields.
            datetime values are converted to ISO 8601 strings.
            LogLevel and LogFormat enums are converted to their string values.
        """
        result: dict[str, Any] = {}

        for field_name in self.available_fields():
            value = getattr(self, field_name)

            # Convert datetime to ISO 8601 string
            if isinstance(value, datetime):
                result[field_name] = value.isoformat()
            # Convert enums to their string values
            elif isinstance(value, LogLevel):
                result[field_name] = value.name
            elif isinstance(value, LogFormat):
                result[field_name] = value.value
            else:
                result[field_name] = value

        return result


# PostgreSQL default log line format (with PID):
# 2024-01-15 10:30:45.123 UTC [12345] LOG:  database system is ready
# Timestamp format: YYYY-MM-DD HH:MM:SS.mmm TZ [PID] LEVEL: message
_LOG_PATTERN_WITH_PID = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"  # timestamp
    r"(\w+)?\s*"  # timezone (optional)
    r"\[(\d+)\]\s+"  # PID
    r"(\w+):\s*"  # level
    r"(.*)$"  # message
)

# PostgreSQL log format without PID (common on Windows):
# 2024-01-15 10:30:45.123 PST LOG:  database system is ready
# Timestamp format: YYYY-MM-DD HH:MM:SS.mmm TZ LEVEL: message
_LOG_PATTERN_NO_PID = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"  # timestamp
    r"(\w+)\s+"  # timezone
    r"(\w+):\s+"  # level
    r"(.*)$"  # message
)

# PostgreSQL bracketed log format (custom log_line_prefix with brackets):
# [2024-01-15 10:30:45.123 UTC] [12345] [dbname] LOG:  message
# Format: [timestamp TZ] [PID] [optional context] LEVEL: message
_LOG_PATTERN_BRACKETED = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"  # [timestamp
    r"(\w+)\]\s+"  # timezone]
    r"\[(\d+)\]\s+"  # [PID]
    r"(?:\[[^\]]*\]\s+)?"  # optional [context/dbname] - skip it
    r"(\w+):\s*"  # level
    r"(.*)$"  # message
)

# Level name to LogLevel mapping
_LEVEL_MAP = {
    "PANIC": LogLevel.PANIC,
    "FATAL": LogLevel.FATAL,
    "ERROR": LogLevel.ERROR,
    "WARNING": LogLevel.WARNING,
    "NOTICE": LogLevel.NOTICE,
    "LOG": LogLevel.LOG,
    "INFO": LogLevel.INFO,
    "DEBUG1": LogLevel.DEBUG1,
    "DEBUG2": LogLevel.DEBUG2,
    "DEBUG3": LogLevel.DEBUG3,
    "DEBUG4": LogLevel.DEBUG4,
    "DEBUG5": LogLevel.DEBUG5,
    # Common aliases
    "DEBUG": LogLevel.DEBUG1,
    "STATEMENT": LogLevel.LOG,
    "DETAIL": LogLevel.LOG,
    "HINT": LogLevel.LOG,
    "CONTEXT": LogLevel.LOG,
}


def _parse_text_line(line: str) -> LogEntry:
    """Parse a PostgreSQL TEXT format log line.

    Handles PostgreSQL log formats:
    - With PID: YYYY-MM-DD HH:MM:SS.mmm TZ [PID] LEVEL: message
    - Without PID: YYYY-MM-DD HH:MM:SS.mmm TZ LEVEL: message (common on Windows)
    - Bracketed: [YYYY-MM-DD HH:MM:SS.mmm TZ] [PID] [context] LEVEL: message

    For unparseable lines, returns a LogEntry with level=LOG and
    the raw line preserved in both message and raw fields.

    Args:
        line: Raw log line from PostgreSQL log file.

    Returns:
        LogEntry with parsed fields, or fallback entry for unparseable lines.
    """
    # Try format with PID first
    match = _LOG_PATTERN_WITH_PID.match(line)
    if match:
        timestamp_str, tz_str, pid_str, level_str, message = match.groups()
        pid = int(pid_str) if pid_str else None
    else:
        # Try bracketed format (timestamp and context in brackets)
        match = _LOG_PATTERN_BRACKETED.match(line)
        if match:
            timestamp_str, tz_str, pid_str, level_str, message = match.groups()
            pid = int(pid_str) if pid_str else None
        else:
            # Try format without PID
            match = _LOG_PATTERN_NO_PID.match(line)
            if match:
                timestamp_str, tz_str, level_str, message = match.groups()
                pid = None
            else:
                # Unparseable line - return as LOG level with raw preserved
                return LogEntry(
                    timestamp=None,
                    level=LogLevel.LOG,
                    message=line,
                    raw=line,
                    pid=None,
                    format=LogFormat.TEXT,
                )

    # Parse timestamp
    timestamp = None
    try:
        # Try with milliseconds
        if "." in timestamp_str:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        # Apply UTC timezone if specified in the log line
        # This is critical for correct time filter comparisons
        if timestamp is not None and tz_str and tz_str.upper() == "UTC":
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Parse level
    level = _LEVEL_MAP.get(level_str.upper(), LogLevel.LOG)

    return LogEntry(
        timestamp=timestamp,
        level=level,
        message=message,
        raw=line,
        pid=pid,
        format=LogFormat.TEXT,
    )


def parse_log_line(line: str, format: LogFormat = LogFormat.TEXT) -> LogEntry:
    """Parse a log line using the appropriate parser.

    Args:
        line: Raw log line
        format: Expected format (TEXT, CSV, or JSON)

    Returns:
        LogEntry with fields populated according to format.
        For unparseable lines, returns fallback entry with raw preserved.
    """
    line = line.rstrip("\n\r")

    if format == LogFormat.CSV:
        from pgtail_py.parser_csv import parse_csv_line

        try:
            return parse_csv_line(line)
        except ValueError:
            # Fallback to raw entry on parse error
            return LogEntry(
                timestamp=None,
                level=LogLevel.LOG,
                message=line,
                raw=line,
                pid=None,
                format=LogFormat.CSV,
            )

    if format == LogFormat.JSON:
        from pgtail_py.parser_json import parse_json_line

        try:
            return parse_json_line(line)
        except ValueError:
            # Fallback to raw entry on parse error
            return LogEntry(
                timestamp=None,
                level=LogLevel.LOG,
                message=line,
                raw=line,
                pid=None,
                format=LogFormat.JSON,
            )

    # Default: TEXT format
    return _parse_text_line(line)
