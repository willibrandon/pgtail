"""PostgreSQL log line parsing."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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

    timestamp: Optional[datetime]
    level: LogLevel
    message: str
    raw: str
    pid: Optional[int] = None
