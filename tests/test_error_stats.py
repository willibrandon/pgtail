"""Tests for error statistics tracking."""

from datetime import datetime

import pytest

from pgtail_py.error_stats import (
    ERROR_LEVELS,
    SQLSTATE_CATEGORIES,
    SQLSTATE_NAMES,
    TRACKED_LEVELS,
    WARNING_LEVELS,
    ErrorEvent,
    ErrorStats,
    get_sqlstate_category,
    get_sqlstate_name,
)
from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry


# Test fixtures
@pytest.fixture
def sample_error_entry() -> LogEntry:
    """Create a sample ERROR log entry."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 30, 45),
        level=LogLevel.ERROR,
        message="duplicate key value violates unique constraint",
        raw="2024-01-15 10:30:45.123 UTC [12345] ERROR: duplicate key value",
        pid=12345,
        sql_state="23505",
        database_name="testdb",
        user_name="testuser",
    )


@pytest.fixture
def sample_warning_entry() -> LogEntry:
    """Create a sample WARNING log entry."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 31, 0),
        level=LogLevel.WARNING,
        message="could not open statistics file",
        raw="2024-01-15 10:31:00.000 UTC [12345] WARNING: could not open",
        pid=12345,
        sql_state=None,
        database_name="testdb",
        user_name="testuser",
    )


@pytest.fixture
def sample_log_entry() -> LogEntry:
    """Create a sample LOG level entry (should not be tracked)."""
    return LogEntry(
        timestamp=datetime(2024, 1, 15, 10, 32, 0),
        level=LogLevel.LOG,
        message="database system is ready",
        raw="2024-01-15 10:32:00.000 UTC [12345] LOG: database system is ready",
        pid=12345,
    )


class TestErrorLevelConstants:
    """Tests for error level constants."""

    def test_error_levels_contains_panic(self) -> None:
        assert LogLevel.PANIC in ERROR_LEVELS

    def test_error_levels_contains_fatal(self) -> None:
        assert LogLevel.FATAL in ERROR_LEVELS

    def test_error_levels_contains_error(self) -> None:
        assert LogLevel.ERROR in ERROR_LEVELS

    def test_error_levels_not_contains_warning(self) -> None:
        assert LogLevel.WARNING not in ERROR_LEVELS

    def test_warning_levels_contains_warning(self) -> None:
        assert LogLevel.WARNING in WARNING_LEVELS

    def test_tracked_levels_is_union(self) -> None:
        assert TRACKED_LEVELS == ERROR_LEVELS | WARNING_LEVELS


class TestGetSqlstateName:
    """Tests for get_sqlstate_name() function."""

    def test_known_code_returns_name(self) -> None:
        assert get_sqlstate_name("23505") == "unique_violation"

    def test_known_code_foreign_key(self) -> None:
        assert get_sqlstate_name("23503") == "foreign_key_violation"

    def test_known_code_syntax_error(self) -> None:
        assert get_sqlstate_name("42601") == "syntax_error"

    def test_unknown_code_returns_code(self) -> None:
        assert get_sqlstate_name("99999") == "99999"

    def test_empty_code_returns_empty(self) -> None:
        assert get_sqlstate_name("") == ""


class TestGetSqlstateCategory:
    """Tests for get_sqlstate_category() function."""

    def test_integrity_constraint_violation(self) -> None:
        assert get_sqlstate_category("23505") == "Integrity Constraint Violation"

    def test_syntax_error_category(self) -> None:
        assert get_sqlstate_category("42601") == "Syntax Error or Access Rule Violation"

    def test_insufficient_resources(self) -> None:
        assert get_sqlstate_category("53100") == "Insufficient Resources"

    def test_operator_intervention(self) -> None:
        assert get_sqlstate_category("57014") == "Operator Intervention"

    def test_system_error(self) -> None:
        assert get_sqlstate_category("58030") == "System Error"

    def test_unknown_category(self) -> None:
        assert get_sqlstate_category("99999") == "Unknown"

    def test_empty_code_returns_unknown(self) -> None:
        assert get_sqlstate_category("") == "Unknown"

    def test_single_char_returns_unknown(self) -> None:
        assert get_sqlstate_category("2") == "Unknown"


