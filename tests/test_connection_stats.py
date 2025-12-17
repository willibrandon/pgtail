"""Tests for ConnectionStats aggregator."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from pgtail_py.connection_stats import ConnectionStats
from pgtail_py.connection_event import ConnectionEvent, ConnectionEventType
from pgtail_py.parser import LogEntry
from pgtail_py.filter import LogLevel


class TestConnectionStatsBasics:
    """Tests for basic ConnectionStats functionality."""

    def test_new_stats_is_empty(self) -> None:
        """Test that new stats object is empty."""
        stats = ConnectionStats()
        assert stats.is_empty()
        assert stats.active_count() == 0
        assert stats.connect_count == 0
        assert stats.disconnect_count == 0

    def test_clear_resets_all(self) -> None:
        """Test that clear() resets all statistics."""
        stats = ConnectionStats()
        # Add some events
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
        )
        stats.add(entry)
        assert not stats.is_empty()

        # Clear and verify
        stats.clear()
        assert stats.is_empty()
        assert stats.active_count() == 0
        assert stats.connect_count == 0
        assert stats.disconnect_count == 0

    def test_is_empty_after_events(self) -> None:
        """Test that is_empty() returns False after adding events."""
        stats = ConnectionStats()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
        )
        stats.add(entry)
        assert not stats.is_empty()


class TestConnectionStatsAdd:
    """Tests for ConnectionStats.add() method."""

    def test_add_connection_increments_count(self) -> None:
        """Test that adding a connection increments connect_count."""
        stats = ConnectionStats()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
        )
        result = stats.add(entry)
        assert result is True
        assert stats.connect_count == 1
        assert stats.active_count() == 1

    def test_add_disconnection_increments_count(self) -> None:
        """Test that adding a disconnection increments disconnect_count."""
        stats = ConnectionStats()
        # First add a connection
        connect_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=12345,
        )
        stats.add(connect_entry)

        # Then add disconnection
        disconnect_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="disconnection: session time: 0:01:00.000 user=postgres database=mydb host=[local]",
            raw="...",
            pid=12345,
        )
        result = stats.add(disconnect_entry)
        assert result is True
        assert stats.disconnect_count == 1
        assert stats.active_count() == 0

    def test_add_non_connection_returns_false(self) -> None:
        """Test that non-connection messages return False."""
        stats = ConnectionStats()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="database system is ready to accept connections",
            raw="...",
            pid=12345,
        )
        result = stats.add(entry)
        assert result is False
        assert stats.is_empty()

    def test_add_tracks_by_pid(self) -> None:
        """Test that connections are tracked by PID."""
        stats = ConnectionStats()
        # Add two connections with different PIDs
        for pid in [100, 200]:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.LOG,
                message="connection authorized: user=postgres database=mydb",
                raw="...",
                pid=pid,
            )
            stats.add(entry)

        assert stats.active_count() == 2

        # Disconnect one
        disconnect_entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="disconnection: session time: 0:01:00.000 user=postgres database=mydb host=[local]",
            raw="...",
            pid=100,
        )
        stats.add(disconnect_entry)
        assert stats.active_count() == 1


class TestConnectionStatsAggregations:
    """Tests for ConnectionStats aggregation methods."""

    @pytest.fixture
    def stats_with_data(self) -> ConnectionStats:
        """Create stats with test data."""
        stats = ConnectionStats()
        # Add connections for different users/databases/apps
        test_data = [
            (100, "postgres", "mydb", "psql"),
            (101, "postgres", "mydb", "psql"),
            (102, "app_user", "production", "rails"),
            (103, "app_user", "production", "rails"),
            (104, "app_user", "production", "sidekiq"),
            (105, "readonly", "analytics", "metabase"),
        ]
        for pid, user, db, app in test_data:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.LOG,
                message=f"connection authorized: user={user} database={db} application_name={app}",
                raw="...",
                pid=pid,
                user_name=user,
                database_name=db,
                application_name=app,
            )
            stats.add(entry)
        return stats

    def test_get_by_database(self, stats_with_data: ConnectionStats) -> None:
        """Test aggregation by database."""
        by_db = stats_with_data.get_by_database()
        assert by_db == {
            "mydb": 2,
            "production": 3,
            "analytics": 1,
        }

    def test_get_by_user(self, stats_with_data: ConnectionStats) -> None:
        """Test aggregation by user."""
        by_user = stats_with_data.get_by_user()
        assert by_user == {
            "postgres": 2,
            "app_user": 3,
            "readonly": 1,
        }

    def test_get_by_application(self, stats_with_data: ConnectionStats) -> None:
        """Test aggregation by application."""
        by_app = stats_with_data.get_by_application()
        assert by_app == {
            "psql": 2,
            "rails": 2,
            "sidekiq": 1,
            "metabase": 1,
        }

    def test_get_by_host(self) -> None:
        """Test aggregation by host."""
        stats = ConnectionStats()
        # Add connections from different hosts
        test_data = [
            (100, "192.168.1.100"),
            (101, "192.168.1.100"),
            (102, "10.0.1.5"),
            (103, "[local]"),
        ]
        for pid, host in test_data:
            entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.LOG,
                message=f"connection authorized: user=postgres database=mydb",
                raw="...",
                pid=pid,
                remote_host=host,
            )
            stats.add(entry)

        by_host = stats.get_by_host()
        assert by_host == {
            "192.168.1.100": 2,
            "10.0.1.5": 1,
            "[local]": 1,
        }


class TestConnectionStatsHistory:
    """Tests for ConnectionStats history and trend methods."""

    def test_get_events_since(self) -> None:
        """Test get_events_since() time filtering."""
        stats = ConnectionStats()
        now = datetime.now()

        # Add events at different times
        for i, minutes_ago in enumerate([10, 5, 2, 1]):
            ts = now - timedelta(minutes=minutes_ago)
            entry = LogEntry(
                timestamp=ts,
                level=LogLevel.LOG,
                message="connection authorized: user=postgres database=mydb",
                raw="...",
                pid=100 + i,
            )
            stats.add(entry)

        # Get events from last 3 minutes
        since_time = now - timedelta(minutes=3)
        events = stats.get_events_since(since_time)
        assert len(events) == 2  # 2 min ago and 1 min ago

    def test_get_trend_buckets(self) -> None:
        """Test get_trend_buckets() returns (connects, disconnects) per bucket."""
        stats = ConnectionStats()
        now = datetime.now()

        # Add connections at different times (15-min buckets)
        # Bucket 1 (45-30 min ago): 2 connects
        for i in range(2):
            entry = LogEntry(
                timestamp=now - timedelta(minutes=40),
                level=LogLevel.LOG,
                message="connection authorized: user=postgres database=mydb",
                raw="...",
                pid=100 + i,
            )
            stats.add(entry)

        # Bucket 2 (30-15 min ago): 1 connect, 1 disconnect
        entry = LogEntry(
            timestamp=now - timedelta(minutes=20),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=200,
        )
        stats.add(entry)
        entry = LogEntry(
            timestamp=now - timedelta(minutes=20),
            level=LogLevel.LOG,
            message="disconnection: session time: 0:01:00.000 user=postgres database=mydb host=[local]",
            raw="...",
            pid=100,
        )
        stats.add(entry)

        # Bucket 3 (15-0 min ago): 1 connect
        entry = LogEntry(
            timestamp=now - timedelta(minutes=5),
            level=LogLevel.LOG,
            message="connection authorized: user=postgres database=mydb",
            raw="...",
            pid=300,
        )
        stats.add(entry)

        buckets = stats.get_trend_buckets(minutes=60)
        # Should have 4 buckets (60 min / 15 min per bucket)
        assert len(buckets) == 4

        # Each bucket is (connects, disconnects)
        # Verify totals match
        total_connects = sum(b[0] for b in buckets)
        total_disconnects = sum(b[1] for b in buckets)
        assert total_connects == 4  # 2 + 1 + 1
        assert total_disconnects == 1


class TestConnectionStatsEdgeCases:
    """Tests for edge cases in ConnectionStats."""

    def test_disconnect_without_matching_connect(self) -> None:
        """Test handling disconnect for unknown PID."""
        stats = ConnectionStats()
        # Disconnect without prior connect (standalone event)
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.LOG,
            message="disconnection: session time: 0:01:00.000 user=postgres database=mydb host=[local]",
            raw="...",
            pid=12345,
        )
        result = stats.add(entry)
        # Should still track the event
        assert result is True
        assert stats.disconnect_count == 1
        # But active count shouldn't go negative
        assert stats.active_count() == 0

    def test_maxlen_enforcement(self) -> None:
        """Test that events deque respects maxlen."""
        stats = ConnectionStats()
        # Add more events than maxlen (10,000)
        # We'll just verify the deque has maxlen set
        # Adding 10,001 events would be slow, so check the structure
        assert stats._events.maxlen == 10000

    def test_connection_failed_tracking(self) -> None:
        """Test tracking of connection failures."""
        stats = ConnectionStats()
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.FATAL,
            message="sorry, too many clients already",
            raw="...",
            pid=12345,
        )
        result = stats.add(entry)
        # Should track the failure
        assert result is True
        # But shouldn't count as active connection
        assert stats.active_count() == 0
