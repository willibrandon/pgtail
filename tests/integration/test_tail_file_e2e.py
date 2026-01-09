"""Integration tests for tail --file functionality.

End-to-end tests with real temporary log files:
- T064: tail --file with relative path
- T065: tail --file with absolute path
- T066: tail --file --since combined
- T067: tail --file error cases
- T068: file-based CSV format detection
- T069: file-based JSON format detection
- T086: tail --file without path argument (usage error)
- T090-T095: Multi-file and stdin tests (placeholders for Phases 8-10)
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pgtail_py.cli_utils import validate_file_path, validate_tail_args
from pgtail_py.format_detector import LogFormat, detect_format
from pgtail_py.parser import LogEntry, parse_log_line
from pgtail_py.tailer import LogTailer
from pgtail_py.time_filter import TimeFilter

if TYPE_CHECKING:
    pass


# Sample PostgreSQL log entries for testing
SAMPLE_TEXT_LOG = """\
2024-01-15 10:30:45.123 UTC [12345] LOG:  database system is ready to accept connections
2024-01-15 10:30:46.456 UTC [12346] LOG:  starting PostgreSQL 17.0 on x86_64-apple-darwin
2024-01-15 10:30:47.789 UTC [12345] ERROR:  duplicate key value violates unique constraint
2024-01-15 10:30:48.012 UTC [12345] WARNING:  connection reset by peer
"""

# PostgreSQL CSV log format: 26 columns
# 0:log_time,1:user_name,2:database_name,3:process_id,4:connection_from,5:session_id,6:session_line_num,
# 7:command_tag,8:session_start_time,9:virtual_transaction_id,10:transaction_id,11:error_severity,
# 12:sql_state_code,13:message,14:detail,15:hint,16:internal_query,17:internal_query_pos,18:context,
# 19:query,20:query_pos,21:location,22:application_name,23:backend_type,24:leader_pid,25:query_id
SAMPLE_CSV_LOG = """\
2024-01-15 10:30:45.123 UTC,myuser,mydb,12345,192.168.1.1:55432,5ef2a.1,1,SELECT,2024-01-15 10:30:00.000 UTC,3/100,500,LOG,00000,database system is ready,,,,,,,,,myapp,client backend,,
2024-01-15 10:30:46.456 UTC,myuser,mydb,12346,192.168.1.1:55433,5ef2b.2,2,INSERT,2024-01-15 10:30:00.000 UTC,3/101,501,ERROR,23505,duplicate key value violates unique constraint,Key (id)=(1) already exists.,,,,,,,,myapp,client backend,,
"""

# PostgreSQL JSON log format (PG15+)
SAMPLE_JSON_LOG = """\
{"timestamp":"2024-01-15 10:30:45.123 UTC","user":"myuser","dbname":"mydb","pid":12345,"remote_host":"192.168.1.1","remote_port":"55432","session_id":"5ef2a","line_num":1,"ps":"SELECT","session_start":"2024-01-15 10:30:00.000 UTC","vxid":"3/100","txid":"500","error_severity":"LOG","state_code":"00000","message":"database system is ready to accept connections"}
{"timestamp":"2024-01-15 10:30:46.456 UTC","user":"myuser","dbname":"mydb","pid":12346,"remote_host":"192.168.1.1","remote_port":"55433","session_id":"5ef2b","line_num":2,"ps":"INSERT","session_start":"2024-01-15 10:30:00.000 UTC","vxid":"3/101","txid":"501","error_severity":"ERROR","state_code":"23505","message":"duplicate key value violates unique constraint","detail":"Key (id)=(1) already exists.","application_name":"myapp","backend_type":"client backend"}
"""


class TestTailFileRelativePath:
    """Integration tests for tail --file with relative path (T064)."""

    def test_validate_relative_path(self, tmp_path: Path) -> None:
        """Test that relative paths are resolved correctly."""
        # Create test file
        test_file = tmp_path / "test.log"
        test_file.write_text(SAMPLE_TEXT_LOG)

        # Change to tmp_path directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            resolved, error = validate_file_path("test.log")

            assert error is None
            assert resolved.is_absolute()
            assert resolved.exists()
        finally:
            os.chdir(original_cwd)

    def test_tailer_with_relative_path(self, tmp_path: Path) -> None:
        """Test LogTailer works with resolved relative path."""
        import time

        # Create test file
        test_file = tmp_path / "test.log"
        test_file.write_text(SAMPLE_TEXT_LOG)

        # Create tailer with absolute path and time filter to read from start
        # Use a time in the past so all entries are included
        time_filter = TimeFilter(
            since=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        tailer = LogTailer(log_path=test_file.resolve(), time_filter=time_filter)
        tailer.start()

        try:
            # Give tailer time to read entries
            time.sleep(0.3)

            # Get buffered entries
            buffer = tailer.get_buffer()
            assert len(buffer) > 0, "Expected entries in buffer"
        finally:
            tailer.stop()


class TestTailFileAbsolutePath:
    """Integration tests for tail --file with absolute path (T065)."""

    def test_validate_absolute_path(self, tmp_path: Path) -> None:
        """Test validation of absolute path."""
        test_file = tmp_path / "test.log"
        test_file.write_text(SAMPLE_TEXT_LOG)

        resolved, error = validate_file_path(str(test_file.resolve()))

        assert error is None
        assert resolved == test_file.resolve()

    def test_tailer_reads_historical_entries(self, tmp_path: Path) -> None:
        """Test LogTailer reads existing entries with time filter."""
        import time

        test_file = tmp_path / "test.log"
        test_file.write_text(SAMPLE_TEXT_LOG)

        # Create time filter that includes all entries (from 2024-01-01)
        time_filter = TimeFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))

        tailer = LogTailer(log_path=test_file.resolve(), time_filter=time_filter)
        tailer.start()

        try:
            time.sleep(0.3)

            # Get all buffered entries
            buffer = tailer.get_buffer()
            assert len(buffer) >= 4, f"Expected at least 4 entries, got {len(buffer)}"
        finally:
            tailer.stop()


class TestTailFileSinceCombined:
    """Integration tests for tail --file --since combined (T066)."""

    def test_tailer_with_time_filter(self, tmp_path: Path) -> None:
        """Test LogTailer respects time filter."""
        import time

        test_file = tmp_path / "test.log"
        test_file.write_text(SAMPLE_TEXT_LOG)

        # Create time filter for entries after a specific time
        # The test log has timestamps from 2024-01-15, so filter for that date
        time_filter = TimeFilter(
            since=datetime(2024, 1, 15, 10, 30, 46, tzinfo=timezone.utc)
        )

        tailer = LogTailer(log_path=test_file.resolve(), time_filter=time_filter)
        tailer.start()

        try:
            time.sleep(0.3)

            # Get buffered entries - should only include entries after filter time
            buffer = tailer.get_buffer()
            # All entries with timestamp >= 10:30:46 should be included
            for entry in buffer:
                if entry.timestamp:
                    # The timestamp may be naive or UTC-aware; compare second
                    assert entry.timestamp.second >= 46 or entry.timestamp.minute > 30 or entry.timestamp.hour > 10
        finally:
            tailer.stop()


class TestTailFileErrorCases:
    """Integration tests for tail --file error cases (T067)."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test error when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.log"

        resolved, error = validate_file_path(str(nonexistent))

        assert error is not None
        assert "File not found" in error

    def test_path_is_directory(self, tmp_path: Path) -> None:
        """Test error when path is a directory."""
        resolved, error = validate_file_path(str(tmp_path))

        assert error is not None
        assert "is a directory" in error

    def test_mutual_exclusivity_file_and_instance(self) -> None:
        """Test error when both --file and instance ID provided."""
        error = validate_tail_args(file_path="/path/to/log", instance_id=0)

        assert error is not None
        assert "--file" in error
        assert "instance" in error.lower()


