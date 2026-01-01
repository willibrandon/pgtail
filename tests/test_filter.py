"""Tests for pgtail_py.filter module."""

import pytest

from pgtail_py.filter import LogLevel, parse_levels, should_show


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_all_levels_exist(self) -> None:
        """Test that all expected log levels exist."""
        expected = [
            "PANIC", "FATAL", "ERROR", "WARNING", "NOTICE",
            "LOG", "INFO", "DEBUG1", "DEBUG2", "DEBUG3", "DEBUG4", "DEBUG5"
        ]
        for name in expected:
            assert hasattr(LogLevel, name)

    def test_severity_ordering(self) -> None:
        """Test that levels are ordered by severity (lower = more severe)."""
        assert LogLevel.PANIC < LogLevel.FATAL
        assert LogLevel.FATAL < LogLevel.ERROR
        assert LogLevel.ERROR < LogLevel.WARNING
        assert LogLevel.WARNING < LogLevel.NOTICE
        assert LogLevel.NOTICE < LogLevel.LOG
        assert LogLevel.LOG < LogLevel.INFO
        assert LogLevel.INFO < LogLevel.DEBUG1
        assert LogLevel.DEBUG1 < LogLevel.DEBUG2
        assert LogLevel.DEBUG4 < LogLevel.DEBUG5

    def test_from_string_valid(self) -> None:
        """Test parsing valid level names."""
        assert LogLevel.from_string("ERROR") == LogLevel.ERROR
        assert LogLevel.from_string("error") == LogLevel.ERROR
        assert LogLevel.from_string("Error") == LogLevel.ERROR
        assert LogLevel.from_string("WARNING") == LogLevel.WARNING
        assert LogLevel.from_string("DEBUG1") == LogLevel.DEBUG1

    def test_from_string_invalid(self) -> None:
        """Test parsing invalid level names raises ValueError."""
        with pytest.raises(ValueError, match="Unknown log level"):
            LogLevel.from_string("INVALID")

        with pytest.raises(ValueError, match="Unknown log level"):
            LogLevel.from_string("DEBUG6")

    def test_from_string_abbreviations(self) -> None:
        """Test that common abbreviations are recognized."""
        assert LogLevel.from_string("err") == LogLevel.ERROR
        assert LogLevel.from_string("warn") == LogLevel.WARNING
        assert LogLevel.from_string("inf") == LogLevel.INFO
        assert LogLevel.from_string("dbg") == LogLevel.DEBUG1
        assert LogLevel.from_string("debug") == LogLevel.DEBUG1
        assert LogLevel.from_string("fat") == LogLevel.FATAL
        assert LogLevel.from_string("pan") == LogLevel.PANIC
        assert LogLevel.from_string("ntc") == LogLevel.NOTICE

    def test_from_string_single_letter(self) -> None:
        """Test that single-letter shortcuts work."""
        assert LogLevel.from_string("e") == LogLevel.ERROR
        assert LogLevel.from_string("w") == LogLevel.WARNING
        assert LogLevel.from_string("i") == LogLevel.INFO
        assert LogLevel.from_string("l") == LogLevel.LOG
        assert LogLevel.from_string("d") == LogLevel.DEBUG1
        assert LogLevel.from_string("f") == LogLevel.FATAL
        assert LogLevel.from_string("p") == LogLevel.PANIC
        assert LogLevel.from_string("n") == LogLevel.NOTICE

    def test_all_levels(self) -> None:
        """Test that all_levels() returns all log levels."""
        all_levels = LogLevel.all_levels()
        assert len(all_levels) == 12
        assert LogLevel.ERROR in all_levels
        assert LogLevel.DEBUG5 in all_levels

    def test_names(self) -> None:
        """Test that names() returns all level names."""
        names = LogLevel.names()
        assert "ERROR" in names
        assert "WARNING" in names
        assert "DEBUG1" in names
        assert len(names) == 12

    def test_at_or_above_error(self) -> None:
        """Test at_or_above for ERROR level."""
        levels = LogLevel.at_or_above(LogLevel.ERROR)
        assert levels == {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR}

    def test_at_or_above_warning(self) -> None:
        """Test at_or_above for WARNING level."""
        levels = LogLevel.at_or_above(LogLevel.WARNING)
        assert levels == {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR, LogLevel.WARNING}

    def test_at_or_above_panic(self) -> None:
        """Test at_or_above for PANIC (most severe) level."""
        levels = LogLevel.at_or_above(LogLevel.PANIC)
        assert levels == {LogLevel.PANIC}

    def test_at_or_above_debug5(self) -> None:
        """Test at_or_above for DEBUG5 (least severe) level."""
        levels = LogLevel.at_or_above(LogLevel.DEBUG5)
        assert levels == LogLevel.all_levels()


class TestShouldShow:
    """Tests for should_show function."""

    def test_none_shows_all(self) -> None:
        """Test that None active_levels shows all levels."""
        for level in LogLevel:
            assert should_show(level, None) is True

    def test_empty_set_shows_none(self) -> None:
        """Test that empty set shows no levels."""
        for level in LogLevel:
            assert should_show(level, set()) is False

    def test_single_level_filter(self) -> None:
        """Test filtering to a single level."""
        active = {LogLevel.ERROR}
        assert should_show(LogLevel.ERROR, active) is True
        assert should_show(LogLevel.WARNING, active) is False
        assert should_show(LogLevel.LOG, active) is False

    def test_multiple_levels_filter(self) -> None:
        """Test filtering to multiple levels."""
        active = {LogLevel.ERROR, LogLevel.WARNING, LogLevel.FATAL}
        assert should_show(LogLevel.ERROR, active) is True
        assert should_show(LogLevel.WARNING, active) is True
        assert should_show(LogLevel.FATAL, active) is True
        assert should_show(LogLevel.LOG, active) is False
        assert should_show(LogLevel.INFO, active) is False


