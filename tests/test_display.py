"""Tests for display formatting with semantic highlighting (T103).

Tests cover:
- REPL mode highlighting integration
- Theme parameter passing
- Semantic highlighting flag behavior
- Fallback to SQL-only highlighting
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.display import (
    DisplayMode,
    DisplayState,
    OutputFormat,
    format_entry,
    format_entry_compact,
    format_entry_custom,
    format_entry_full,
)
from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry
from pgtail_py.tail_rich import reset_highlighter_chain
from pgtail_py.highlighter_registry import reset_registry
from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_theme() -> Theme:
    """Create a test theme with semantic highlighting styles."""
    return Theme(
        name="test",
        description="Test theme",
        levels={
            LogLevel.ERROR: ColorStyle(fg="red", bold=True),
            LogLevel.WARNING: ColorStyle(fg="yellow"),
            LogLevel.LOG: ColorStyle(fg="green"),
        },
        ui={
            # Duration styles for testing
            "hl_duration_fast": ColorStyle(fg="green"),
            "hl_duration_slow": ColorStyle(fg="yellow"),
            "hl_duration_critical": ColorStyle(fg="red", bold=True),
            # SQL styles
            "sql_keyword": ColorStyle(fg="blue", bold=True),
            "sql_string": ColorStyle(fg="green"),
            # Param style
            "hl_param": ColorStyle(fg="magenta"),
        },
    )


@pytest.fixture
def sample_entry() -> LogEntry:
    """Create a sample log entry."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
        pid=12345,
        level=LogLevel.LOG,
        message="duration: 150 ms  statement: SELECT * FROM users WHERE id = $1",
        raw="2024-01-15 14:30:45.123 UTC [12345] LOG: duration: 150 ms  statement: SELECT * FROM users WHERE id = $1",
    )


