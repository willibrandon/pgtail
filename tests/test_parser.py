"""Tests for pgtail_py.parser module."""



from pgtail_py.filter import LogLevel
from pgtail_py.parser import parse_log_line


class TestParseLogLine:
    """Tests for parse_log_line function."""

    def test_standard_log_line(self) -> None:
        """Test parsing a standard PostgreSQL log line."""
        line = "2024-01-15 10:30:45.123 UTC [12345] LOG:  database system is ready"
        entry = parse_log_line(line)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2024
        assert entry.timestamp.month == 1
        assert entry.timestamp.day == 15
        assert entry.timestamp.hour == 10
        assert entry.timestamp.minute == 30
        assert entry.timestamp.second == 45
        assert entry.level == LogLevel.LOG
        assert entry.message == "database system is ready"
        assert entry.pid == 12345
        assert entry.raw == line

    def test_error_level(self) -> None:
        """Test parsing an ERROR level log line."""
        line = "2024-01-15 10:30:45.123 UTC [12345] ERROR:  connection failed"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.ERROR
        assert entry.message == "connection failed"

    def test_warning_level(self) -> None:
        """Test parsing a WARNING level log line."""
        line = "2024-01-15 10:30:45.123 UTC [12345] WARNING:  deprecated feature"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.WARNING
        assert entry.message == "deprecated feature"

    def test_fatal_level(self) -> None:
        """Test parsing a FATAL level log line."""
        line = "2024-01-15 10:30:45.123 UTC [12345] FATAL:  server crashed"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.FATAL
        assert entry.message == "server crashed"

    def test_debug_levels(self) -> None:
        """Test parsing DEBUG level log lines."""
        for i in range(1, 6):
            level_name = f"DEBUG{i}"
            line = f"2024-01-15 10:30:45.123 UTC [12345] {level_name}:  debug message"
            entry = parse_log_line(line)
            assert entry.level == getattr(LogLevel, level_name)

    def test_unparseable_line(self) -> None:
        """Test that unparseable lines return LOG level with raw preserved."""
        line = "This is not a PostgreSQL log line"
        entry = parse_log_line(line)

        assert entry.timestamp is None
        assert entry.level == LogLevel.LOG
        assert entry.message == line
        assert entry.raw == line
        assert entry.pid is None

    def test_continuation_line(self) -> None:
        """Test parsing a continuation line (no timestamp)."""
        line = "\tStack trace: line 42"
        entry = parse_log_line(line)

        assert entry.timestamp is None
        assert entry.level == LogLevel.LOG
        assert entry.message == line
        assert entry.raw == line

    def test_empty_line(self) -> None:
        """Test parsing an empty line."""
        entry = parse_log_line("")
        assert entry.message == ""
        assert entry.level == LogLevel.LOG

    def test_line_with_newline(self) -> None:
        """Test that trailing newlines are stripped."""
        line = "2024-01-15 10:30:45.123 UTC [12345] LOG:  message\n"
        entry = parse_log_line(line)

        assert not entry.raw.endswith("\n")
        assert entry.message == "message"

    def test_timestamp_without_milliseconds(self) -> None:
        """Test parsing timestamp without milliseconds."""
        line = "2024-01-15 10:30:45 UTC [12345] LOG:  message"
        entry = parse_log_line(line)

        assert entry.timestamp is not None
        assert entry.timestamp.second == 45

    def test_notice_level(self) -> None:
        """Test parsing NOTICE level."""
        line = "2024-01-15 10:30:45.123 UTC [12345] NOTICE:  important notice"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.NOTICE
        assert entry.message == "important notice"

    def test_info_level(self) -> None:
        """Test parsing INFO level."""
        line = "2024-01-15 10:30:45.123 UTC [12345] INFO:  information message"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.INFO
        assert entry.message == "information message"

    def test_panic_level(self) -> None:
        """Test parsing PANIC level."""
        line = "2024-01-15 10:30:45.123 UTC [12345] PANIC:  system panic"
        entry = parse_log_line(line)

        assert entry.level == LogLevel.PANIC
        assert entry.message == "system panic"
