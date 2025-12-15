"""PostgreSQL log line parsing."""

import re
from dataclasses import dataclass
from datetime import datetime

from pgtail_py.filter import LogLevel


@dataclass
class LogEntry:
    """A parsed PostgreSQL log line.

    Attributes:
        timestamp: Parsed timestamp, or None if unparseable
        level: Log severity level
        message: The log message content
        raw: Original line (preserved for fallback display)
        pid: Process ID from log line, if present
    """

    timestamp: datetime | None
    level: LogLevel
    message: str
    raw: str
    pid: int | None = None


# PostgreSQL default log line format:
# 2024-01-15 10:30:45.123 UTC [12345] LOG:  database system is ready
# Timestamp format: YYYY-MM-DD HH:MM:SS.mmm TZ [PID] LEVEL: message
_LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+"  # timestamp
    r"(\w+)?\s*"  # timezone (optional)
    r"\[(\d+)\]\s+"  # PID
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


def parse_log_line(line: str) -> LogEntry:
    """Parse a PostgreSQL log line into a LogEntry.

    Handles the default PostgreSQL log format:
    YYYY-MM-DD HH:MM:SS.mmm TZ [PID] LEVEL: message

    For unparseable lines, returns a LogEntry with level=LOG and
    the raw line preserved in both message and raw fields.

    Args:
        line: Raw log line from PostgreSQL log file.

    Returns:
        LogEntry with parsed fields, or fallback entry for unparseable lines.
    """
    line = line.rstrip("\n\r")
    match = _LOG_PATTERN.match(line)

    if not match:
        # Unparseable line - return as LOG level with raw preserved
        return LogEntry(
            timestamp=None,
            level=LogLevel.LOG,
            message=line,
            raw=line,
            pid=None,
        )

    timestamp_str, _tz, pid_str, level_str, message = match.groups()

    # Parse timestamp
    timestamp = None
    try:
        # Try with milliseconds
        if "." in timestamp_str:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        pass

    # Parse level
    level = _LEVEL_MAP.get(level_str.upper(), LogLevel.LOG)

    # Parse PID
    pid = int(pid_str) if pid_str else None

    return LogEntry(
        timestamp=timestamp,
        level=level,
        message=message,
        raw=line,
        pid=pid,
    )
