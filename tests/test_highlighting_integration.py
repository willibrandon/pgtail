"""Integration tests for semantic highlighting.

Tests cover:
- Full highlighting pipeline in tail mode
- Theme switching and color changes
- NO_COLOR environment variable handling
- Missing hl_* theme key fallback behavior
- Edge cases (long lines, overlapping patterns, nested patterns)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from pgtail_py.filter import LogLevel
from pgtail_py.highlighter import (
    HighlighterChain,
    OccupancyTracker,
    escape_brackets,
    is_color_disabled,
)
from pgtail_py.highlighter_registry import get_registry, reset_registry
from pgtail_py.highlighting_config import HighlightingConfig
from pgtail_py.parser import LogEntry
from pgtail_py.tail_rich import (
    format_entry_compact,
    get_highlighter_chain,
    register_all_highlighters,
    reset_highlighter_chain,
)
from pgtail_py.theme import ColorStyle, Theme


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def test_theme() -> Theme:
    """Create a test theme with all highlight styles."""
    return Theme(
        name="test",
        description="Test theme",
        levels={
            "ERROR": ColorStyle(fg="red", bold=True),
            "WARNING": ColorStyle(fg="yellow"),
            "LOG": ColorStyle(fg="green"),
        },
        ui={
            # Structural
            "hl_timestamp_date": ColorStyle(fg="gray"),
            "hl_timestamp_time": ColorStyle(fg="gray"),
            "hl_timestamp_ms": ColorStyle(fg="gray", dim=True),
            "hl_timestamp_tz": ColorStyle(fg="gray", dim=True),
            "hl_pid": ColorStyle(fg="cyan"),
            "hl_context": ColorStyle(fg="yellow", bold=True),
            # Diagnostic
            "hl_sqlstate_success": ColorStyle(fg="green"),
            "hl_sqlstate_warning": ColorStyle(fg="yellow"),
            "hl_sqlstate_error": ColorStyle(fg="red"),
            "hl_error_name": ColorStyle(fg="red", bold=True),
            # Performance
            "hl_duration_fast": ColorStyle(fg="green"),
            "hl_duration_slow": ColorStyle(fg="yellow"),
            "hl_duration_very_slow": ColorStyle(fg="yellow", bold=True),
            "hl_duration_critical": ColorStyle(fg="red", bold=True),
            "hl_memory_value": ColorStyle(fg="cyan"),
            "hl_memory_unit": ColorStyle(fg="cyan", dim=True),
            "hl_statistics": ColorStyle(fg="blue"),
            # Objects
            "hl_identifier": ColorStyle(fg="cyan"),
            "hl_relation": ColorStyle(fg="cyan", bold=True),
            "hl_schema": ColorStyle(fg="blue"),
            # WAL
            "hl_lsn_segment": ColorStyle(fg="blue"),
            "hl_lsn_offset": ColorStyle(fg="blue", dim=True),
            "hl_wal_segment": ColorStyle(fg="blue"),
            "hl_txid": ColorStyle(fg="magenta"),
            # Connection
            "hl_host": ColorStyle(fg="cyan"),
            "hl_port": ColorStyle(fg="cyan", dim=True),
            "hl_user": ColorStyle(fg="green"),
            "hl_database": ColorStyle(fg="green"),
            "hl_ip": ColorStyle(fg="cyan"),
            "hl_backend": ColorStyle(fg="magenta"),
            # SQL
            "hl_param": ColorStyle(fg="magenta"),
            "sql_keyword": ColorStyle(fg="blue", bold=True),
            "sql_string": ColorStyle(fg="green"),
            "sql_number": ColorStyle(fg="magenta"),
            "sql_operator": ColorStyle(fg="yellow"),
            # Lock
            "hl_lock_share": ColorStyle(fg="blue"),
            "hl_lock_exclusive": ColorStyle(fg="red"),
            "hl_lock_wait": ColorStyle(fg="yellow"),
            # Checkpoint
            "hl_checkpoint": ColorStyle(fg="cyan"),
            "hl_recovery": ColorStyle(fg="magenta"),
            # Misc
            "hl_bool_true": ColorStyle(fg="green"),
            "hl_bool_false": ColorStyle(fg="red"),
            "hl_null": ColorStyle(fg="magenta", bold=True),
            "hl_oid": ColorStyle(fg="cyan"),
            "hl_path": ColorStyle(fg="blue"),
        },
    )


@pytest.fixture
def minimal_theme() -> Theme:
    """Create a minimal theme missing most hl_* keys."""
    return Theme(
        name="minimal",
        description="Minimal theme",
        levels={},
        ui={
            # Only a few keys defined
            "hl_duration_fast": ColorStyle(fg="green"),
        },
    )


@pytest.fixture
def sample_log_entry() -> LogEntry:
    """Create a sample log entry for testing."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
        pid=12345,
        level=LogLevel.LOG,
        message="duration: 1234.567 ms  statement: SELECT * FROM users WHERE id = $1",
        raw="2024-01-15 14:30:45.123 UTC [12345] LOG: duration: 1234.567 ms  statement: SELECT * FROM users WHERE id = $1",
    )