class TestFileBasedCsvFormat:
    """Integration tests for file-based CSV format detection (T068)."""

    def test_csv_format_detection(self, tmp_path: Path) -> None:
        """Test CSV format is auto-detected from file content."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(SAMPLE_CSV_LOG)

        # Read first line and detect format
        with open(test_file) as f:
            first_line = f.readline()

        detected = detect_format(first_line)
        assert detected == LogFormat.CSV

    def test_csv_parsing(self, tmp_path: Path) -> None:
        """Test CSV log entries are parsed correctly."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(SAMPLE_CSV_LOG)

        entries: list[LogEntry] = []
        with open(test_file) as f:
            for line in f:
                if line.strip():
                    entry = parse_log_line(line, LogFormat.CSV)
                    entries.append(entry)

        assert len(entries) >= 2
        # Check parsed fields (CSV has user_name at index 1, database_name at index 2)
        assert entries[0].user_name == "myuser"
        assert entries[0].database_name == "mydb"
        assert entries[1].sql_state == "23505"

    def test_tailer_csv_format(self, tmp_path: Path) -> None:
        """Test LogTailer detects and uses CSV format."""
        import time

        test_file = tmp_path / "test.csv"
        test_file.write_text(SAMPLE_CSV_LOG)

        time_filter = TimeFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))
        tailer = LogTailer(log_path=test_file.resolve(), time_filter=time_filter)
        tailer.start()

        try:
            time.sleep(0.3)

            # Check format was detected as CSV
            assert tailer.format == LogFormat.CSV

            # Check entries have CSV-specific fields
            buffer = tailer.get_buffer()
            assert len(buffer) >= 2
            assert buffer[0].format == LogFormat.CSV
        finally:
            tailer.stop()