@pytest.fixture
def entry_with_sql() -> LogEntry:
    """Create a log entry with SQL content."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
        pid=12345,
        level=LogLevel.LOG,
        message="statement: INSERT INTO users (name, email) VALUES ('test', 'test@example.com')",
        raw="2024-01-15 14:30:45.123 UTC [12345] LOG: statement: INSERT INTO users (name, email) VALUES ('test', 'test@example.com')",
    )


@pytest.fixture(autouse=True)
def reset_highlighters():
    """Reset highlighter chain before each test."""
    from pgtail_py.tail_rich import register_all_highlighters

    reset_highlighter_chain()
    reset_registry()
    register_all_highlighters()
    yield
    reset_highlighter_chain()
    reset_registry()


# =============================================================================
# Test format_entry_compact
# =============================================================================


class TestFormatEntryCompact:
    """Tests for format_entry_compact with semantic highlighting."""

    def test_with_theme_and_highlighting(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should apply semantic highlighting when theme is provided."""
        result = format_entry_compact(
            sample_entry, theme=test_theme, use_semantic_highlighting=True
        )

        assert isinstance(result, FormattedText)
        # Should contain the message content
        text_content = "".join(part[1] for part in result)
        assert "duration" in text_content
        assert "SELECT" in text_content

    def test_without_highlighting(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should use SQL-only highlighting when semantic highlighting disabled."""
        result = format_entry_compact(
            sample_entry, theme=test_theme, use_semantic_highlighting=False
        )

        assert isinstance(result, FormattedText)
        text_content = "".join(part[1] for part in result)
        assert "duration" in text_content

    def test_without_theme(self, sample_entry: LogEntry) -> None:
        """Should fall back to SQL-only highlighting when no theme."""
        result = format_entry_compact(
            sample_entry, theme=None, use_semantic_highlighting=True
        )

        assert isinstance(result, FormattedText)
        text_content = "".join(part[1] for part in result)
        assert "duration" in text_content

    def test_includes_timestamp(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should include formatted timestamp."""
        result = format_entry_compact(sample_entry, theme=test_theme)

        text_content = "".join(part[1] for part in result)
        assert "14:30:45" in text_content

    def test_includes_pid(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should include PID in brackets."""
        result = format_entry_compact(sample_entry, theme=test_theme)

        text_content = "".join(part[1] for part in result)
        assert "[12345]" in text_content

    def test_includes_level(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should include log level."""
        result = format_entry_compact(sample_entry, theme=test_theme)

        text_content = "".join(part[1] for part in result)
        assert "LOG" in text_content


# =============================================================================
# Test format_entry_full
# =============================================================================


class TestFormatEntryFull:
    """Tests for format_entry_full with semantic highlighting."""

    def test_with_theme_and_highlighting(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should apply semantic highlighting in full mode."""
        result = format_entry_full(
            sample_entry, theme=test_theme, use_semantic_highlighting=True
        )

        assert isinstance(result, FormattedText)
        text_content = "".join(part[1] for part in result)
        assert "duration" in text_content

    def test_secondary_fields(self, test_theme: Theme) -> None:
        """Should include secondary fields when present."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.ERROR,
            message="relation does not exist",
            raw="2024-01-15 14:30:45.000 UTC [12345] ERROR: relation does not exist",
            sql_state="42P01",
            detail="The table was dropped.",
            hint="Create the table first.",
            query="SELECT * FROM missing_table",
        )

        result = format_entry_full(entry, theme=test_theme)

        text_content = "".join(part[1] for part in result)
        assert "Detail:" in text_content
        assert "Hint:" in text_content
        assert "Query:" in text_content


# =============================================================================
# Test format_entry_custom
# =============================================================================


class TestFormatEntryCustom:
    """Tests for format_entry_custom with semantic highlighting."""

    def test_selected_fields_only(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should only include selected fields."""
        result = format_entry_custom(
            sample_entry,
            fields=["level", "message"],
            theme=test_theme,
        )

        text_content = "".join(part[1] for part in result)
        assert "LOG" in text_content
        assert "duration" in text_content
        # Should not include timestamp since not in fields
        assert "14:30:45" not in text_content

    def test_message_with_highlighting(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should apply highlighting to message field."""
        result = format_entry_custom(
            sample_entry,
            fields=["message"],
            theme=test_theme,
            use_semantic_highlighting=True,
        )

        assert isinstance(result, FormattedText)
        text_content = "".join(part[1] for part in result)
        assert "duration" in text_content


# =============================================================================
# Test format_entry (dispatcher)
# =============================================================================


class TestFormatEntry:
    """Tests for format_entry dispatcher."""

    def test_compact_mode(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should use compact format by default."""
        state = DisplayState()
        state.set_compact()

        result = format_entry(sample_entry, state, theme=test_theme)

        assert isinstance(result, FormattedText)

    def test_full_mode(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should use full format when set."""
        state = DisplayState()
        state.set_full()

        result = format_entry(sample_entry, state, theme=test_theme)

        assert isinstance(result, FormattedText)

    def test_custom_mode(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should use custom format with selected fields."""
        state = DisplayState()
        state.set_custom(["timestamp", "message"])

        result = format_entry(sample_entry, state, theme=test_theme)

        assert isinstance(result, FormattedText)

    def test_json_output(self, test_theme: Theme, sample_entry: LogEntry) -> None:
        """Should return JSON string for JSON output format."""
        state = DisplayState()
        state.set_output_json()

        result = format_entry(sample_entry, state, theme=test_theme)

        assert isinstance(result, str)
        assert "duration" in result

    def test_passes_theme_to_compact(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should pass theme parameter through to format functions."""
        state = DisplayState()

        # With highlighting enabled
        result = format_entry(
            sample_entry, state, theme=test_theme, use_semantic_highlighting=True
        )

        assert isinstance(result, FormattedText)

    def test_highlighting_disabled(
        self, test_theme: Theme, sample_entry: LogEntry
    ) -> None:
        """Should respect use_semantic_highlighting flag."""
        state = DisplayState()

        result = format_entry(
            sample_entry, state, theme=test_theme, use_semantic_highlighting=False
        )

        assert isinstance(result, FormattedText)


# =============================================================================
# Test DisplayState
# =============================================================================


class TestDisplayState:
    """Tests for DisplayState class."""

    def test_default_mode(self) -> None:
        """Should default to compact mode."""
        state = DisplayState()
        assert state.mode == DisplayMode.COMPACT

    def test_default_output_format(self) -> None:
        """Should default to text output."""
        state = DisplayState()
        assert state.output_format == OutputFormat.TEXT

    def test_set_full(self) -> None:
        """Should set full mode."""
        state = DisplayState()
        state.set_full()
        assert state.mode == DisplayMode.FULL

    def test_set_custom(self) -> None:
        """Should set custom mode with valid fields."""
        state = DisplayState()
        invalid = state.set_custom(["timestamp", "invalid_field", "message"])

        assert state.mode == DisplayMode.CUSTOM
        assert state.custom_fields == ["timestamp", "message"]
        assert invalid == ["invalid_field"]

    def test_format_status(self) -> None:
        """Should format status string."""
        state = DisplayState()
        status = state.format_status()

        assert "compact" in status
        assert "text" in status