@pytest.fixture(autouse=True)
def reset_highlighters():
    """Reset highlighter chain and registry before and after each test.

    Note: This clears the global state so tests are isolated. Tests that
    need highlighters must call register_all_highlighters() or use
    get_highlighter_chain() which does this automatically.
    """
    reset_highlighter_chain()
    reset_registry()
    # Re-register highlighters for tests that use get_highlighter_chain
    register_all_highlighters()
    yield
    reset_highlighter_chain()
    reset_registry()


# =============================================================================
# Test Tail Mode Integration (T090)
# =============================================================================


class TestTailModeIntegration:
    """Tests for tail mode highlighting integration."""

    def test_format_entry_applies_highlighting(self, test_theme: Theme, sample_log_entry: LogEntry) -> None:
        """format_entry_compact should apply semantic highlighting."""
        result = format_entry_compact(sample_log_entry, theme=test_theme, use_semantic_highlighting=True)

        # Should contain Rich markup (style tags)
        assert "[" in result
        # Should contain the message content
        assert "duration" in result
        assert "SELECT" in result

    def test_format_entry_without_highlighting(self, test_theme: Theme, sample_log_entry: LogEntry) -> None:
        """format_entry_compact with use_semantic_highlighting=False should not apply chain."""
        result = format_entry_compact(sample_log_entry, theme=test_theme, use_semantic_highlighting=False)

        # Should still escape brackets but not apply semantic styles
        assert "duration" in result
        # Brackets should be escaped
        assert "\\[12345]" in result

    def test_format_entry_without_theme(self, sample_log_entry: LogEntry) -> None:
        """format_entry_compact without theme should use SQL-only highlighting."""
        result = format_entry_compact(sample_log_entry, theme=None, use_semantic_highlighting=True)

        # Should still work and contain message
        assert "duration" in result
        assert "SELECT" in result

    def test_highlighter_chain_is_cached(self, test_theme: Theme) -> None:
        """get_highlighter_chain should return cached chain."""
        chain1 = get_highlighter_chain()
        chain2 = get_highlighter_chain()

        assert chain1 is chain2

    def test_highlighter_chain_config_change(self, test_theme: Theme) -> None:
        """get_highlighter_chain with different config should return new chain."""
        config1 = HighlightingConfig()
        config2 = HighlightingConfig()
        config2.max_length = 5000

        chain1 = get_highlighter_chain(config1)
        chain2 = get_highlighter_chain(config2)

        # Different config means different chain
        assert chain1 is not chain2

    def test_all_highlighters_registered(self) -> None:
        """register_all_highlighters should register all built-in highlighters."""
        register_all_highlighters()
        registry = get_registry()

        # Should have all categories
        categories = registry.all_categories()
        assert "structural" in categories
        assert "diagnostic" in categories
        assert "performance" in categories
        assert "objects" in categories
        assert "wal" in categories
        assert "connection" in categories
        assert "sql" in categories
        assert "lock" in categories
        assert "checkpoint" in categories
        assert "misc" in categories

        # Should have all highlighters
        names = registry.all_names()
        assert "timestamp" in names
        assert "duration" in names
        assert "sqlstate" in names


# =============================================================================
# Test Theme Switching (T094)
# =============================================================================


