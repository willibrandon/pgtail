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

    def test_single_level(self) -> None:
        """Test parsing a single level."""
        levels, invalid = parse_levels(["ERROR"])
        assert levels == {LogLevel.ERROR}
        assert invalid == []

    def test_multiple_levels(self) -> None:
        """Test parsing multiple levels."""
        levels, invalid = parse_levels(["ERROR", "WARNING", "FATAL"])
        assert levels == {LogLevel.ERROR, LogLevel.WARNING, LogLevel.FATAL}
        assert invalid == []

    def test_case_insensitive(self) -> None:
        """Test that parsing is case insensitive."""
        levels, invalid = parse_levels(["error", "WARNING", "Fatal"])
        assert levels == {LogLevel.ERROR, LogLevel.WARNING, LogLevel.FATAL}
        assert invalid == []

    def test_invalid_level_name(self) -> None:
        """Test that invalid names are returned in invalid list."""
        levels, invalid = parse_levels(["ERROR", "INVALID", "WARNING"])
        assert levels == {LogLevel.ERROR, LogLevel.WARNING}
        assert invalid == ["INVALID"]

    def test_all_invalid_returns_none(self) -> None:
        """Test that all invalid names returns None for levels."""
        levels, invalid = parse_levels(["INVALID1", "INVALID2"])
        assert levels is None
        assert invalid == ["INVALID1", "INVALID2"]
