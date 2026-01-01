"""Tests for ConnectionEvent dataclass."""

from __future__ import annotations

from datetime import datetime

import pytest

from pgtail_py.connection_event import (
    ConnectionEvent,
    ConnectionEventType,
)
from pgtail_py.parser import LogEntry
from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat


class TestConnectionEventType:
    """Tests for ConnectionEventType enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert ConnectionEventType.CONNECT.value == "connect"
        assert ConnectionEventType.DISCONNECT.value == "disconnect"
        assert ConnectionEventType.CONNECTION_FAILED.value == "failed"

    def test_enum_members(self) -> None:
        """Test that all expected members exist."""
        assert hasattr(ConnectionEventType, "CONNECT")
        assert hasattr(ConnectionEventType, "DISCONNECT")
        assert hasattr(ConnectionEventType, "CONNECTION_FAILED")


class TestConnectionEvent:
    """Tests for ConnectionEvent dataclass."""

    def test_create_basic_event(self) -> None:
        """Test creating a basic connection event."""
        ts = datetime(2024, 1, 15, 14, 30, 45)
        event = ConnectionEvent(
            timestamp=ts,
            event_type=ConnectionEventType.CONNECT,
            pid=12345,
            user="postgres",
            database="mydb",
        )
        assert event.timestamp == ts
        assert event.event_type == ConnectionEventType.CONNECT
        assert event.pid == 12345
        assert event.user == "postgres"
        assert event.database == "mydb"
        assert event.application == "unknown"  # default
        assert event.host is None
        assert event.port is None
        assert event.duration_seconds is None

    def test_create_disconnect_event(self) -> None:
        """Test creating a disconnect event with duration."""
        ts = datetime(2024, 1, 15, 14, 31, 50)
        event = ConnectionEvent(
            timestamp=ts,
            event_type=ConnectionEventType.DISCONNECT,
            pid=12345,
            user="postgres",
            database="mydb",
            duration_seconds=65.123,
        )
        assert event.event_type == ConnectionEventType.DISCONNECT
        assert event.duration_seconds == 65.123

    def test_event_is_frozen(self) -> None:
        """Test that ConnectionEvent is immutable (frozen dataclass)."""
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type=ConnectionEventType.CONNECT,
            pid=1,
        )
        with pytest.raises(AttributeError):
            event.pid = 2  # type: ignore[misc]

    def test_default_application_unknown(self) -> None:
        """Test that application defaults to 'unknown'."""
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type=ConnectionEventType.CONNECT,
            pid=1,
        )
        assert event.application == "unknown"

    def test_explicit_application(self) -> None:
        """Test that explicit application is preserved."""
        event = ConnectionEvent(
            timestamp=datetime.now(),
            event_type=ConnectionEventType.CONNECT,
            pid=1,
            application="rails",
        )
        assert event.application == "rails"


class TestConnectionEventFromLogEntry:
    """Tests for ConnectionEvent.from_log_entry factory method."""

    def test_from_log_entry_authorized(self) -> None:
        """Test creating event from 'connection authorized' log entry."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb application_name=psql",
            raw="2024-01-15 14:30:45 UTC [12345] LOG:  connection authorized: ...",
            pid=12345,
            user_name="postgres",
            database_name="mydb",
            application_name="psql",
        )
        event = ConnectionEvent.from_log_entry(entry)
        assert event is not None
        assert event.event_type == ConnectionEventType.CONNECT
        assert event.pid == 12345
        assert event.user == "postgres"
        assert event.database == "mydb"
        assert event.application == "psql"

    def test_from_log_entry_disconnection(self) -> None:
        """Test creating event from 'disconnection' log entry."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 31, 50),
            level=LogLevel.LOG,
            message="disconnection: session time: 0:01:05.123 user=postgres database=mydb host=[local]",
            raw="2024-01-15 14:31:50 UTC [12345] LOG:  disconnection: ...",
            pid=12345,
            user_name="postgres",
            database_name="mydb",
        )
        event = ConnectionEvent.from_log_entry(entry)
        assert event is not None
        assert event.event_type == ConnectionEventType.DISCONNECT
        assert event.duration_seconds is not None
        assert abs(event.duration_seconds - 65.123) < 0.1

    def test_from_log_entry_non_connection_message(self) -> None:
        """Test that non-connection messages return None."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            level=LogLevel.LOG,
            message="database system is ready to accept connections",
            raw="2024-01-15 14:30:45 UTC [12345] LOG:  database system is ready...",
            pid=12345,
        )
        event = ConnectionEvent.from_log_entry(entry)
        assert event is None

    def test_from_log_entry_fatal_connection_failure(self) -> None:
        """Test creating event from FATAL connection failure."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            level=LogLevel.FATAL,
            message="sorry, too many clients already",
            raw="2024-01-15 14:30:45 UTC [12345] FATAL:  sorry, too many clients already",
            pid=12345,
            user_name="app_user",
        )
        event = ConnectionEvent.from_log_entry(entry)
        assert event is not None
        assert event.event_type == ConnectionEventType.CONNECTION_FAILED
        assert event.user == "app_user"

    def test_from_log_entry_uses_structured_fields(self) -> None:
        """Test that structured fields from CSV/JSON are used when available."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
            format=LogFormat.JSON,
            user_name="structured_user",
            database_name="structured_db",
            application_name="structured_app",
            remote_host="192.168.1.100",
            remote_port=54321,
        )
        event = ConnectionEvent.from_log_entry(entry)
        assert event is not None
        # Structured fields should take precedence
        assert event.user == "structured_user"
        assert event.database == "structured_db"
        assert event.application == "structured_app"
        assert event.host == "192.168.1.100"
        assert event.port == 54321

    def test_from_log_entry_missing_timestamp_uses_now(self) -> None:
        """Test that missing timestamp defaults to now."""
        entry = LogEntry(
            timestamp=None,
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
        )
        before = datetime.now()
        event = ConnectionEvent.from_log_entry(entry)
        after = datetime.now()
        assert event is not None
        assert before <= event.timestamp <= after