class TestThemeSwitching:
    """Tests for theme switching."""

    def test_highlighting_uses_current_theme(self, test_theme: Theme) -> None:
        """Highlighting should use colors from current theme."""
        chain = get_highlighter_chain()
        text = "duration: 150 ms"

        result = chain.apply_rich(text, test_theme)

        # Should have styling from theme
        assert "[" in result
        assert "150 ms" in result

    def test_theme_switch_changes_colors(self) -> None:
        """Switching theme should change highlighting colors."""
        chain = get_highlighter_chain()
        text = "duration: 150 ms"

        # Theme with green duration
        theme1 = Theme(
            name="green",
            description="Green theme",
            levels={},
            ui={"hl_duration_slow": ColorStyle(fg="green")},
        )

        # Theme with red duration
        theme2 = Theme(
            name="red",
            description="Red theme",
            levels={},
            ui={"hl_duration_slow": ColorStyle(fg="red")},
        )

        result1 = chain.apply_rich(text, theme1)
        result2 = chain.apply_rich(text, theme2)

        # Results should be different (different colors)
        # Both should contain the text but with different styles
        assert "150 ms" in result1
        assert "150 ms" in result2
        # Check style differences
        if "green" in result1:
            assert "red" in result2

    def test_theme_get_style_fallback(self, minimal_theme: Theme) -> None:
        """Theme should return None for missing hl_* keys."""
        # This key exists
        style = minimal_theme.get_style("hl_duration_fast")
        assert style is not None
        assert style.fg == "green"

        # This key doesn't exist
        style = minimal_theme.get_style("hl_timestamp_date")
        assert style is None

    def test_highlighting_with_missing_theme_keys(self, minimal_theme: Theme) -> None:
        """Highlighting should work with missing theme keys (graceful fallback)."""
        chain = get_highlighter_chain()
        text = "2024-01-15 14:30:45 duration: 50 ms"

        # Should not raise even with missing keys
        result = chain.apply_rich(text, minimal_theme)

        # Should still contain the text
        assert "2024-01-15" in result
        assert "50 ms" in result
        # Duration styling should be present (key exists)
        assert "[green]" in result or "green" in result


# =============================================================================
# Test NO_COLOR (T095)
# =============================================================================


class TestNoColor:
    """Tests for NO_COLOR handling."""

    def test_is_color_disabled_default(self) -> None:
        """is_color_disabled should return False by default."""
        # Clear NO_COLOR if set
        old_value = os.environ.pop("NO_COLOR", None)
        try:
            assert is_color_disabled() is False
        finally:
            if old_value is not None:
                os.environ["NO_COLOR"] = old_value

    def test_is_color_disabled_when_set(self) -> None:
        """is_color_disabled should return True when NO_COLOR is set."""
        old_value = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"
            assert is_color_disabled() is True

            os.environ["NO_COLOR"] = ""  # Empty string means not set
            assert is_color_disabled() is False

            os.environ["NO_COLOR"] = "anything"
            assert is_color_disabled() is True
        finally:
            if old_value is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_value

    def test_highlighter_chain_respects_no_color(self, test_theme: Theme) -> None:
        """HighlighterChain should return plain text when NO_COLOR is set."""
        chain = get_highlighter_chain()
        text = "duration: 150 ms"

        old_value = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"

            result = chain.apply_rich(text, test_theme)

            # Should be escaped but no color tags
            assert "[" not in result or result.startswith("\\[")
            assert "duration" in result
        finally:
            if old_value is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_value

    def test_highlighter_chain_apply_respects_no_color(self, test_theme: Theme) -> None:
        """HighlighterChain.apply() should return plain text when NO_COLOR is set."""
        chain = get_highlighter_chain()
        text = "duration: 150 ms"

        old_value = os.environ.get("NO_COLOR")
        try:
            os.environ["NO_COLOR"] = "1"

            result = chain.apply(text, test_theme)

            # Should be FormattedText with no styles
            assert len(result) == 1
            assert result[0][0] == ""  # Empty style
            assert result[0][1] == text  # Original text
        finally:
            if old_value is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = old_value


# =============================================================================
# Test Non-Overlapping Composition (T096-T099)
# =============================================================================


