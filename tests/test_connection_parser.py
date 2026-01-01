"""Tests for connection message parsing."""

from __future__ import annotations

from pgtail_py.connection_parser import (
    parse_connection_message,
    PATTERN_CONNECTION_AUTHORIZED,
    PATTERN_DISCONNECTION,
    PATTERN_CONNECTION_RECEIVED,
)
from pgtail_py.connection_event import ConnectionEventType


class TestConnectionPatterns:
    """Tests for regex patterns."""

    def test_pattern_authorized_basic(self) -> None:
        """Test connection authorized pattern with minimal fields."""
        msg = "connection authorized: user=postgres database=mydb"
        match = PATTERN_CONNECTION_AUTHORIZED.search(msg)
        assert match is not None
        assert match.group("user") == "postgres"
        assert match.group("database") == "mydb"
        assert match.group("application") is None

    def test_pattern_authorized_with_application(self) -> None:
        """Test connection authorized pattern with application_name."""
        msg = "connection authorized: user=app_user database=production application_name=rails"
        match = PATTERN_CONNECTION_AUTHORIZED.search(msg)
        assert match is not None
        assert match.group("user") == "app_user"
        assert match.group("database") == "production"
        assert match.group("application") == "rails"

    def test_pattern_disconnection_with_duration(self) -> None:
        """Test disconnection pattern with session time."""
        msg = "disconnection: session time: 0:01:23.456 user=postgres database=mydb host=192.168.1.100 port=54321"
        match = PATTERN_DISCONNECTION.search(msg)
        assert match is not None
        assert match.group("duration") == "0:01:23.456"
        assert match.group("user") == "postgres"
        assert match.group("database") == "mydb"
        assert match.group("host") == "192.168.1.100"
        assert match.group("port") == "54321"

    def test_pattern_disconnection_local(self) -> None:
        """Test disconnection pattern with local socket."""
        msg = "disconnection: session time: 0:00:05.123 user=admin database=test host=[local]"
        match = PATTERN_DISCONNECTION.search(msg)
        assert match is not None
        assert match.group("host") == "[local]"
        assert match.group("port") is None

    def test_pattern_connection_received_with_port(self) -> None:
        """Test connection received pattern with host and port."""
        msg = "connection received: host=10.0.1.5 port=45678"
        match = PATTERN_CONNECTION_RECEIVED.search(msg)
        assert match is not None
        assert match.group("host") == "10.0.1.5"
        assert match.group("port") == "45678"

    def test_pattern_connection_received_local(self) -> None:
        """Test connection received pattern with local socket."""
        msg = "connection received: host=[local]"
        match = PATTERN_CONNECTION_RECEIVED.search(msg)
        assert match is not None
        assert match.group("host") == "[local]"
        assert match.group("port") is None


class TestParseConnectionMessage:
    """Tests for parse_connection_message function."""

    def test_parse_authorized_message(self) -> None:
        """Test parsing connection authorized message."""
        msg = "connection authorized: user=postgres database=mydb"
        result = parse_connection_message(msg)
        assert result is not None
        event_type, data = result
        assert event_type == ConnectionEventType.CONNECT
        assert data["user"] == "postgres"
        assert data["database"] == "mydb"

    def test_parse_disconnection_message(self) -> None:
        """Test parsing disconnection message."""
        msg = "disconnection: session time: 1:23:45.678 user=app_user database=production host=[local]"
        result = parse_connection_message(msg)
        assert result is not None
        event_type, data = result
        assert event_type == ConnectionEventType.DISCONNECT
        assert data["user"] == "app_user"
        assert data["database"] == "production"
        assert data["host"] == "[local]"
        assert data["duration"] == "1:23:45.678"

    def test_parse_connection_received_message_ignored(self) -> None:
        """Test that connection received messages are ignored.

        'connection received' messages occur before authentication and don't
        include user/database info. We only track 'connection authorized'.
        """
        msg = "connection received: host=192.168.1.100 port=54321"
        result = parse_connection_message(msg)
        assert result is None  # Intentionally not tracked

    def test_parse_unrelated_message(self) -> None:
        """Test that unrelated messages return None."""
        msg = "database system is ready to accept connections"
        result = parse_connection_message(msg)
        assert result is None

    def test_parse_empty_message(self) -> None:
        """Test that empty message returns None."""
        result = parse_connection_message("")
        assert result is None

    def test_parse_fatal_too_many_connections(self) -> None:
        """Test parsing FATAL connection limit message."""
        msg = "sorry, too many clients already"
        result = parse_connection_message(msg, is_fatal=True)
        assert result is not None
        event_type, _ = result
        assert event_type == ConnectionEventType.CONNECTION_FAILED

    def test_parse_fatal_auth_failed(self) -> None:
        """Test parsing FATAL auth failure message."""
        msg = "password authentication failed for user \"unknown\""
        result = parse_connection_message(msg, is_fatal=True)
        assert result is not None
        event_type, _ = result
        assert event_type == ConnectionEventType.CONNECTION_FAILED


class TestDurationParsing:
    """Tests for session duration parsing."""

    def test_parse_duration_seconds_only(self) -> None:
        """Test parsing duration with only seconds."""
        msg = "disconnection: session time: 0:00:01.234 user=x database=y host=[local]"
        result = parse_connection_message(msg)
        assert result is not None
        _, data = result
        # Duration string should be preserved for later conversion
        assert data["duration"] == "0:00:01.234"

    def test_parse_duration_hours_minutes_seconds(self) -> None:
        """Test parsing duration with hours, minutes, seconds."""
        msg = "disconnection: session time: 12:34:56.789 user=x database=y host=[local]"
        result = parse_connection_message(msg)
        assert result is not None
        _, data = result
        assert data["duration"] == "12:34:56.789"
