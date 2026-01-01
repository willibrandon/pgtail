"""Tests for slow query detection and highlighting."""

from pgtail_py.slow_query import (
    DEFAULT_CRITICAL_MS,
    DEFAULT_SLOW_MS,
    DEFAULT_WARNING_MS,
    DurationStats,
    SlowQueryConfig,
    SlowQueryLevel,
    extract_duration,
    validate_thresholds,
)


class TestExtractDuration:
    """Tests for extract_duration() function."""

    # T008: Unit test for extract_duration() with ms format
    def test_extract_duration_ms_format(self) -> None:
        """Should extract duration in milliseconds format."""
        assert extract_duration("duration: 234.567 ms") == 234.567
        assert extract_duration("duration: 0.123 ms") == 0.123
        assert extract_duration("duration: 1000.0 ms") == 1000.0

    def test_extract_duration_ms_in_log_line(self) -> None:
        """Should extract duration from full PostgreSQL log line."""
        log_line = "2024-01-15 10:30:45.123 UTC [12345] LOG:  duration: 234.567 ms  statement: SELECT * FROM users"
        assert extract_duration(log_line) == 234.567

    def test_extract_duration_ms_case_insensitive(self) -> None:
        """Should handle case variations in unit."""
        assert extract_duration("duration: 100.0 MS") == 100.0
        assert extract_duration("duration: 100.0 Ms") == 100.0

    # T009: Unit test for extract_duration() with seconds format
    def test_extract_duration_seconds_format(self) -> None:
        """Should extract duration in seconds format and convert to ms."""
        assert extract_duration("duration: 1.234 s") == 1234.0
        assert extract_duration("duration: 0.5 s") == 500.0
        assert extract_duration("duration: 2.0 s") == 2000.0

    def test_extract_duration_seconds_case_insensitive(self) -> None:
        """Should handle case variations in seconds unit."""
        assert extract_duration("duration: 1.0 S") == 1000.0

    # T010: Unit test for extract_duration() with malformed input
    def test_extract_duration_no_match(self) -> None:
        """Should return None when no duration pattern found."""
        assert extract_duration("LOG: database system is ready") is None
        assert extract_duration("") is None
        assert extract_duration("some random text") is None

    def test_extract_duration_malformed_value(self) -> None:
        """Should return None for malformed duration values."""
        # No unit
        assert extract_duration("duration: 100") is None
        # Invalid unit
        assert extract_duration("duration: 100 minutes") is None

    def test_extract_duration_integer_value(self) -> None:
        """Should handle integer values (no decimal)."""
        assert extract_duration("duration: 100 ms") == 100.0
        assert extract_duration("duration: 1 s") == 1000.0

    def test_extract_duration_zero_value(self) -> None:
        """Should handle zero duration."""
        assert extract_duration("duration: 0 ms") == 0.0
        assert extract_duration("duration: 0.0 ms") == 0.0

    def test_extract_duration_first_match_only(self) -> None:
        """Should return first duration when multiple patterns exist."""
        # T035: Edge case - multiple duration patterns in single line
        text = "duration: 100 ms followed by duration: 200 ms"
        assert extract_duration(text) == 100.0

    def test_extract_duration_negative_value(self) -> None:
        """Should return None for negative duration values."""
        # T036: Edge case - negative duration values
        # Note: The regex doesn't match negative values (no minus sign in pattern)
        # This test documents the expected behavior
        assert extract_duration("duration: -100 ms") is None