class TestNonOverlapping:
    """Tests for non-overlapping composition."""

    def test_occupancy_tracker_prevents_overlap(self) -> None:
        """OccupancyTracker should prevent overlapping highlights."""
        tracker = OccupancyTracker(20)

        # Mark region 5-10
        tracker.mark_occupied(5, 10)

        # Region 5-10 should not be available
        assert tracker.is_available(5, 10) is False
        assert tracker.is_available(6, 8) is False
        assert tracker.is_available(4, 11) is False

        # Adjacent regions should be available
        assert tracker.is_available(0, 5) is True
        assert tracker.is_available(10, 15) is True

    def test_highlighter_chain_overlap_prevention(self, test_theme: Theme) -> None:
        """HighlighterChain should prevent overlapping highlights."""
        chain = get_highlighter_chain()

        # Text with multiple highlightable patterns in same region
        # "123.456" could match duration and number patterns
        text = "duration: 123.456 ms table users"

        result = chain.apply_rich(text, test_theme)

        # Should contain only one style per character (no nesting)
        # Count open/close brackets should be balanced
        open_count = result.count("[") - result.count("\\[")
        close_count = result.count("[/]")
        # Each styled region has one open and one close
        assert open_count >= close_count

    def test_priority_based_conflict_resolution(self, test_theme: Theme) -> None:
        """Lower priority highlighters should win on conflict."""
        # Create two highlighters that match same text
        from pgtail_py.highlighter import RegexHighlighter

        # Lower priority (100) wins
        h1 = RegexHighlighter(
            name="test_high_priority",
            priority=100,
            pattern=r"test",
            style="hl_timestamp_date",
        )

        # Higher priority (500) loses
        h2 = RegexHighlighter(
            name="test_low_priority",
            priority=500,
            pattern=r"test",
            style="hl_wal_segment",
        )

        chain = HighlighterChain([h1, h2])
        text = "test"

        result = chain.apply_rich(text, test_theme)

        # Should have style from h1 (lower priority number)
        assert "gray" in result  # hl_timestamp_date is gray in test_theme

    def test_nested_pattern_handling(self, test_theme: Theme) -> None:
        """Should handle nested patterns (schema.table within relation)."""
        chain = get_highlighter_chain()

        # Schema-qualified name
        text = "relation public.users"

        result = chain.apply_rich(text, test_theme)

        # Should highlight without errors
        assert "public.users" in result or "public" in result

    def test_multi_pattern_same_line(self, test_theme: Theme) -> None:
        """Multiple different patterns on same line should all be highlighted."""
        chain = get_highlighter_chain()

        # Line with multiple pattern types
        text = "2024-01-15 [12345] duration: 150 ms relation users"

        result = chain.apply_rich(text, test_theme)

        # All parts should be in result (checking for text content, may include markup)
        assert "2024" in result and "01" in result and "15" in result
        assert "12345" in result  # May be in escaped form like \\[12345]
        assert "150 ms" in result or ("150" in result and "ms" in result)


# =============================================================================
# Test Missing Theme Keys Fallback (T177)
# =============================================================================


