"""Connection message parsing for PostgreSQL logs.

Provides regex patterns and parsing functions for connection-related
log messages (connection authorized, disconnection, connection received,
and FATAL connection errors).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.connection_event import ConnectionEventType

# Regex pattern for "connection authorized" messages
# Example: connection authorized: user=postgres database=mydb application_name=psql
PATTERN_CONNECTION_AUTHORIZED = re.compile(
    r"connection authorized:\s+"
    r"user=(?P<user>\S+)\s+"
    r"database=(?P<database>\S+)"
    r"(?:\s+application_name=(?P<application>\S+))?"
)

# Regex pattern for "disconnection" messages
# Example: disconnection: session time: 0:01:23.456 user=postgres database=mydb host=192.168.1.100 port=54321
# Example: disconnection: session time: 1:23:45.678 user=app_user database=production host=[local]
PATTERN_DISCONNECTION = re.compile(
    r"disconnection:\s+session time:\s+"
    r"(?P<duration>[\d:\.]+)\s+"
    r"user=(?P<user>\S+)\s+"
    r"database=(?P<database>\S+)\s+"
    r"host=(?P<host>\S+)"
    r"(?:\s+port=(?P<port>\d+))?"
)

# Regex pattern for "connection received" messages
# Example: connection received: host=192.168.1.100 port=54321
# Example: connection received: host=[local]
PATTERN_CONNECTION_RECEIVED = re.compile(
    r"connection received:\s+"
    r"host=(?P<host>\S+)"
    r"(?:\s+port=(?P<port>\d+))?"
)

# Patterns indicating FATAL connection failures
FATAL_CONNECTION_PATTERNS: list[str] = [
    "too many connections",
    "too many clients already",
    "connection limit exceeded",
    "password authentication failed",
    "no pg_hba.conf entry",
    "database .* does not exist",
    "role .* does not exist",
    "authentication failed",
]


def parse_connection_message(
    message: str, *, is_fatal: bool = False
) -> tuple[ConnectionEventType, dict[str, str | None]] | None:
    """Parse a connection-related log message.

    Attempts to match the message against known connection patterns
    (authorized, disconnection, received) or FATAL error patterns.

    Args:
        message: The log message to parse.
        is_fatal: Whether this message is from a FATAL level log entry.

    Returns:
        Tuple of (ConnectionEventType, dict of extracted fields) if the message
        is connection-related, None otherwise.

        The dict may contain keys: user, database, application, host, port, duration
    """
    from pgtail_py.connection_event import ConnectionEventType

    if not message:
        return None

    # Check for "connection authorized" pattern
    match = PATTERN_CONNECTION_AUTHORIZED.search(message)
    if match:
        return (
            ConnectionEventType.CONNECT,
            {
                "user": match.group("user"),
                "database": match.group("database"),
                "application": match.group("application"),
            },
        )

    # Check for "disconnection" pattern
    match = PATTERN_DISCONNECTION.search(message)
    if match:
        return (
            ConnectionEventType.DISCONNECT,
            {
                "user": match.group("user"),
                "database": match.group("database"),
                "host": match.group("host"),
                "port": match.group("port"),
                "duration": match.group("duration"),
            },
        )

    # Note: "connection received" messages are intentionally NOT tracked.
    # They occur before authentication and don't include user/database info.
    # The "connection authorized" message is the meaningful connection event.
    # Failed auth attempts are tracked via FATAL messages instead.

    # Check for FATAL connection failures
    if is_fatal:
        message_lower = message.lower()
        for pattern in FATAL_CONNECTION_PATTERNS:
            if re.search(pattern, message_lower):
                return (
                    ConnectionEventType.CONNECTION_FAILED,
                    {},
                )

    return None