class TestSlowQueryConfigGetLevel:
    """Tests for SlowQueryConfig.get_level() method."""

    # T011: Unit test for SlowQueryConfig.get_level() threshold logic
    def test_get_level_below_warning(self) -> None:
        """Should return None when duration is below warning threshold."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=100.0,
            slow_ms=500.0,
            critical_ms=1000.0,
        )
        assert config.get_level(50.0) is None
        assert config.get_level(99.9) is None
        assert config.get_level(0.0) is None

    def test_get_level_warning(self) -> None:
        """Should return WARNING when duration exceeds warning but not slow threshold."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=100.0,
            slow_ms=500.0,
            critical_ms=1000.0,
        )
        assert config.get_level(100.1) == SlowQueryLevel.WARNING
        assert config.get_level(234.567) == SlowQueryLevel.WARNING
        assert config.get_level(499.9) == SlowQueryLevel.WARNING

    def test_get_level_slow(self) -> None:
        """Should return SLOW when duration exceeds slow but not critical threshold."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=100.0,
            slow_ms=500.0,
            critical_ms=1000.0,
        )
        assert config.get_level(500.1) == SlowQueryLevel.SLOW
        assert config.get_level(750.0) == SlowQueryLevel.SLOW
        assert config.get_level(999.9) == SlowQueryLevel.SLOW

    def test_get_level_critical(self) -> None:
        """Should return CRITICAL when duration exceeds critical threshold."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=100.0,
            slow_ms=500.0,
            critical_ms=1000.0,
        )
        assert config.get_level(1000.1) == SlowQueryLevel.CRITICAL
        assert config.get_level(1234.567) == SlowQueryLevel.CRITICAL
        assert config.get_level(5000.0) == SlowQueryLevel.CRITICAL

    def test_get_level_boundary_values(self) -> None:
        """Should handle exact boundary values correctly."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=100.0,
            slow_ms=500.0,
            critical_ms=1000.0,
        )
        # Exact boundaries should NOT trigger the level (must exceed, not equal)
        assert config.get_level(100.0) is None
        assert config.get_level(500.0) == SlowQueryLevel.WARNING
        assert config.get_level(1000.0) == SlowQueryLevel.SLOW

    def test_get_level_default_thresholds(self) -> None:
        """Should use default thresholds when not specified."""
        config = SlowQueryConfig(enabled=True)
        assert config.warning_ms == DEFAULT_WARNING_MS
        assert config.slow_ms == DEFAULT_SLOW_MS
        assert config.critical_ms == DEFAULT_CRITICAL_MS


class TestValidateThresholds:
    """Tests for validate_thresholds() function."""

    # T017: Unit test for threshold validation (positive numbers, ascending order)
    def test_validate_thresholds_valid(self) -> None:
        """Should return None for valid thresholds."""
        assert validate_thresholds(100.0, 500.0, 1000.0) is None
        assert validate_thresholds(1.0, 10.0, 100.0) is None
        assert validate_thresholds(0.1, 0.5, 1.0) is None

    def test_validate_thresholds_negative(self) -> None:
        """Should reject negative thresholds."""
        assert validate_thresholds(-1.0, 500.0, 1000.0) is not None
        assert validate_thresholds(100.0, -500.0, 1000.0) is not None
        assert validate_thresholds(100.0, 500.0, -1000.0) is not None

    def test_validate_thresholds_zero(self) -> None:
        """Should reject zero thresholds."""
        assert validate_thresholds(0.0, 500.0, 1000.0) is not None
        assert validate_thresholds(100.0, 0.0, 1000.0) is not None
        assert validate_thresholds(100.0, 500.0, 0.0) is not None

    def test_validate_thresholds_wrong_order(self) -> None:
        """Should reject thresholds not in ascending order."""
        assert validate_thresholds(500.0, 100.0, 1000.0) is not None
        assert validate_thresholds(100.0, 1000.0, 500.0) is not None
        assert validate_thresholds(1000.0, 500.0, 100.0) is not None

    def test_validate_thresholds_equal_values(self) -> None:
        """Should reject equal threshold values."""
        assert validate_thresholds(100.0, 100.0, 1000.0) is not None
        assert validate_thresholds(100.0, 500.0, 500.0) is not None
        assert validate_thresholds(100.0, 100.0, 100.0) is not None


class TestSlowQueryConfigFormatThresholds:
    """Tests for SlowQueryConfig.format_thresholds() method."""

    # T018: Unit test for SlowQueryConfig.format_thresholds() output
    def test_format_thresholds_default(self) -> None:
        """Should format default thresholds correctly."""
        config = SlowQueryConfig(enabled=True)
        output = config.format_thresholds()
        assert "Warning (yellow):" in output
        assert "> 100ms" in output
        assert "Slow (yellow bold):" in output
        assert "> 500ms" in output
        assert "Critical (red bold):" in output
        assert "> 1000ms" in output

    def test_format_thresholds_custom(self) -> None:
        """Should format custom thresholds correctly."""
        config = SlowQueryConfig(
            enabled=True,
            warning_ms=50.0,
            slow_ms=200.0,
            critical_ms=500.0,
        )
        output = config.format_thresholds()
        assert "> 50ms" in output
        assert "> 200ms" in output
        assert "> 500ms" in output


class TestDurationStats:
    """Tests for DurationStats class."""

    def test_empty_stats(self) -> None:
        """Should handle empty stats correctly."""
        stats = DurationStats()
        assert stats.is_empty()
        assert stats.count == 0
        assert stats.average == 0.0
        assert stats.min == 0.0
        assert stats.max == 0.0

    def test_add_single_sample(self) -> None:
        """Should handle single sample correctly."""
        stats = DurationStats()
        stats.add(100.0)
        assert not stats.is_empty()
        assert stats.count == 1
        assert stats.average == 100.0
        assert stats.min == 100.0
        assert stats.max == 100.0

    def test_add_multiple_samples(self) -> None:
        """Should calculate stats for multiple samples."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)
        stats.add(300.0)
        assert stats.count == 3
        assert stats.average == 200.0
        assert stats.min == 100.0
        assert stats.max == 300.0

    def test_clear_stats(self) -> None:
        """Should reset stats on clear."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)
        stats.clear()
        assert stats.is_empty()
        assert stats.count == 0

    def test_percentiles_single_sample(self) -> None:
        """Should return sample value for percentiles with single sample."""
        stats = DurationStats()
        stats.add(100.0)
        assert stats.p50 == 100.0
        assert stats.p95 == 100.0
        assert stats.p99 == 100.0

    def test_format_summary(self) -> None:
        """Should format summary string."""
        stats = DurationStats()
        stats.add(100.0)
        stats.add(200.0)
        summary = stats.format_summary()
        assert "Query Duration Statistics" in summary
        assert "Queries:" in summary
        assert "Average:" in summary
        assert "p50:" in summary
        assert "p95:" in summary
        assert "p99:" in summary
        assert "max:" in summary