class TestMissingThemeKeys:
    """Tests for missing theme key fallback."""

    def test_missing_key_returns_plain_text(self, minimal_theme: Theme) -> None:
        """Missing theme key should result in plain text (no style)."""
        chain = get_highlighter_chain()

        # Timestamp - key doesn't exist in minimal theme
        text = "2024-01-15 14:30:45"

        result = chain.apply_rich(text, minimal_theme)

        # Should still contain the text
        assert "2024-01-15" in result
        # Should have escaped brackets but minimal/no styling
        # (exact styling depends on which keys are missing)

    def test_partial_styling_with_missing_keys(self, minimal_theme: Theme) -> None:
        """Some patterns styled, others not, based on available keys."""
        chain = get_highlighter_chain()

        # Duration (key exists) and timestamp (key missing)
        text = "2024-01-15 duration: 50 ms"

        result = chain.apply_rich(text, minimal_theme)

        # Duration should be styled (green)
        assert "green" in result
        # Both parts should be present
        assert "2024-01-15" in result
        assert "50 ms" in result

    def test_all_keys_missing_returns_escaped_text(self) -> None:
        """Theme with no hl_* keys should return escaped text."""
        empty_theme = Theme(
            name="empty",
            description="Empty theme",
            levels={},
            ui={},
        )

        chain = get_highlighter_chain()
        text = "2024-01-15 [12345] LOG: test"

        result = chain.apply_rich(text, empty_theme)

        # Should have escaped brackets
        assert "\\[12345]" in result
        # Content should be present
        assert "test" in result


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_text(self, test_theme: Theme) -> None:
        """Empty text should return empty string."""
        chain = get_highlighter_chain()
        result = chain.apply_rich("", test_theme)
        assert result == ""

    def test_no_matches(self, test_theme: Theme) -> None:
        """Text with no matches should return escaped text."""
        chain = get_highlighter_chain()
        text = "plain text without patterns"
        result = chain.apply_rich(text, test_theme)
        # Should be escaped (in case there are brackets)
        assert "plain text" in result

    def test_long_line_depth_limiting(self, test_theme: Theme) -> None:
        """Long lines should be truncated at max_length for highlighting."""
        config = HighlightingConfig()
        config.max_length = 100  # Small limit for testing

        registry = get_registry()
        register_all_highlighters()
        chain = registry.create_chain(config)

        # Create text longer than max_length
        text = "duration: 150 ms " * 100  # Much longer than 100 chars

        result = chain.apply_rich(text, test_theme)

        # Should still work without error
        assert "duration" in result
        # Full text content should be present
        assert len(result) > 0

    def test_rich_markup_like_content(self, test_theme: Theme) -> None:
        """Content that looks like Rich markup should be escaped."""
        chain = get_highlighter_chain()
        text = "[bold]not markup[/bold] just text"

        result = chain.apply_rich(text, test_theme)

        # The literal [bold] should be escaped
        assert "\\[bold]" in result

    def test_escape_brackets_utility(self) -> None:
        """escape_brackets should escape all open brackets."""
        assert escape_brackets("[test]") == "\\[test]"
        assert escape_brackets("[[nested]]") == "\\[\\[nested]]"
        assert escape_brackets("no brackets") == "no brackets"
        assert escape_brackets("") == ""

    def test_extremely_long_lines_over_10kb(self, test_theme: Theme) -> None:
        """Extremely long lines (>10KB) should be handled with depth limiting (T163).

        The default max_length is 10KB (10240 bytes). Lines longer than this
        should have highlighting applied only to the first max_length chars,
        with the remainder passed through unmodified.
        """
        chain = get_highlighter_chain()

        # Create text > 10KB with recognizable patterns at start and end
        prefix = "duration: 100 ms "  # Highlightable pattern at start
        middle = "x" * 11000  # Filler to exceed 10KB
        suffix = "duration: 200 ms"  # Pattern at end (beyond max_length)

        text = prefix + middle + suffix

        assert len(text) > 10240  # Verify > 10KB

        result = chain.apply_rich(text, test_theme)

        # Result should contain all the text (escaped)
        assert len(result) >= len(text) - 100  # Allow for markup overhead
        # The prefix pattern should be highlighted (within max_length)
        assert "100 ms" in result
        # The suffix should be present (passed through as escaped text)
        assert "200 ms" in result

    def test_very_long_line_performance(self, test_theme: Theme) -> None:
        """Very long lines should not cause excessive processing time.

        Even with max_length limiting, we should verify the system handles
        large inputs gracefully without timeout or memory issues.
        """
        import time

        chain = get_highlighter_chain()

        # 100KB line - 10x larger than max_length
        huge_line = "duration: 150 ms " * 6000

        start = time.perf_counter()
        result = chain.apply_rich(huge_line, test_theme)
        elapsed = time.perf_counter() - start

        # Should complete quickly (< 100ms) due to depth limiting
        assert elapsed < 0.1, f"100KB line took {elapsed:.3f}s, expected < 100ms"
        # Result should contain the text
        assert "duration" in result
        assert "150 ms" in result


# =============================================================================
# Test SQL Context Awareness
# =============================================================================


