"""Tests for pgtail_py.tail_rich module."""

from __future__ import annotations

from datetime import datetime

import pytest
from rich.text import Text

from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry
from pgtail_py.tail_rich import (
    LEVEL_STYLES,
    format_entry_as_rich,
    format_entry_compact,
)


@pytest.fixture
def sample_entry() -> LogEntry:
    """Create a sample LogEntry for testing."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 30, 45, 123000),
        pid=12345,
        level=LogLevel.ERROR,
        message="duplicate key value violates unique constraint",
        sql_state="23505",
        raw="2024-01-15 10:30:45.123 UTC [12345] ERROR:  duplicate key value violates unique constraint",
    )


@pytest.fixture
def entry_with_detail() -> LogEntry:
    """Create a LogEntry with DETAIL field."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 30, 45, 123000),
        pid=12345,
        level=LogLevel.ERROR,
        message="duplicate key value violates unique constraint",
        sql_state="23505",
        detail="Key (id)=(123) already exists.",
        raw="...",
    )


class TestLevelStyles:
    """Tests for LEVEL_STYLES mapping."""

    def test_all_levels_have_styles(self) -> None:
        """Test that all LogLevel values have corresponding styles."""
        for level in LogLevel:
            assert level in LEVEL_STYLES, f"Missing style for {level}"

    def test_error_levels_are_red(self) -> None:
        """Test that error-class levels use red styling."""
        assert "red" in LEVEL_STYLES[LogLevel.PANIC]
        assert "red" in LEVEL_STYLES[LogLevel.FATAL]
        assert "red" in LEVEL_STYLES[LogLevel.ERROR]

    def test_warning_is_yellow(self) -> None:
        """Test that WARNING uses yellow styling."""
        assert "yellow" in LEVEL_STYLES[LogLevel.WARNING]

    def test_debug_levels_are_dim(self) -> None:
        """Test that DEBUG levels use dim styling."""
        for level in [LogLevel.DEBUG1, LogLevel.DEBUG2, LogLevel.DEBUG3, LogLevel.DEBUG4, LogLevel.DEBUG5]:
            assert "dim" in LEVEL_STYLES[level]


class TestFormatEntryAsRich:
    """Tests for format_entry_as_rich function."""

    def test_returns_text_object(self, sample_entry: LogEntry) -> None:
        """Test that function returns a Rich Text object."""
        result = format_entry_as_rich(sample_entry)
        assert isinstance(result, Text)

    def test_contains_timestamp(self, sample_entry: LogEntry) -> None:
        """Test that output contains formatted timestamp."""
        result = format_entry_as_rich(sample_entry)
        plain = result.plain
        assert "10:30:45" in plain

    def test_contains_pid(self, sample_entry: LogEntry) -> None:
        """Test that output contains PID."""
        result = format_entry_as_rich(sample_entry)
        plain = result.plain
        assert "12345" in plain

    def test_contains_level(self, sample_entry: LogEntry) -> None:
        """Test that output contains log level."""
        result = format_entry_as_rich(sample_entry)
        plain = result.plain
        assert "ERROR" in plain

    def test_contains_message(self, sample_entry: LogEntry) -> None:
        """Test that output contains message."""
        result = format_entry_as_rich(sample_entry)
        plain = result.plain
        assert "duplicate key value" in plain

    def test_contains_sqlstate(self, sample_entry: LogEntry) -> None:
        """Test that output contains SQLSTATE code."""
        result = format_entry_as_rich(sample_entry)
        plain = result.plain
        assert "23505" in plain

    def test_detail_on_separate_line(self, entry_with_detail: LogEntry) -> None:
        """Test that DETAIL field appears on separate line."""
        result = format_entry_as_rich(entry_with_detail)
        plain = result.plain
        assert "DETAIL:" in plain
        assert "Key (id)=(123)" in plain

    def test_handles_missing_timestamp(self) -> None:
        """Test graceful handling of missing timestamp."""
        entry = LogEntry(
            timestamp=None,
            pid=12345,
            level=LogLevel.LOG,
            message="test message",
            raw="test",
        )
        result = format_entry_as_rich(entry)
        assert isinstance(result, Text)
        assert "test message" in result.plain

    def test_handles_missing_pid(self) -> None:
        """Test graceful handling of missing PID."""
        entry = LogEntry(
            timestamp=datetime.now(),
            pid=None,
            level=LogLevel.LOG,
            message="test message",
            raw="test",
        )
        result = format_entry_as_rich(entry)
        assert isinstance(result, Text)
        assert "test message" in result.plain


class TestFormatEntryCompact:
    """Tests for format_entry_compact function."""

    def test_returns_string(self, sample_entry: LogEntry) -> None:
        """Test that function returns a string."""
        result = format_entry_compact(sample_entry)
        assert isinstance(result, str)

    def test_single_line(self, sample_entry: LogEntry) -> None:
        """Test that compact format is single line (no newlines in main content)."""
        result = format_entry_compact(sample_entry)
        # Main message should be on one line
        lines = result.split("\n")
        assert len(lines) >= 1
        assert "duplicate key value" in lines[0]

    def test_contains_basic_fields(self, sample_entry: LogEntry) -> None:
        """Test that compact format contains timestamp, level, message."""
        result = format_entry_compact(sample_entry)
        assert "10:30:45" in result
        assert "ERROR" in result
        assert "duplicate key value" in result