class TestSqlstateDicts:
    """Tests for SQLSTATE dictionaries."""

    def test_categories_has_common_classes(self) -> None:
        assert "23" in SQLSTATE_CATEGORIES  # Integrity Constraint
        assert "42" in SQLSTATE_CATEGORIES  # Syntax Error
        assert "53" in SQLSTATE_CATEGORIES  # Insufficient Resources
        assert "57" in SQLSTATE_CATEGORIES  # Operator Intervention
        assert "58" in SQLSTATE_CATEGORIES  # System Error

    def test_names_has_common_codes(self) -> None:
        assert "23505" in SQLSTATE_NAMES  # unique_violation
        assert "42P01" in SQLSTATE_NAMES  # undefined_table
        assert "57014" in SQLSTATE_NAMES  # query_canceled


class TestErrorEventFromEntry:
    """Tests for ErrorEvent.from_entry() classmethod."""

    def test_creates_event_with_all_fields(self, sample_error_entry: LogEntry) -> None:
        event = ErrorEvent.from_entry(sample_error_entry)

        assert event.timestamp == datetime(2024, 1, 15, 10, 30, 45)
        assert event.level == LogLevel.ERROR
        assert event.sql_state == "23505"
        assert "duplicate key" in event.message
        assert event.pid == 12345
        assert event.database == "testdb"
        assert event.user == "testuser"

    def test_handles_none_sql_state(self, sample_warning_entry: LogEntry) -> None:
        event = ErrorEvent.from_entry(sample_warning_entry)
        assert event.sql_state is None

    def test_truncates_long_message(self) -> None:
        long_message = "x" * 300
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message=long_message,
            raw="raw",
        )
        event = ErrorEvent.from_entry(entry)
        assert len(event.message) == 200

    def test_handles_none_timestamp(self) -> None:
        entry = LogEntry(
            timestamp=None,
            level=LogLevel.ERROR,
            message="test",
            raw="raw",
        )
        event = ErrorEvent.from_entry(entry)
        assert event.timestamp is not None  # Should default to now

    def test_handles_none_message(self) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message=None,  # type: ignore[arg-type]
            raw="raw",
        )
        event = ErrorEvent.from_entry(entry)
        assert event.message == ""


