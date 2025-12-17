"""Tests for error trend visualization."""

from datetime import datetime, timedelta

import pytest

from pgtail_py.error_stats import ErrorEvent
from pgtail_py.error_trend import SPARK_CHARS, bucket_events, sparkline
from pgtail_py.filter import LogLevel


# Test fixtures
@pytest.fixture
def sample_events() -> list[ErrorEvent]:
    """Create sample error events spread over time."""
    now = datetime.now()
    return [
        ErrorEvent(
            timestamp=now - timedelta(minutes=5),
            level=LogLevel.ERROR,
            sql_state="23505",
            message="error 1",
            pid=1000,
            database="db1",
            user="user1",
        ),
        ErrorEvent(
            timestamp=now - timedelta(minutes=5),
            level=LogLevel.ERROR,
            sql_state="23505",
            message="error 2",
            pid=1000,
            database="db1",
            user="user1",
        ),
        ErrorEvent(
            timestamp=now - timedelta(minutes=10),
            level=LogLevel.ERROR,
            sql_state="42601",
            message="error 3",
            pid=1000,
            database="db1",
            user="user1",
        ),
    ]


class TestSparkChars:
    """Tests for SPARK_CHARS constant."""

    def test_spark_chars_has_8_characters(self) -> None:
        assert len(SPARK_CHARS) == 8

    def test_spark_chars_are_unicode_blocks(self) -> None:
        assert SPARK_CHARS == "▁▂▃▄▅▆▇█"

    def test_spark_chars_first_is_lowest(self) -> None:
        assert SPARK_CHARS[0] == "▁"

    def test_spark_chars_last_is_highest(self) -> None:
        assert SPARK_CHARS[-1] == "█"


class TestSparkline:
    """Tests for sparkline() function."""

    def test_empty_list_returns_empty_string(self) -> None:
        assert sparkline([]) == ""

    def test_single_value_returns_max_char(self) -> None:
        result = sparkline([5])
        assert result == "█"

    def test_all_zeros_returns_lowest_chars(self) -> None:
        result = sparkline([0, 0, 0])
        assert result == "▁▁▁"

    def test_all_same_values_returns_max_chars(self) -> None:
        result = sparkline([5, 5, 5])
        assert result == "███"

    def test_increasing_values(self) -> None:
        result = sparkline([0, 1, 2, 3, 4, 5, 6, 7])
        # Each value maps to increasing height
        assert len(result) == 8
        assert result[0] == "▁"  # 0 maps to lowest
        assert result[-1] == "█"  # 7 maps to highest

    def test_max_value_gets_highest_char(self) -> None:
        result = sparkline([1, 10, 1])
        assert result[1] == "█"  # max value gets highest char

    def test_min_value_gets_lowest_char(self) -> None:
        result = sparkline([0, 10, 0])
        assert result[0] == "▁"
        assert result[2] == "▁"

    def test_proportional_scaling(self) -> None:
        # 0, 50, 100 should give low, mid, high
        result = sparkline([0, 50, 100])
        assert result[0] == "▁"  # 0 -> lowest
        assert result[2] == "█"  # 100 -> highest
        # 50 should be somewhere in the middle
        assert result[1] in "▃▄▅"

    def test_length_matches_input(self) -> None:
        for length in [1, 5, 10, 60]:
            values = [i % 10 for i in range(length)]
            result = sparkline(values)
            assert len(result) == length


class TestBucketEvents:
    """Tests for bucket_events() function."""

    def test_empty_events_returns_zeros(self) -> None:
        result = bucket_events([], minutes=10)
        assert result == [0] * 10

    def test_returns_correct_number_of_buckets(self) -> None:
        result = bucket_events([], minutes=60)
        assert len(result) == 60

        result = bucket_events([], minutes=30)
        assert len(result) == 30

    def test_recent_event_in_last_bucket(self) -> None:
        now = datetime.now()
        events = [
            ErrorEvent(
                timestamp=now - timedelta(seconds=30),  # Less than 1 minute ago
                level=LogLevel.ERROR,
                sql_state="23505",
                message="recent",
                pid=1000,
                database=None,
                user=None,
            )
        ]
        result = bucket_events(events, minutes=10)
        # Most recent bucket is last
        assert result[-1] == 1
        assert sum(result[:-1]) == 0

    def test_older_event_in_earlier_bucket(self) -> None:
        now = datetime.now()
        events = [
            ErrorEvent(
                timestamp=now - timedelta(minutes=5, seconds=30),
                level=LogLevel.ERROR,
                sql_state="23505",
                message="older",
                pid=1000,
                database=None,
                user=None,
            )
        ]
        result = bucket_events(events, minutes=10)
        # 5 minutes ago should be in bucket index 4 (from the end)
        # buckets are oldest first, so index 10-1-5 = 4
        assert result[4] == 1

    def test_events_outside_window_ignored(self) -> None:
        now = datetime.now()
        events = [
            ErrorEvent(
                timestamp=now - timedelta(minutes=120),  # 2 hours ago
                level=LogLevel.ERROR,
                sql_state="23505",
                message="old",
                pid=1000,
                database=None,
                user=None,
            )
        ]
        result = bucket_events(events, minutes=60)
        assert sum(result) == 0  # Event is outside 60-minute window

    def test_multiple_events_same_minute(self, sample_events: list[ErrorEvent]) -> None:
        # sample_events has 2 events at 5 minutes ago
        result = bucket_events(sample_events, minutes=60)
        total = sum(result)
        assert total == 3  # All 3 events should be counted

    def test_buckets_ordered_oldest_first(self) -> None:
        now = datetime.now()
        events = [
            ErrorEvent(
                timestamp=now - timedelta(minutes=1),
                level=LogLevel.ERROR,
                sql_state="23505",
                message="recent",
                pid=1000,
                database=None,
                user=None,
            ),
            ErrorEvent(
                timestamp=now - timedelta(minutes=9),
                level=LogLevel.ERROR,
                sql_state="23505",
                message="older",
                pid=1000,
                database=None,
                user=None,
            ),
        ]
        result = bucket_events(events, minutes=10)
        # Oldest (9 min ago) should be earlier in list
        # Recent (1 min ago) should be later
        older_idx = result.index(1)  # First occurrence (older event)
        # Find second occurrence
        recent_idx = len(result) - 1 - result[::-1].index(1)
        assert older_idx < recent_idx


class TestSparklineIntegration:
    """Integration tests for sparkline with bucket_events."""

    def test_sparkline_from_buckets(self, sample_events: list[ErrorEvent]) -> None:
        buckets = bucket_events(sample_events, minutes=60)
        result = sparkline(buckets)
        assert len(result) == 60
        # Should have some non-minimum values where events occurred
        assert "█" in result or "▇" in result or "▆" in result

    def test_empty_events_produces_flat_sparkline(self) -> None:
        buckets = bucket_events([], minutes=10)
        result = sparkline(buckets)
        # All zeros should produce all lowest chars
        assert result == "▁" * 10
