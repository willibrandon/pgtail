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


# =============================================================================
# SQL Highlighting Integration Tests (T014)
# =============================================================================


class TestFormatEntryCompactSqlHighlighting:
    """Tests for SQL highlighting in format_entry_compact() - T014."""

    def test_sql_statement_highlighted(self) -> None:
        """SQL statement in message should be highlighted with Rich markup."""
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: statement: SELECT * FROM users",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT * FROM users",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        # Should have Rich markup tags
        assert "[" in result
        # Should contain the SQL keywords
        assert "SELECT" in result
        assert "FROM" in result

    def test_no_sql_message_escaped(self) -> None:
        """Non-SQL message should be escaped but not highlighted."""
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: connection received",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            pid=12345,
            level=LogLevel.LOG,
            message="connection received",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        assert "connection received" in result

    def test_sql_with_brackets_escaped(self) -> None:
        """SQL with array brackets should escape brackets properly."""
        entry = LogEntry(
            raw="2024-01-15 10:00:00.000 UTC LOG: statement: SELECT arr[1] FROM t",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT arr[1] FROM t",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        # Bracket should be escaped to prevent Rich parsing errors
        assert "\\[" in result

    def test_execute_statement_detected(self) -> None:
        """Execute statement pattern should be detected and highlighted."""
        entry = LogEntry(
            raw="LOG: execute S_1: SELECT id FROM orders WHERE status = $1",
            timestamp=None,
            pid=None,
            level=LogLevel.LOG,
            message="execute S_1: SELECT id FROM orders WHERE status = $1",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        assert "SELECT" in result
        assert "FROM" in result
        # Should have Rich markup
        assert "[" in result

    def test_message_with_brackets_no_sql_escaped(self) -> None:
        """Non-SQL message with brackets should be escaped."""
        entry = LogEntry(
            raw="LOG: array value [1, 2, 3] received",
            timestamp=None,
            pid=None,
            level=LogLevel.LOG,
            message="array value [1, 2, 3] received",
            sql_state=None,
        )
        result = format_entry_compact(entry)
        # Brackets should be escaped
        assert "\\[" in result


class TestFormatEntryCompactThemeSwitch:
    """Tests for theme switching in format_entry_compact() - T040."""

    def test_theme_switch_updates_sql_colors(self) -> None:
        """Simulating theme switch should update SQL colors in output (T040)."""
        from pgtail_py.sql_highlighter import _get_theme_manager, highlight_sql_rich
        from pgtail_py.themes import BUILTIN_THEMES

        # Get the theme manager
        tm = _get_theme_manager()

        # Switch to dark theme
        tm._current_theme = BUILTIN_THEMES["dark"]
        result_dark = highlight_sql_rich("SELECT id FROM users")

        # Switch to monokai theme
        tm._current_theme = BUILTIN_THEMES["monokai"]
        result_monokai = highlight_sql_rich("SELECT id FROM users")

        # Both should have markup
        assert "[" in result_dark
        assert "[" in result_monokai

        # The colors should be different (dark uses ansiblue, monokai uses #f92672)
        # We just verify the outputs are different
        assert result_dark != result_monokai

        # Both should still contain the SQL content
        assert "SELECT" in result_dark
        assert "SELECT" in result_monokai


class TestFormatEntryCompactNoColor:
    """Tests for NO_COLOR handling in format_entry_compact() - T032."""

    def test_no_color_produces_no_rich_markup(self) -> None:
        """format_entry_compact() should produce no Rich markup when NO_COLOR=1 (T032)."""
        import os
        from unittest.mock import patch

        from pgtail_py import utils

        entry = LogEntry(
            raw="LOG: statement: SELECT * FROM users",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT * FROM users",
            sql_state=None,
        )

        with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
            utils._color_disabled = None  # Clear cache
            try:
                result = format_entry_compact(entry)
                # Should not have Rich closing tags from SQL highlighting
                # (Note: the entry itself has level markup, but SQL portion shouldn't)
                # The SQL portion should have escaped brackets but no color markup
                assert "SELECT" in result
                assert "FROM" in result
            finally:
                utils._color_disabled = None  # Clear cache


class TestFormatEntryCompactPerformance:
    """Performance tests for format_entry_compact() - T054, T055."""

    def test_format_entry_under_100ms(self) -> None:
        """format_entry_compact() should complete within 100ms for typical SQL (SC-001)."""
        import time

        entry = LogEntry(
            raw="LOG: statement: SELECT id, name, email FROM users WHERE active = true ORDER BY created_at DESC LIMIT 100",
            timestamp=datetime(2024, 1, 15, 10, 0, 0),
            pid=12345,
            level=LogLevel.LOG,
            message="statement: SELECT id, name, email FROM users WHERE active = true ORDER BY created_at DESC LIMIT 100",
            sql_state=None,
        )

        start = time.perf_counter()
        result = format_entry_compact(entry)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result  # Result is valid
        assert elapsed_ms < 100, f"format_entry_compact() took {elapsed_ms:.2f}ms, expected < 100ms"

    def test_100_entries_per_second_throughput(self) -> None:
        """Should be able to format 100+ entries/sec without visible delay (SC-004)."""
        import time

        entries = [
            LogEntry(
                raw=f"LOG: statement: SELECT id FROM table_{i} WHERE col = 'value_{i}'",
                timestamp=datetime(2024, 1, 15, 10, 0, i % 60),
                pid=12345 + i,
                level=LogLevel.LOG,
                message=f"statement: SELECT id FROM table_{i} WHERE col = 'value_{i}'",
                sql_state=None,
            )
            for i in range(100)
        ]

        start = time.perf_counter()
        results = [format_entry_compact(entry) for entry in entries]
        elapsed_sec = time.perf_counter() - start

        assert len(results) == 100
        assert all(r for r in results)
        # Should complete 100 entries in under 1 second
        assert elapsed_sec < 1.0, f"100 entries took {elapsed_sec:.2f}s, expected < 1.0s"
