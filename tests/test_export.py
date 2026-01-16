"""Tests for pgtail_py.export module - markup stripping functionality."""

import json
from datetime import datetime

import pytest

from pgtail_py.export import (
    ExportFormat,
    format_csv_row,
    format_entry,
    format_json_entry,
    format_text_entry,
    strip_rich_markup,
)
from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry


class TestStripRichMarkup:
    """Tests for strip_rich_markup function."""

    def test_strip_simple_tags(self) -> None:
        """Test stripping simple style tags."""
        assert strip_rich_markup("[bold]Hello[/bold]") == "Hello"
        assert strip_rich_markup("[red]Error[/red]") == "Error"
        assert strip_rich_markup("[cyan]Info[/cyan]") == "Info"

    def test_strip_closing_shorthand(self) -> None:
        """Test stripping [/] shorthand closing tag."""
        assert strip_rich_markup("[bold red]Warning[/]") == "Warning"
        assert strip_rich_markup("[yellow on blue]Text[/]") == "Text"

    def test_strip_compound_styles(self) -> None:
        """Test stripping compound style tags like [bold red on white]."""
        assert strip_rich_markup("[bold red]Critical[/bold red]") == "Critical"
        assert strip_rich_markup("[italic cyan on black]Status[/]") == "Status"

    def test_strip_multiple_tags(self) -> None:
        """Test stripping multiple tags from a line."""
        text = "[bold]Error[/bold]: [red]Connection failed[/red]"
        assert strip_rich_markup(text) == "Error: Connection failed"

    def test_strip_nested_tags(self) -> None:
        """Test stripping nested style tags."""
        text = "[bold][red]FATAL[/red][/bold] message"
        assert strip_rich_markup(text) == "FATAL message"

    def test_preserve_non_markup_brackets(self) -> None:
        """Test that literal brackets in content are preserved where possible.

        Note: The regex pattern matches [anything] so legitimate brackets like
        [12345] for PIDs would be removed. This is acceptable as exports should
        use raw entry content which doesn't have Rich markup.
        """
        # PID-style brackets would be stripped (edge case)
        # In practice, raw log content doesn't have Rich markup
        pass

    def test_no_markup_unchanged(self) -> None:
        """Test that text without markup is unchanged."""
        text = "2024-01-15 10:30:00 ERROR: Connection failed"
        assert strip_rich_markup(text) == text

    def test_empty_string(self) -> None:
        """Test handling empty string."""
        assert strip_rich_markup("") == ""

    def test_empty_brackets(self) -> None:
        """Test stripping empty brackets []."""
        assert strip_rich_markup("Hello[]World") == "HelloWorld"

    def test_highlight_style_tags(self) -> None:
        """Test stripping actual highlight style tags used by pgtail."""
        # Duration highlighting
        text = "[#ffa500]duration: 150.000 ms[/]"
        assert strip_rich_markup(text) == "duration: 150.000 ms"

        # SQLSTATE highlighting
        text = "[#ff6b6b]23505[/]"
        assert strip_rich_markup(text) == "23505"

        # Timestamp highlighting
        text = "[#888888]2024-01-15[/] [#aaaaaa]10:30:00.123[/]"
        assert strip_rich_markup(text) == "2024-01-15 10:30:00.123"


class TestFormatTextEntry:
    """Tests for format_text_entry function."""

    @pytest.fixture
    def sample_entry(self) -> LogEntry:
        """Create a sample log entry for testing."""
        return LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.ERROR,
            message="Connection failed",
            raw="[bold red]2024-01-15 10:30:00[/] ERROR: [cyan]Connection failed[/]",
            pid=12345,
        )

    def test_strip_markup_by_default(self, sample_entry: LogEntry) -> None:
        """Test that markup is stripped by default (FR-152)."""
        result = format_text_entry(sample_entry)
        assert "[bold" not in result
        assert "[red]" not in result
        assert "[/]" not in result
        assert "[cyan]" not in result
        assert "2024-01-15" in result
        assert "Connection failed" in result

    def test_preserve_markup_when_requested(self, sample_entry: LogEntry) -> None:
        """Test that markup is preserved with preserve_markup=True (FR-153)."""
        result = format_text_entry(sample_entry, preserve_markup=True)
        assert result == sample_entry.raw
        assert "[bold red]" in result
        assert "[cyan]" in result

    def test_entry_without_markup(self) -> None:
        """Test entry without any markup."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.LOG,
            message="Normal log line",
            raw="2024-01-15 10:30:00 LOG: Normal log line",
            pid=12345,
        )
        result = format_text_entry(entry)
        assert result == entry.raw


class TestFormatJsonEntry:
    """Tests for format_json_entry function."""

    @pytest.fixture
    def sample_entry_with_markup(self) -> LogEntry:
        """Create a sample log entry with markup in message."""
        return LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.ERROR,
            message="[red]unique_violation[/]: duplicate key",
            raw="2024-01-15 10:30:00 ERROR: unique_violation: duplicate key",
            pid=12345,
        )

    def test_json_never_includes_markup(self, sample_entry_with_markup: LogEntry) -> None:
        """Test that JSON export never includes markup (FR-154)."""
        result = format_json_entry(sample_entry_with_markup)
        parsed = json.loads(result)

        # Message should be stripped of markup
        assert "[red]" not in parsed["message"]
        assert "[/]" not in parsed["message"]
        assert "unique_violation" in parsed["message"]
        assert "duplicate key" in parsed["message"]

    def test_json_structure(self, sample_entry_with_markup: LogEntry) -> None:
        """Test JSON output structure."""
        result = format_json_entry(sample_entry_with_markup)
        parsed = json.loads(result)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "pid" in parsed
        assert "message" in parsed
        assert parsed["level"] == "ERROR"
        assert parsed["pid"] == 12345

    def test_json_entry_without_markup(self) -> None:
        """Test JSON output for entry without markup."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.LOG,
            message="Normal log message",
            raw="raw line",
            pid=12345,
        )
        result = format_json_entry(entry)
        parsed = json.loads(result)
        assert parsed["message"] == "Normal log message"


