"""Tests for DurationStats percentile calculations with boundary sample sizes."""

from __future__ import annotations

from pgtail_py.slow_query import DurationStats


class TestDurationStatsPercentileBoundaries:
    """Tests for percentile calculation with edge case sample sizes."""

    def test_empty_stats_returns_zero(self) -> None:
        """Empty stats returns 0 for all percentiles."""
        stats = DurationStats()
        assert stats.p50 == 0.0
        assert stats.p95 == 0.0
        assert stats.p99 == 0.0
        assert stats.average == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0

    def test_single_sample_returns_that_value(self) -> None:
        """Single sample returns that value for all percentiles."""
        stats = DurationStats()
        stats.add(100.0)

        assert stats.p50 == 100.0
        assert stats.p95 == 100.0
        assert stats.p99 == 100.0
        assert stats.average == 100.0
        assert stats.min == 100.0
        assert stats.max == 100.0

    def test_two_samples_median(self) -> None:
        """Two samples returns correct median."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)

        # Median of [100, 200] should be 150
        assert stats.p50 == 150.0
        # p95 should be close to 200
        assert stats.p95 > 190.0
        # p99 should be very close to 200
        assert stats.p99 > 198.0

    def test_three_samples(self) -> None:
        """Three samples returns correct percentiles."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)
        stats.add(300.0)

        # Median should be 200 (middle value)
        assert stats.p50 == 200.0
        # Average should be 200
        assert stats.average == 200.0

    def test_ten_samples(self) -> None:
        """Ten samples returns correct percentiles."""
        stats = DurationStats()
        for i in range(1, 11):
            stats.add(float(i * 10))  # 10, 20, 30, ..., 100

        # Median should be between 50 and 60
        assert 50.0 <= stats.p50 <= 60.0
        # p95 should be close to 100
        assert stats.p95 > 90.0
        # p99 should be very close to 100
        assert stats.p99 > 95.0

    def test_hundred_samples(self) -> None:
        """Hundred samples returns correct percentiles."""
        stats = DurationStats()
        for i in range(1, 101):
            stats.add(float(i))  # 1, 2, 3, ..., 100

        # Median should be around 50
        assert 49.0 <= stats.p50 <= 51.0
        # p95 should be around 95
        assert 94.0 <= stats.p95 <= 96.0
        # p99 should be around 99
        assert 98.0 <= stats.p99 <= 100.0

    def test_ninety_nine_samples(self) -> None:
        """99 samples (edge case before 100) returns correct percentiles."""
        stats = DurationStats()
        for i in range(1, 100):
            stats.add(float(i))  # 1, 2, 3, ..., 99

        assert stats.count == 99
        # p50 should be around 50
        assert 49.0 <= stats.p50 <= 51.0
        # p95 should be around 94
        assert 93.0 <= stats.p95 <= 95.0

    def test_fifty_samples(self) -> None:
        """50 samples returns correct percentiles."""
        stats = DurationStats()
        for i in range(1, 51):
            stats.add(float(i))  # 1, 2, 3, ..., 50

        assert stats.count == 50
        # Median should be around 25
        assert 24.0 <= stats.p50 <= 26.0


class TestDurationStatsCaching:
    """Tests for sorted cache behavior."""

    def test_cache_invalidated_on_add(self) -> None:
        """Cache is invalidated when new sample is added."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)

        # Access percentile to populate cache
        _ = stats.p50

        # Add new sample (should invalidate cache)
        stats.add(300.0)

        # Verify percentile is recalculated correctly
        assert stats.p50 == 200.0  # Median of [100, 200, 300]

    def test_cache_invalidated_on_clear(self) -> None:
        """Cache is invalidated when stats are cleared."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)

        # Access percentile to populate cache
        _ = stats.p50

        # Clear stats (should invalidate cache)
        stats.clear()

        # Verify percentiles return 0 for empty stats
        assert stats.p50 == 0.0
        assert stats.p95 == 0.0

    def test_repeated_access_uses_cache(self) -> None:
        """Repeated percentile access uses cached sorted values."""
        stats = DurationStats()
        for i in range(100):
            stats.add(float(i))

        # Multiple accesses should return same values
        p50_first = stats.p50
        p95_first = stats.p95
        p99_first = stats.p99

        p50_second = stats.p50
        p95_second = stats.p95
        p99_second = stats.p99

        assert p50_first == p50_second
        assert p95_first == p95_second
        assert p99_first == p99_second


class TestDurationStatsFormatSummary:
    """Tests for format_summary output."""

    def test_format_summary_empty(self) -> None:
        """Format summary handles empty stats."""
        stats = DurationStats()
        summary = stats.format_summary()
        assert "Queries:  0" in summary
        assert "Average:  0.0ms" in summary

    def test_format_summary_with_data(self) -> None:
        """Format summary shows correct data."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)
        stats.add(300.0)

        summary = stats.format_summary()
        assert "Queries:  3" in summary
        assert "Average:  200.0ms" in summary
        assert "max:" in summary