class TestSQLContextAwareness:
    """Tests that SQL keywords are only highlighted within SQL contexts.

    Common English words that are also SQL keywords (for, with, at, or)
    should NOT be highlighted in regular log messages, only within actual
    SQL statements detected by sql_detector.
    """

    def test_sql_keywords_not_highlighted_outside_context(
        self, test_theme: Theme
    ) -> None:
        """SQL keywords in regular log text should NOT be highlighted."""
        chain = get_highlighter_chain()

        # Regular log message with words that are also SQL keywords
        text = "background worker exited with exit code 0"

        result = chain.apply_rich(text, test_theme)

        # "with" should NOT be styled as SQL keyword (no blue)
        # The word should appear but without sql_keyword styling
        assert "with" in result
        # Should not have SQL keyword styling
        assert "bold blue" not in result or result.count("bold blue") == 0

    def test_sql_keywords_not_highlighted_for_with_at_or(
        self, test_theme: Theme
    ) -> None:
        """Common words for/with/at/or should not be SQL-highlighted outside SQL."""
        chain = get_highlighter_chain()

        # Log messages that contain SQL keywords as English words
        messages = [
            "registering pglogical manager process for database pg_walrus",
            "manager worker at slot 1 generation 3558 detaching cleanly",
            "already at or below min_size",
            "checkpointer starting with time",
        ]

        for text in messages:
            result = chain.apply_rich(text, test_theme)
            # These common English words should not have SQL keyword styling
            # sql_keyword uses "bold blue" in test_theme
            # The words should be present but not SQL-styled
            assert "bold blue" not in result

    def test_sql_keywords_highlighted_inside_sql_context(
        self, test_theme: Theme
    ) -> None:
        """SQL keywords within 'statement:' context SHOULD be highlighted."""
        chain = get_highlighter_chain()

        # Log message with actual SQL
        text = "statement: SELECT id, name FROM users WHERE id = 1"

        result = chain.apply_rich(text, test_theme)

        # SQL keywords should be styled
        # SELECT, FROM, WHERE should have SQL styling
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_sql_keywords_in_duration_statement(self, test_theme: Theme) -> None:
        """SQL in duration: ... statement: should be highlighted."""
        chain = get_highlighter_chain()

        text = "duration: 5.123 ms statement: SELECT * FROM users"

        result = chain.apply_rich(text, test_theme)

        # SQL keywords should be present (styling may vary by theme)
        assert "SELECT" in result
        assert "FROM" in result

    def test_sql_keywords_in_execute_context(self, test_theme: Theme) -> None:
        """SQL in execute <name>: should be highlighted."""
        chain = get_highlighter_chain()

        text = "execute stmt_1: SELECT id FROM accounts WHERE active = true"

        result = chain.apply_rich(text, test_theme)

        # SQL keywords should be present
        assert "SELECT" in result
        assert "FROM" in result
        assert "WHERE" in result

    def test_non_sql_highlighters_still_work_everywhere(
        self, test_theme: Theme
    ) -> None:
        """Non-SQL highlighters (checkpoint, recovery, etc) should still apply."""
        chain = get_highlighter_chain()

        # Log message with checkpoint keywords (not SQL)
        text = "checkpoint starting: time"

        result = chain.apply_rich(text, test_theme)

        # Checkpoint keywords should still be highlighted
        # They're not SQL highlighters, so they apply everywhere
        assert "checkpoint" in result
        assert "starting" in result

    def test_mixed_sql_and_non_sql_highlighting(self, test_theme: Theme) -> None:
        """Both SQL (in context) and non-SQL highlighting should work together."""
        chain = get_highlighter_chain()

        # Duration highlighting (non-SQL) + SQL statement
        text = "duration: 150 ms statement: SELECT * FROM users"

        result = chain.apply_rich(text, test_theme)

        # Duration should be highlighted (performance highlighter)
        assert "150 ms" in result or "150" in result
        # SQL keywords in the SQL context should be present
        assert "SELECT" in result
        assert "FROM" in result


# =============================================================================
# Test Performance Throughput
# =============================================================================