class TestParseLevels:
    """Tests for parse_levels function."""

    def test_empty_args_returns_none(self) -> None:
        """Test that empty args returns None (show all)."""
        levels, invalid = parse_levels([])
        assert levels is None
        assert invalid == []

    def test_all_keyword(self) -> None:
        """Test that 'ALL' returns None (show all)."""
        levels, invalid = parse_levels(["ALL"])
        assert levels is None
        assert invalid == []

        levels, invalid = parse_levels(["all"])
        assert levels is None
        assert invalid == []

    def test_single_level_exact_match(self) -> None:
        """Test that single level without suffix is exact match."""
        levels, invalid = parse_levels(["ERROR"])
        assert levels == {LogLevel.ERROR}
        assert invalid == []

    def test_level_plus_suffix(self) -> None:
        """Test that + suffix includes level and more severe."""
        levels, invalid = parse_levels(["ERROR+"])
        # ERROR+ should include PANIC, FATAL, ERROR
        assert levels == {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR}
        assert invalid == []

    def test_level_minus_suffix(self) -> None:
        """Test that - suffix includes level and less severe."""
        levels, invalid = parse_levels(["ERROR-"])
        # ERROR- should include ERROR, WARNING, NOTICE, LOG, INFO, DEBUG1-5
        assert levels is not None
        assert LogLevel.ERROR in levels
        assert LogLevel.WARNING in levels
        assert LogLevel.LOG in levels
        assert LogLevel.DEBUG5 in levels
        # Should NOT include FATAL or PANIC
        assert LogLevel.FATAL not in levels
        assert LogLevel.PANIC not in levels
        assert invalid == []

    def test_warning_plus_suffix(self) -> None:
        """Test that WARNING+ includes WARNING, ERROR, FATAL, PANIC."""
        levels, invalid = parse_levels(["WARNING+"])
        assert levels == {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR, LogLevel.WARNING}
        assert invalid == []

    def test_multiple_levels_exact_match(self) -> None:
        """Test that multiple levels returns exact levels specified."""
        levels, invalid = parse_levels(["ERROR", "WARNING", "FATAL"])
        assert levels == {LogLevel.ERROR, LogLevel.WARNING, LogLevel.FATAL}
        assert invalid == []

    def test_mixed_suffix_and_exact(self) -> None:
        """Test combining + suffix with exact match."""
        levels, invalid = parse_levels(["ERROR+", "LOG"])
        # ERROR+ gives PANIC, FATAL, ERROR; plus exact LOG
        assert levels is not None
        assert LogLevel.PANIC in levels
        assert LogLevel.FATAL in levels
        assert LogLevel.ERROR in levels
        assert LogLevel.LOG in levels
        # WARNING should NOT be included (not in ERROR+ or exact LOG)
        assert LogLevel.WARNING not in levels
        assert invalid == []

    def test_case_insensitive(self) -> None:
        """Test that parsing is case insensitive."""
        levels, invalid = parse_levels(["error", "WARNING", "Fatal"])
        # Multiple levels = exact match
        assert levels == {LogLevel.ERROR, LogLevel.WARNING, LogLevel.FATAL}
        assert invalid == []

    def test_abbreviations_with_suffix(self) -> None:
        """Test that abbreviations work with + and - suffixes."""
        # warn+ should give WARNING, ERROR, FATAL, PANIC
        levels, invalid = parse_levels(["warn+"])
        assert levels == {LogLevel.WARNING, LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC}
        assert invalid == []

        # err- should give ERROR and all less severe
        levels, invalid = parse_levels(["err-"])
        assert levels is not None
        assert LogLevel.ERROR in levels
        assert LogLevel.WARNING in levels
        assert LogLevel.DEBUG5 in levels
        assert LogLevel.PANIC not in levels
        assert invalid == []

        # Single letter with suffix: e+ for ERROR+
        levels, invalid = parse_levels(["e+"])
        assert levels == {LogLevel.ERROR, LogLevel.FATAL, LogLevel.PANIC}
        assert invalid == []

        # w for WARNING exact match
        levels, invalid = parse_levels(["w"])
        assert levels == {LogLevel.WARNING}
        assert invalid == []

    def test_invalid_level_name(self) -> None:
        """Test that invalid names are returned in invalid list."""
        levels, invalid = parse_levels(["ERROR", "INVALID", "WARNING"])
        # Two valid levels = exact match (no "and up" expansion)
        assert levels == {LogLevel.ERROR, LogLevel.WARNING}
        assert invalid == ["INVALID"]

    def test_all_invalid_returns_none(self) -> None:
        """Test that all invalid names returns None for levels."""
        levels, invalid = parse_levels(["INVALID1", "INVALID2"])
        assert levels is None
        assert invalid == ["INVALID1", "INVALID2"]