class TestErrorStatsAdd:
    """Tests for ErrorStats.add() method."""

    def test_add_error_increments_error_count(self, sample_error_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        assert stats.error_count == 1
        assert stats.warning_count == 0

    def test_add_warning_increments_warning_count(self, sample_warning_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_warning_entry)
        assert stats.error_count == 0
        assert stats.warning_count == 1

    def test_add_log_does_not_increment(self, sample_log_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_log_entry)
        assert stats.error_count == 0
        assert stats.warning_count == 0
        assert stats.is_empty()

    def test_add_updates_last_error_time(self, sample_error_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        assert stats.last_error_time == datetime(2024, 1, 15, 10, 30, 45)

    def test_add_warning_does_not_update_last_error_time(
        self, sample_warning_entry: LogEntry
    ) -> None:
        stats = ErrorStats()
        stats.add(sample_warning_entry)
        assert stats.last_error_time is None

    def test_add_multiple_errors(self, sample_error_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        stats.add(sample_error_entry)
        stats.add(sample_error_entry)
        assert stats.error_count == 3

    def test_add_fatal_counts_as_error(self) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.FATAL,
            message="fatal error",
            raw="raw",
        )
        stats = ErrorStats()
        stats.add(entry)
        assert stats.error_count == 1

    def test_add_panic_counts_as_error(self) -> None:
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.PANIC,
            message="panic",
            raw="raw",
        )
        stats = ErrorStats()
        stats.add(entry)
        assert stats.error_count == 1


class TestErrorStatsClear:
    """Tests for ErrorStats.clear() method."""

    def test_clear_resets_counts(
        self, sample_error_entry: LogEntry, sample_warning_entry: LogEntry
    ) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        stats.add(sample_warning_entry)
        stats.clear()

        assert stats.error_count == 0
        assert stats.warning_count == 0
        assert stats.is_empty()
        assert stats.last_error_time is None


class TestErrorStatsIsEmpty:
    """Tests for ErrorStats.is_empty() method."""

    def test_empty_initially(self) -> None:
        stats = ErrorStats()
        assert stats.is_empty()

    def test_not_empty_after_add(self, sample_error_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        assert not stats.is_empty()


class TestErrorStatsGetByLevel:
    """Tests for ErrorStats.get_by_level() method."""

    def test_returns_correct_counts(
        self, sample_error_entry: LogEntry, sample_warning_entry: LogEntry
    ) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        stats.add(sample_error_entry)
        stats.add(sample_warning_entry)

        by_level = stats.get_by_level()
        assert by_level[LogLevel.ERROR] == 2
        assert by_level[LogLevel.WARNING] == 1

    def test_empty_stats_returns_empty_dict(self) -> None:
        stats = ErrorStats()
        assert stats.get_by_level() == {}

    def test_multiple_levels(self) -> None:
        stats = ErrorStats()
        entries = [
            LogEntry(timestamp=datetime.now(), level=LogLevel.ERROR, message="e1", raw="r"),
            LogEntry(timestamp=datetime.now(), level=LogLevel.FATAL, message="f1", raw="r"),
            LogEntry(timestamp=datetime.now(), level=LogLevel.WARNING, message="w1", raw="r"),
        ]
        for entry in entries:
            stats.add(entry)

        by_level = stats.get_by_level()
        assert by_level[LogLevel.ERROR] == 1
        assert by_level[LogLevel.FATAL] == 1
        assert by_level[LogLevel.WARNING] == 1


class TestErrorStatsGetByCode:
    """Tests for ErrorStats.get_by_code() method."""

    def test_returns_counts_sorted_by_frequency(self) -> None:
        stats = ErrorStats()
        # Add 3 unique violations
        for _ in range(3):
            entry = LogEntry(
                timestamp=datetime.now(),
                level=LogLevel.ERROR,
                message="unique",
                raw="r",
                sql_state="23505",
            )
            stats.add(entry)

        # Add 1 syntax error
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="syntax",
            raw="r",
            sql_state="42601",
        )
        stats.add(entry)

        by_code = stats.get_by_code()
        codes = list(by_code.keys())

        # Most frequent first
        assert codes[0] == "23505"
        assert by_code["23505"] == 3
        assert codes[1] == "42601"
        assert by_code["42601"] == 1

    def test_none_sql_state_becomes_unknown(self, sample_warning_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_warning_entry)

        by_code = stats.get_by_code()
        assert "UNKNOWN" in by_code
        assert by_code["UNKNOWN"] == 1

    def test_empty_stats_returns_empty_dict(self) -> None:
        stats = ErrorStats()
        assert stats.get_by_code() == {}


class TestErrorStatsGetEventsByCode:
    """Tests for ErrorStats.get_events_by_code() method."""

    def test_returns_matching_events(self) -> None:
        stats = ErrorStats()
        entry1 = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="unique1",
            raw="r",
            sql_state="23505",
        )
        entry2 = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.ERROR,
            message="syntax",
            raw="r",
            sql_state="42601",
        )
        stats.add(entry1)
        stats.add(entry2)

        events = stats.get_events_by_code("23505")
        assert len(events) == 1
        assert events[0].sql_state == "23505"

    def test_returns_empty_for_no_matches(self, sample_error_entry: LogEntry) -> None:
        stats = ErrorStats()
        stats.add(sample_error_entry)
        events = stats.get_events_by_code("99999")
        assert events == []
