"""Connection statistics tracking for PostgreSQL logs.

Provides session-scoped aggregation of connection events, including
active connection counts, breakdowns by user/database/application/host,
and trend analysis.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pgtail_py.connection_event import ConnectionEvent, ConnectionEventType

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


@dataclass
class ConnectionStats:
    """Session-scoped connection statistics aggregator.

    Tracks connection and disconnection events, maintaining:
    - Event history (up to 10,000 events)
    - Active connections by PID
    - Aggregate counts

    Follows the ErrorStats pattern for consistency.

    Attributes:
        _events: Deque of all events (max 10,000 for memory bounds).
        _active: Dict mapping PID to active ConnectionEvent.
        session_start: When tracking started.
        connect_count: Total connections seen.
        disconnect_count: Total disconnections seen.
    """

    _events: deque[ConnectionEvent] = field(
        default_factory=lambda: deque(maxlen=10000)
    )
    _active: dict[int, ConnectionEvent] = field(default_factory=dict)
    session_start: datetime = field(default_factory=datetime.now)
    connect_count: int = 0
    disconnect_count: int = 0

    def add(self, entry: LogEntry) -> bool:
        """Process a LogEntry and track if it's a connection event.

        Args:
            entry: Parsed log entry to process.

        Returns:
            True if the entry was a connection event, False otherwise.
        """
        event = ConnectionEvent.from_log_entry(entry)
        if event is None:
            return False

        # Add to event history
        self._events.append(event)

        # Update counters and active connections based on event type
        if event.event_type == ConnectionEventType.CONNECT:
            self.connect_count += 1
            # Track as active connection if we have a PID
            if event.pid is not None:
                self._active[event.pid] = event

        elif event.event_type == ConnectionEventType.DISCONNECT:
            self.disconnect_count += 1
            # Remove from active connections if tracked
            if event.pid is not None and event.pid in self._active:
                del self._active[event.pid]

        # CONNECTION_FAILED events are tracked but don't affect active count

        return True

    def clear(self) -> None:
        """Reset all statistics."""
        self._events.clear()
        self._active.clear()
        self.connect_count = 0
        self.disconnect_count = 0
        self.session_start = datetime.now()

    def is_empty(self) -> bool:
        """Check if any events have been tracked.

        Returns:
            True if no events recorded, False otherwise.
        """
        return len(self._events) == 0

    def active_count(self) -> int:
        """Get the number of currently active connections.

        Returns:
            Count of connections without matching disconnections.
        """
        return len(self._active)

    def get_by_database(self) -> dict[str, int]:
        """Get active connection counts grouped by database.

        Returns:
            Dict mapping database name to connection count.
        """
        counts: dict[str, int] = defaultdict(int)
        for event in self._active.values():
            db = event.database or "unknown"
            counts[db] += 1
        return dict(counts)

    def get_by_user(self) -> dict[str, int]:
        """Get active connection counts grouped by user.

        Returns:
            Dict mapping user name to connection count.
        """
        counts: dict[str, int] = defaultdict(int)
        for event in self._active.values():
            user = event.user or "unknown"
            counts[user] += 1
        return dict(counts)

    def get_by_application(self) -> dict[str, int]:
        """Get active connection counts grouped by application.

        Returns:
            Dict mapping application name to connection count.
        """
        counts: dict[str, int] = defaultdict(int)
        for event in self._active.values():
            app = event.application or "unknown"
            counts[app] += 1
        return dict(counts)

    def get_by_host(self) -> dict[str, int]:
        """Get active connection counts grouped by host.

        Returns:
            Dict mapping host address to connection count.
        """
        counts: dict[str, int] = defaultdict(int)
        for event in self._active.values():
            host = event.host or "unknown"
            counts[host] += 1
        return dict(counts)

    def get_events_since(self, since: datetime) -> list[ConnectionEvent]:
        """Get events after a specific timestamp.

        Args:
            since: Only return events after this time.

        Returns:
            List of events in chronological order.
        """
        return [e for e in self._events if e.timestamp >= since]

    def get_trend_buckets(
        self, minutes: int = 60, bucket_size: int = 15
    ) -> list[tuple[int, int]]:
        """Get connection counts per time bucket for trend visualization.

        Args:
            minutes: Total time window in minutes (default 60).
            bucket_size: Size of each bucket in minutes (default 15).

        Returns:
            List of (connects, disconnects) tuples per bucket, oldest first.
        """
        now = datetime.now()
        num_buckets = max(1, minutes // bucket_size)
        buckets: list[tuple[int, int]] = [(0, 0) for _ in range(num_buckets)]

        # Calculate bucket boundaries
        for event in self._events:
            # How many minutes ago was this event?
            delta = now - event.timestamp
            minutes_ago = delta.total_seconds() / 60

            if minutes_ago < 0 or minutes_ago >= minutes:
                continue

            # Which bucket? (0 = oldest, num_buckets-1 = newest)
            bucket_idx = num_buckets - 1 - int(minutes_ago // bucket_size)
            bucket_idx = max(0, min(num_buckets - 1, bucket_idx))

            connects, disconnects = buckets[bucket_idx]
            if event.event_type == ConnectionEventType.CONNECT:
                buckets[bucket_idx] = (connects + 1, disconnects)
            elif event.event_type == ConnectionEventType.DISCONNECT:
                buckets[bucket_idx] = (connects, disconnects + 1)

        return buckets
