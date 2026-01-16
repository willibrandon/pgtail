"""Connection highlighters for PostgreSQL log output.

Highlighters in this module:
- ConnectionHighlighter: Host, port, user, database info (priority 600)
- IPHighlighter: IPv4/IPv6 addresses with CIDR (priority 610)
- BackendHighlighter: Backend type names (priority 620)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pgtail_py.highlighter import KeywordHighlighter, Match, RegexHighlighter

if TYPE_CHECKING:
    from pgtail_py.theme import Theme


# =============================================================================
# ConnectionHighlighter
# =============================================================================


class ConnectionHighlighter(RegexHighlighter):
    """Highlights connection information in log messages.

    Matches patterns like:
    - host=192.168.1.1
    - port=5432
    - user=postgres
    - database=mydb
    - application_name=psql
    """

    # Pattern: key=value pairs for connection info
    PATTERN = r'\b(host|port|user|database|application_name)=("[^"]*"|[^\s,]+)'

    def __init__(self) -> None:
        """Initialize connection highlighter."""
        super().__init__(
            name="connection",
            priority=600,
            pattern=self.PATTERN,
            style="hl_connection",
        )
        self._extract_pattern = re.compile(self.PATTERN, re.IGNORECASE)

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Connection info (host, port, user, database)"

    def find_matches(self, text: str, theme: Theme) -> list[Match]:
        """Find all connection info matches with specific styling per field.

        Args:
            text: Input text to search.
            theme: Current theme (unused).

        Returns:
            List of Match objects with field-specific styles.
        """
        matches: list[Match] = []

        for m in self._extract_pattern.finditer(text):
            field = m.group(1).lower()

            # Map field to specific style
            style_map = {
                "host": "hl_host",
                "port": "hl_port",
                "user": "hl_user",
                "database": "hl_database",
                "application_name": "hl_database",  # Use database style for app name
            }

            style = style_map.get(field, "hl_connection")

            matches.append(
                Match(
                    start=m.start(),
                    end=m.end(),
                    style=style,
                    text=m.group(),
                )
            )

        return matches


# =============================================================================
# IPHighlighter
# =============================================================================


class IPHighlighter(RegexHighlighter):
    """Highlights IP addresses (IPv4 and IPv6) with optional CIDR notation.

    Matches:
    - IPv4: 192.168.1.1, 10.0.0.0/8
    - IPv6: ::1, fe80::1, 2001:db8::1/64
    - Mixed: ::ffff:192.168.1.1
    """

    # IPv4 pattern: standard dotted decimal
    IPV4_PATTERN = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/\d{1,2})?\b"

    # IPv6 pattern: simplified but covers most common formats
    IPV6_PATTERN = r"\b(?:[0-9A-Fa-f]{1,4}:){1,7}[0-9A-Fa-f]{1,4}\b|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}(?:/\d{1,3})?"

    # Combined pattern
    PATTERN = f"(?:{IPV4_PATTERN})|(?:{IPV6_PATTERN})"

    def __init__(self) -> None:
        """Initialize IP highlighter."""
        super().__init__(
            name="ip",
            priority=610,
            pattern=self.PATTERN,
            style="hl_ip",
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "IP addresses (IPv4, IPv6, CIDR notation)"


# =============================================================================
# BackendHighlighter
# =============================================================================


class BackendHighlighter(KeywordHighlighter):
    """Highlights PostgreSQL backend process names.

    Uses Aho-Corasick for efficient matching of backend names
    that appear in log messages.
    """

    # PostgreSQL backend process names
    BACKEND_NAMES = {
        # Core backends
        "autovacuum": "hl_backend",
        "autovacuum launcher": "hl_backend",
        "autovacuum worker": "hl_backend",
        "checkpointer": "hl_backend",
        "background writer": "hl_backend",
        "bgwriter": "hl_backend",
        "walwriter": "hl_backend",
        "wal writer": "hl_backend",
        "walsender": "hl_backend",
        "wal sender": "hl_backend",
        "walreceiver": "hl_backend",
        "wal receiver": "hl_backend",
        "startup": "hl_backend",
        "archiver": "hl_backend",
        # Parallel query backends
        "parallel worker": "hl_backend",
        "parallel leader": "hl_backend",
        # Logical replication
        "logical replication launcher": "hl_backend",
        "logical replication worker": "hl_backend",
        # Statistics
        "stats collector": "hl_backend",
        # Background processes
        "postmaster": "hl_backend",
        "postgres": "hl_backend",
        "backend": "hl_backend",
        # Recovery
        "recovery": "hl_backend",
    }

    def __init__(self) -> None:
        """Initialize backend highlighter."""
        super().__init__(
            name="backend",
            priority=620,
            keywords=self.BACKEND_NAMES,
            case_sensitive=False,
            word_boundary=True,
        )

    @property
    def description(self) -> str:
        """Return human-readable description."""
        return "Backend process names (autovacuum, checkpointer, etc.)"


# =============================================================================
# Module-level registration
# =============================================================================


def get_connection_highlighters() -> list[
    ConnectionHighlighter | IPHighlighter | BackendHighlighter
]:
    """Return all connection highlighters for registration.

    Returns:
        List of connection highlighter instances.
    """
    return [
        ConnectionHighlighter(),
        IPHighlighter(),
        BackendHighlighter(),
    ]


__all__ = [
    "ConnectionHighlighter",
    "IPHighlighter",
    "BackendHighlighter",
    "get_connection_highlighters",
]
