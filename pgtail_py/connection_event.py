"""Connection event tracking for PostgreSQL logs.

Provides data structures for tracking connection and disconnection events
parsed from PostgreSQL log files.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


class ConnectionEventType(Enum):
    """Type of connection event."""

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    CONNECTION_FAILED = "failed"


@dataclass(frozen=True)
class ConnectionEvent:
    """A tracked connection or disconnection event.

    This is an immutable (frozen) dataclass representing a single
    connection event parsed from PostgreSQL logs.

    Attributes:
        timestamp: When the event occurred.
        event_type: CONNECT, DISCONNECT, or CONNECTION_FAILED.
        pid: PostgreSQL backend process ID.
        user: Database user name.
        database: Database name.
        application: Client application name (default: "unknown").
        host: Client IP address or "[local]".
        port: Client port number.
        duration_seconds: Session duration (disconnect events only).
    """

    timestamp: datetime
    event_type: ConnectionEventType
    pid: int | None = None
    user: str | None = None
    database: str | None = None
    application: str = "unknown"
    host: str | None = None
    port: int | None = None
    duration_seconds: float | None = None

    @classmethod
    def from_log_entry(cls, entry: LogEntry) -> ConnectionEvent | None:
        """Create a ConnectionEvent from a LogEntry.

        Parses the log entry message to determine if it's a connection-related
        event and extracts relevant fields.

        Args:
            entry: Parsed log entry to process.

        Returns:
            ConnectionEvent if entry is connection-related, None otherwise.
        """
        from pgtail_py.connection_parser import parse_connection_message
        from pgtail_py.filter import LogLevel

        # Determine if this is a FATAL level (potential connection failure)
        is_fatal = entry.level == LogLevel.FATAL

        # Try to parse the message
        result = parse_connection_message(entry.message, is_fatal=is_fatal)
        if result is None:
            return None

        event_type, data = result

        # Use structured fields from LogEntry when available (CSV/JSON formats)
        # Fall back to parsed message data
        user = entry.user_name or data.get("user")
        database = entry.database_name or data.get("database")
        application = entry.application_name or data.get("application") or "unknown"
        host = entry.remote_host or data.get("host")

        # Port: prefer structured field, fall back to parsed
        port: int | None = None
        if entry.remote_port is not None:
            port = entry.remote_port
        else:
            port_str = data.get("port")
            if port_str:
                with contextlib.suppress(ValueError, TypeError):
                    port = int(port_str)

        # Parse duration for disconnect events
        duration_seconds: float | None = None
        if event_type == ConnectionEventType.DISCONNECT:
            duration_str = data.get("duration")
            if duration_str:
                duration_seconds = _parse_duration(duration_str)

        # Use entry timestamp or default to now
        timestamp = entry.timestamp or datetime.now()

        return cls(
            timestamp=timestamp,
            event_type=event_type,
            pid=entry.pid,
            user=user,
            database=database,
            application=application,
            host=host,
            port=port,
            duration_seconds=duration_seconds,
        )


def _parse_duration(duration_str: str) -> float | None:
    """Parse PostgreSQL session duration string to seconds.

    PostgreSQL format: H:MM:SS.mmm (e.g., "0:01:23.456" or "12:34:56.789")

    Args:
        duration_str: Duration string from disconnection log message.

    Returns:
        Duration in seconds, or None if parsing fails.
    """
    try:
        parts = duration_str.split(":")
        if len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        pass
    return None