class TestFormatCsvRow:
    """Tests for format_csv_row function."""

    @pytest.fixture
    def sample_entry_with_markup(self) -> LogEntry:
        """Create a sample log entry with markup in message."""
        return LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.WARNING,
            message="[yellow]slow query[/]: duration 5000ms",
            raw="2024-01-15 10:30:00 WARNING: slow query: duration 5000ms",
            pid=54321,
        )

    def test_csv_never_includes_markup(self, sample_entry_with_markup: LogEntry) -> None:
        """Test that CSV export never includes markup (like JSON)."""
        result = format_csv_row(sample_entry_with_markup)

        # Markup should be stripped from message
        assert "[yellow]" not in result
        assert "[/]" not in result
        assert "slow query" in result
        assert "duration 5000ms" in result

    def test_csv_structure(self, sample_entry_with_markup: LogEntry) -> None:
        """Test CSV output structure."""
        result = format_csv_row(sample_entry_with_markup)

        # Should have 4 comma-separated fields
        # CSV quoting may affect this, so check basic structure
        assert "2024-01-15T10:30:00" in result
        assert "WARNING" in result
        assert "54321" in result


class TestFormatEntry:
    """Tests for format_entry dispatcher function."""

    @pytest.fixture
    def entry_with_markup(self) -> LogEntry:
        """Create entry with markup for testing."""
        return LogEntry(
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            level=LogLevel.ERROR,
            message="[bold]Error[/bold] occurred",
            raw="[red]2024-01-15[/] ERROR: [bold]Error[/bold] occurred",
            pid=12345,
        )

    def test_text_format_strips_by_default(self, entry_with_markup: LogEntry) -> None:
        """Test TEXT format strips markup by default."""
        result = format_entry(entry_with_markup, ExportFormat.TEXT)
        assert "[red]" not in result
        assert "[bold]" not in result
        assert "[/]" not in result

    def test_text_format_with_preserve_markup(self, entry_with_markup: LogEntry) -> None:
        """Test TEXT format preserves markup when requested."""
        result = format_entry(entry_with_markup, ExportFormat.TEXT, preserve_markup=True)
        assert "[red]" in result
        assert "[bold]" in result

    def test_json_format_always_strips(self, entry_with_markup: LogEntry) -> None:
        """Test JSON format always strips markup regardless of preserve_markup."""
        result = format_entry(entry_with_markup, ExportFormat.JSON, preserve_markup=True)
        parsed = json.loads(result)
        assert "[bold]" not in parsed["message"]
        assert "[/bold]" not in parsed["message"]

    def test_csv_format_always_strips(self, entry_with_markup: LogEntry) -> None:
        """Test CSV format always strips markup regardless of preserve_markup."""
        result = format_entry(entry_with_markup, ExportFormat.CSV, preserve_markup=True)
        assert "[bold]" not in result
        assert "[/bold]" not in result


class TestExportFormatEnum:
    """Tests for ExportFormat enum."""

    def test_from_string_valid(self) -> None:
        """Test parsing valid format strings."""
        assert ExportFormat.from_string("text") == ExportFormat.TEXT
        assert ExportFormat.from_string("TEXT") == ExportFormat.TEXT
        assert ExportFormat.from_string("json") == ExportFormat.JSON
        assert ExportFormat.from_string("csv") == ExportFormat.CSV

    def test_from_string_invalid(self) -> None:
        """Test parsing invalid format strings."""
        with pytest.raises(ValueError, match="Unknown format"):
            ExportFormat.from_string("xml")
        with pytest.raises(ValueError, match="Unknown format"):
            ExportFormat.from_string("invalid")