class TestFileBasedJsonFormat:
    """Integration tests for file-based JSON format detection (T069)."""

    def test_json_format_detection(self, tmp_path: Path) -> None:
        """Test JSON format is auto-detected from file content."""
        test_file = tmp_path / "test.json"
        test_file.write_text(SAMPLE_JSON_LOG)

        # Read first line and detect format
        with open(test_file) as f:
            first_line = f.readline()

        detected = detect_format(first_line)
        assert detected == LogFormat.JSON

    def test_json_parsing(self, tmp_path: Path) -> None:
        """Test JSON log entries are parsed correctly."""
        test_file = tmp_path / "test.json"
        test_file.write_text(SAMPLE_JSON_LOG)

        entries: list[LogEntry] = []
        with open(test_file) as f:
            for line in f:
                if line.strip():
                    entry = parse_log_line(line, LogFormat.JSON)
                    entries.append(entry)

        assert len(entries) >= 2
        # Check parsed fields
        assert entries[0].pid == 12345
        # JSON uses state_code field which maps to sql_state
        assert entries[1].sql_state == "23505"

    def test_tailer_json_format(self, tmp_path: Path) -> None:
        """Test LogTailer detects and uses JSON format."""
        import time

        test_file = tmp_path / "test.json"
        test_file.write_text(SAMPLE_JSON_LOG)

        time_filter = TimeFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))
        tailer = LogTailer(log_path=test_file.resolve(), time_filter=time_filter)
        tailer.start()

        try:
            time.sleep(0.3)

            # Check format was detected as JSON
            assert tailer.format == LogFormat.JSON

            # Check entries have JSON-specific format marker
            buffer = tailer.get_buffer()
            assert len(buffer) >= 2
            assert buffer[0].format == LogFormat.JSON
        finally:
            tailer.stop()


class TestTailFileNoPathArgument:
    """Integration tests for tail --file without path argument (T086)."""

    def test_empty_path_validation(self) -> None:
        """Test that empty path string fails validation."""
        resolved, error = validate_file_path("")

        assert error is not None
        # Empty path resolves to current directory
        assert "directory" in error.lower() or "not found" in error.lower()


# Placeholder tests for future phases


class TestGlobPatternExpansion:
    """Integration tests for glob pattern expansion (T090 - placeholder for Phase 8)."""

    @pytest.mark.skip(reason="Phase 8: Glob patterns not yet implemented")
    def test_glob_expansion_finds_files(self) -> None:
        """Test glob pattern finds matching files."""
        pass

    @pytest.mark.skip(reason="Phase 8: Glob patterns not yet implemented")
    def test_glob_expansion_sorts_by_mtime(self) -> None:
        """Test glob results are sorted by modification time."""
        pass


class TestGlobNoMatches:
    """Integration tests for glob pattern with no matches (T091 - placeholder for Phase 8)."""

    @pytest.mark.skip(reason="Phase 8: Glob patterns not yet implemented")
    def test_glob_no_matches_error_message(self) -> None:
        """Test error message when glob matches nothing."""
        pass


class TestMultipleFileArguments:
    """Integration tests for multiple --file arguments (T092 - placeholder for Phase 9)."""

    @pytest.mark.skip(reason="Phase 9: Multiple files not yet implemented")
    def test_multiple_files_accepted(self) -> None:
        """Test multiple --file arguments are accepted."""
        pass


class TestMultiFileTimestampInterleaving:
    """Integration tests for multi-file timestamp interleaving (T093 - placeholder for Phase 9)."""

    @pytest.mark.skip(reason="Phase 9: Multi-file interleaving not yet implemented")
    def test_entries_interleaved_by_timestamp(self) -> None:
        """Test entries from multiple files are interleaved by timestamp."""
        pass


class TestStdinPipeInput:
    """Integration tests for stdin pipe input (T094 - placeholder for Phase 10)."""

    @pytest.mark.skip(reason="Phase 10: Stdin support not yet implemented")
    def test_stdin_reads_piped_data(self) -> None:
        """Test reading log data from stdin pipe."""
        pass


class TestStdinEofHandling:
    """Integration tests for stdin EOF handling (T095 - placeholder for Phase 10)."""

    @pytest.mark.skip(reason="Phase 10: Stdin support not yet implemented")
    def test_stdin_eof_exits_gracefully(self) -> None:
        """Test graceful exit when stdin reaches EOF."""
        pass