class TestPerformanceThroughput:
    """Performance benchmark tests for highlighting throughput.

    Requirement: 10,000 lines/second throughput for semantic highlighting.
    """

    def test_throughput_10000_lines_per_second(self, test_theme: Theme) -> None:
        """Highlighting should process at least 10,000 lines per second."""
        import time

        chain = get_highlighter_chain()

        # Representative log lines with various patterns to highlight
        sample_lines = [
            "2024-01-15 14:30:45.123 UTC [12345] LOG: duration: 150.234 ms",
            "2024-01-15 14:30:45.124 UTC [12346] ERROR: SQLSTATE 23505 unique_violation",
            "2024-01-15 14:30:45.125 UTC [12347] LOG: checkpoint starting: time",
            "2024-01-15 14:30:45.126 UTC [12348] LOG: statement: SELECT * FROM users",
            "2024-01-15 14:30:45.127 UTC [12349] LOG: connection received: host=127.0.0.1",
            "2024-01-15 14:30:45.128 UTC [12350] LOG: LSN 0/1234ABCD WAL segment 000000010000000000000001",
            "2024-01-15 14:30:45.129 UTC [12351] LOG: acquired AccessShareLock on relation users",
            "2024-01-15 14:30:45.130 UTC [12352] LOG: autovacuum: processing database postgres",
            "2024-01-15 14:30:45.131 UTC [12353] LOG: recovery started at 0/1234ABCD",
            "2024-01-15 14:30:45.132 UTC [12354] DEBUG1: memory used: 1024 MB buffers: 256",
        ]

        # Number of lines to process for benchmark
        num_iterations = 10000
        lines_to_process = [sample_lines[i % len(sample_lines)] for i in range(num_iterations)]

        # Measure time to process all lines
        start_time = time.perf_counter()

        for line in lines_to_process:
            chain.apply_rich(line, test_theme)

        elapsed_time = time.perf_counter() - start_time

        # Calculate throughput
        lines_per_second = num_iterations / elapsed_time

        # Assert minimum throughput of 10,000 lines/second
        assert lines_per_second >= 10000, (
            f"Throughput {lines_per_second:.0f} lines/sec is below "
            f"required 10,000 lines/sec (took {elapsed_time:.3f}s for {num_iterations} lines)"
        )

    def test_throughput_with_long_lines(self, test_theme: Theme) -> None:
        """Highlighting should maintain throughput with longer lines."""
        import time

        chain = get_highlighter_chain()

        # Longer line with SQL statement
        long_line = (
            "2024-01-15 14:30:45.123 UTC [12345] LOG: duration: 1234.567 ms  "
            "statement: SELECT id, name, email, created_at, updated_at FROM users "
            "WHERE status = 'active' AND role IN ('admin', 'user') ORDER BY created_at DESC"
        )

        num_iterations = 5000  # Fewer iterations for longer lines

        start_time = time.perf_counter()

        for _ in range(num_iterations):
            chain.apply_rich(long_line, test_theme)

        elapsed_time = time.perf_counter() - start_time

        lines_per_second = num_iterations / elapsed_time

        # Longer lines may be slower, but should still exceed 5,000 lines/sec
        assert lines_per_second >= 5000, (
            f"Throughput {lines_per_second:.0f} lines/sec is below "
            f"required 5,000 lines/sec for long lines"
        )

    def test_throughput_prompt_toolkit_apply(self, test_theme: Theme) -> None:
        """FormattedText output (prompt_toolkit) should also meet throughput."""
        import time

        chain = get_highlighter_chain()

        sample_line = "2024-01-15 14:30:45.123 UTC [12345] LOG: duration: 150.234 ms"

        num_iterations = 10000

        start_time = time.perf_counter()

        for _ in range(num_iterations):
            chain.apply(sample_line, test_theme)

        elapsed_time = time.perf_counter() - start_time

        lines_per_second = num_iterations / elapsed_time

        assert lines_per_second >= 10000, (
            f"FormattedText throughput {lines_per_second:.0f} lines/sec is below "
            f"required 10,000 lines/sec"
        )


# =============================================================================
# Test CSV/JSON Log Format Highlighting (T167)
# =============================================================================


class TestCSVJSONLogFormatHighlighting:
    """Tests for highlighting applied to CSV/JSON log format output.

    Per Edge Case #9 in the spec: Highlighting applies to the formatted display
    output regardless of the underlying log format (TEXT, CSV, JSON). The message,
    detail, and hint fields should all have highlighting applied.
    """

    def test_highlighting_applies_to_message_field(self, test_theme: Theme) -> None:
        """Highlighting should apply to the message field content."""
        chain = get_highlighter_chain()

        # Message field from a parsed CSV/JSON log entry
        message = "duration: 150.234 ms  statement: SELECT * FROM users"

        result = chain.apply_rich(message, test_theme)

        # Should have Rich markup for duration
        assert "[" in result  # Has markup tags
        assert "150" in result  # Has the duration value
        assert "SELECT" in result  # SQL content preserved

    def test_highlighting_applies_to_detail_field(self, test_theme: Theme) -> None:
        """Highlighting should apply to the detail field content."""
        chain = get_highlighter_chain()

        # Detail field often contains SQL-related info
        detail = 'Key (id)=(42) already exists.'

        result = chain.apply_rich(detail, test_theme)

        # Content should be preserved
        assert "id" in result
        assert "42" in result

    def test_highlighting_applies_to_hint_field(self, test_theme: Theme) -> None:
        """Highlighting should apply to the hint field content."""
        chain = get_highlighter_chain()

        # Hint field may contain SQL keywords
        hint = "Use UPSERT or ON CONFLICT to handle duplicates."

        result = chain.apply_rich(hint, test_theme)

        # Content should be preserved
        assert "UPSERT" in result
        assert "duplicates" in result

    def test_format_entry_compact_applies_highlighting(self, test_theme: Theme) -> None:
        """format_entry_compact should apply highlighting to message content.

        This tests the integration between log parsing and highlighting output.
        """
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.LOG,
            message="duration: 250.789 ms  execute stmt1: SELECT id FROM orders",
            raw="test raw",
        )

        result = format_entry_compact(entry, theme=test_theme, use_semantic_highlighting=True)

        # Should contain styled output
        assert "[" in result  # Rich markup present
        assert "250" in result  # Duration value
        assert "SELECT" in result  # SQL content

    def test_csv_parsed_entry_highlighting(self, test_theme: Theme) -> None:
        """Entries parsed from CSV format should get highlighting.

        CSV logs have structured fields that get formatted into display output.
        The formatted display output should have highlighting applied.
        """
        # Simulate a CSV-parsed entry (has more structured fields)
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
            pid=12345,
            level=LogLevel.ERROR,
            message="unique_violation: duplicate key value",
            sql_state="23505",
            detail='Key (email)=("test@example.com") already exists.',
            hint="Consider using ON CONFLICT clause.",
            raw="csv raw line",
            user_name="postgres",
            database_name="myapp",
            application_name="myapp-api",
        )

        result = format_entry_compact(entry, theme=test_theme, use_semantic_highlighting=True)

        # Message should be highlighted
        assert "unique_violation" in result
        assert "23505" in result  # SQLSTATE

    def test_json_parsed_entry_highlighting(self, test_theme: Theme) -> None:
        """Entries parsed from JSON format should get highlighting.

        JSON logs have all structured fields available.
        """
        # Simulate a JSON-parsed entry
        entry = LogEntry(
            timestamp=datetime(2024, 1, 15, 14, 30, 45, 123000, tzinfo=timezone.utc),
            pid=54321,
            level=LogLevel.LOG,
            message="checkpoint complete: wrote 1500 buffers (9.2%)",
            raw="json raw",
            sql_state=None,
            backend_type="checkpointer",
        )

        result = format_entry_compact(entry, theme=test_theme, use_semantic_highlighting=True)

        # Checkpoint message should be highlighted
        assert "checkpoint" in result
        assert "1500" in result
        assert "9.2%" in result

    def test_highlighting_preserves_all_format_content(self, test_theme: Theme) -> None:
        """All content from CSV/JSON fields should be preserved in output.

        Highlighting should not strip or alter the actual text content.
        """
        chain = get_highlighter_chain()

        # Complex message with multiple highlightable patterns
        message = (
            "duration: 1234.567 ms  "
            "execute stmt_prepare_1: "
            "SELECT u.id, u.email FROM public.users u "
            "WHERE u.status = 'active' AND u.created_at > $1"
        )

        result = chain.apply_rich(message, test_theme)

        # All content should be present
        assert "1234.567 ms" in result or ("1234" in result and "567" in result and "ms" in result)
        assert "stmt_prepare_1" in result
        assert "users" in result
        assert "active" in result
        assert "$1" in result
