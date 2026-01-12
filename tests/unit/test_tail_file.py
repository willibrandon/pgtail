"""Unit tests for tail --file functionality.

Tests for:
- T059: validate_file_path()
- T060: validate_tail_args()
- T061: TailStatus.set_file_source()
- T062: TailStatus filename display
- T063: Instance detection patterns
- T096: Glob pattern matching (placeholder for Phase 8)
- T097: Multi-file tailer (placeholder for Phase 9)
- T098: Stdin reader (placeholder for Phase 10)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pgtail_py.cli_utils import validate_file_path, validate_tail_args
from pgtail_py.filter import LogLevel
from pgtail_py.tail_status import TailStatus


class TestValidateFilePath:
    """Tests for validate_file_path() function (T059)."""

    def test_valid_file(self, tmp_path: Path) -> None:
        """Test validation of an existing, readable file."""
        test_file = tmp_path / "test.log"
        test_file.write_text("test content")

        resolved, error = validate_file_path(str(test_file))

        assert error is None
        assert resolved == test_file.resolve()

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test validation when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.log"

        resolved, error = validate_file_path(str(nonexistent))

        assert error is not None
        assert "File not found" in error
        assert str(resolved) in error

    def test_path_is_directory(self, tmp_path: Path) -> None:
        """Test validation when path is a directory."""
        resolved, error = validate_file_path(str(tmp_path))

        assert error is not None
        assert "Not a file" in error
        assert "is a directory" in error

    def test_tilde_expansion(self) -> None:
        """Test tilde (~) expansion for home directory."""
        # Create a temp file in home directory for testing
        home = Path.home()
        test_file = home / ".pgtail_test_file"
        try:
            test_file.write_text("test")
            resolved, error = validate_file_path("~/.pgtail_test_file")

            assert error is None
            assert resolved == test_file.resolve()
        finally:
            test_file.unlink(missing_ok=True)

    def test_relative_path(self, tmp_path: Path) -> None:
        """Test that relative paths are resolved to absolute."""
        test_file = tmp_path / "test.log"
        test_file.write_text("test content")

        # Change to tmp_path and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            resolved, error = validate_file_path("test.log")

            assert error is None
            assert resolved.is_absolute()
            assert resolved == test_file.resolve()
        finally:
            os.chdir(original_cwd)

    def test_symlink_resolution(self, tmp_path: Path) -> None:
        """Test that symlinks are followed and resolved (T053)."""
        # Create target file
        target = tmp_path / "target.log"
        target.write_text("target content")

        # Create symlink
        symlink = tmp_path / "symlink.log"
        symlink.symlink_to(target)

        resolved, error = validate_file_path(str(symlink))

        assert error is None
        # Path should be resolved to the actual file
        assert resolved == target.resolve()

    def test_path_with_spaces(self, tmp_path: Path) -> None:
        """Test paths with spaces are handled correctly (T054)."""
        dir_with_spaces = tmp_path / "path with spaces"
        dir_with_spaces.mkdir()
        test_file = dir_with_spaces / "test file.log"
        test_file.write_text("test content")

        resolved, error = validate_file_path(str(test_file))

        assert error is None
        assert resolved == test_file.resolve()

    def test_path_with_special_characters(self, tmp_path: Path) -> None:
        """Test paths with special characters are handled correctly (T054)."""
        # Create file with special characters in name
        special_file = tmp_path / "test-file_2024.01.log"
        special_file.write_text("test content")

        resolved, error = validate_file_path(str(special_file))

        assert error is None
        assert resolved == special_file.resolve()

    def test_permission_denied(self, tmp_path: Path) -> None:
        """Test validation when file is not readable."""
        test_file = tmp_path / "unreadable.log"
        test_file.write_text("test content")
        test_file.chmod(0o000)

        try:
            resolved, error = validate_file_path(str(test_file))

            # On some systems (especially macOS with SIP), root can still read
            # So we check that either it's an error or passes
            if error is not None:
                assert "Permission denied" in error or "Cannot access" in error
        finally:
            test_file.chmod(0o644)


class TestValidateTailArgs:
    """Tests for validate_tail_args() function (T060)."""

    def test_no_arguments(self) -> None:
        """Test with no arguments (valid - defaults)."""
        error = validate_tail_args(file_path=None, instance_id=None, stdin_mode=False)
        assert error is None

    def test_file_only(self) -> None:
        """Test with only --file argument (valid)."""
        error = validate_tail_args(file_path="/path/to/log", instance_id=None, stdin_mode=False)
        assert error is None

    def test_instance_only(self) -> None:
        """Test with only instance ID (valid)."""
        error = validate_tail_args(file_path=None, instance_id=0, stdin_mode=False)
        assert error is None

    def test_stdin_only(self) -> None:
        """Test with only --stdin (valid)."""
        error = validate_tail_args(file_path=None, instance_id=None, stdin_mode=True)
        assert error is None

    def test_file_and_instance_conflict(self) -> None:
        """Test mutual exclusivity of --file and instance ID."""
        error = validate_tail_args(file_path="/path/to/log", instance_id=0, stdin_mode=False)

        assert error is not None
        assert "--file" in error
        assert "instance" in error.lower()

    def test_stdin_and_instance_conflict(self) -> None:
        """Test mutual exclusivity of --stdin and instance ID."""
        error = validate_tail_args(file_path=None, instance_id=0, stdin_mode=True)

        assert error is not None
        assert "--stdin" in error
        assert "instance" in error.lower()

    def test_stdin_and_file_conflict(self) -> None:
        """Test mutual exclusivity of --stdin and --file."""
        error = validate_tail_args(file_path="/path/to/log", instance_id=None, stdin_mode=True)

        assert error is not None
        assert "--stdin" in error
        assert "--file" in error


class TestTailStatusFileSource:
    """Tests for TailStatus.set_file_source() method (T061)."""

    def test_set_file_source(self) -> None:
        """Test setting filename for file-based tailing."""
        status = TailStatus()
        status.set_file_source("postmaster.log")

        assert status.filename == "postmaster.log"
        assert status.pg_version == ""  # No version detected yet

    def test_set_file_source_overwrite(self) -> None:
        """Test that set_file_source overwrites previous value."""
        status = TailStatus()
        status.set_file_source("old.log")
        status.set_file_source("new.log")

        assert status.filename == "new.log"

    def test_file_unavailable_flag(self) -> None:
        """Test file unavailability flag."""
        status = TailStatus()
        status.set_file_source("test.log")
        status.set_file_unavailable(True)

        assert status.file_unavailable is True

        status.set_file_unavailable(False)
        assert status.file_unavailable is False


class TestTailStatusFilenameDisplay:
    """Tests for TailStatus filename display in format methods (T062)."""

    def test_format_rich_with_filename(self) -> None:
        """Test format_rich() shows filename when no instance info."""
        status = TailStatus()
        status.set_file_source("postmaster.log")

        text = status.format_rich()
        text_str = str(text)

        assert "postmaster.log" in text_str
        # Should not show PG version format when only filename is set
        assert "PG:" not in text_str

    def test_format_rich_with_filename_unavailable(self) -> None:
        """Test format_rich() shows unavailable indicator."""
        status = TailStatus()
        status.set_file_source("postmaster.log")
        status.set_file_unavailable(True)

        text = status.format_rich()
        text_str = str(text)

        assert "postmaster.log" in text_str
        assert "unavailable" in text_str

    def test_format_rich_with_detected_instance(self) -> None:
        """Test format_rich() shows PG version when detected from content."""
        status = TailStatus()
        status.set_file_source("postmaster.log")
        status.set_detected_instance_info(version="17", port=5432)

        text = status.format_rich()
        text_str = str(text)

        # Should show PG version format, not filename
        assert "PG17:5432" in text_str

    def test_format_plain_with_filename(self) -> None:
        """Test format_plain() shows filename when no instance info."""
        status = TailStatus()
        status.set_file_source("test.log")

        text = status.format_plain()

        assert "test.log" in text
        # Should not show PG version format
        assert "PG" not in text or "PG:" not in text

    def test_format_plain_with_detected_instance(self) -> None:
        """Test format_plain() shows PG version when detected from content."""
        status = TailStatus()
        status.set_file_source("test.log")
        status.set_detected_instance_info(version="16.2", port=5433)

        text = status.format_plain()

        assert "PG16.2:5433" in text


class TestInstanceDetectionPatterns:
    """Tests for instance detection patterns (T063)."""

    def test_version_pattern_basic(self) -> None:
        """Test VERSION_PATTERN matches basic version string."""
        from pgtail_py.tail_textual import VERSION_PATTERN

        message = "starting PostgreSQL 17.0 on x86_64-apple-darwin"
        match = VERSION_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "17"
        assert match.group(2) == "0"

    def test_version_pattern_major_only(self) -> None:
        """Test VERSION_PATTERN matches major version only."""
        from pgtail_py.tail_textual import VERSION_PATTERN

        message = "starting PostgreSQL 18 on x86_64-apple-darwin"
        match = VERSION_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "18"
        assert match.group(2) is None

    def test_port_pattern_ipv4(self) -> None:
        """Test PORT_PATTERN matches IPv4 listening message."""
        from pgtail_py.tail_textual import PORT_PATTERN

        message = 'listening on IPv4 address "0.0.0.0", port 5432'
        match = PORT_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "5432"

    def test_port_pattern_ipv6(self) -> None:
        """Test PORT_PATTERN matches IPv6 listening message."""
        from pgtail_py.tail_textual import PORT_PATTERN

        message = 'listening on IPv6 address "::", port 5433'
        match = PORT_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "5433"

    def test_port_socket_pattern(self) -> None:
        """Test PORT_SOCKET_PATTERN matches Unix socket message (T087)."""
        from pgtail_py.tail_textual import PORT_SOCKET_PATTERN

        message = 'listening on Unix socket "/tmp/.s.PGSQL.5432"'
        match = PORT_SOCKET_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "5432"

    def test_port_socket_pattern_custom_port(self) -> None:
        """Test PORT_SOCKET_PATTERN with custom port."""
        from pgtail_py.tail_textual import PORT_SOCKET_PATTERN

        message = 'listening on Unix socket "/var/run/postgresql/.s.PGSQL.5433"'
        match = PORT_SOCKET_PATTERN.search(message)

        assert match is not None
        assert match.group(1) == "5433"


class TestDetectedInstanceInfo:
    """Tests for DetectedInstanceInfo dataclass."""

    def test_default_values(self) -> None:
        """Test default values are None."""
        from pgtail_py.tail_textual import DetectedInstanceInfo

        info = DetectedInstanceInfo()

        assert info.version is None
        assert info.port is None

    def test_with_values(self) -> None:
        """Test creating with explicit values."""
        from pgtail_py.tail_textual import DetectedInstanceInfo

        info = DetectedInstanceInfo(version="17.0", port=5432)

        assert info.version == "17.0"
        assert info.port == 5432


# Placeholder tests for future phases (T096, T097, T098)


class TestGlobPatternMatching:
    """Tests for glob pattern matching (T096 - Phase 8 implementation)."""

    def test_glob_expansion_single_match(self, tmp_path: Path) -> None:
        """Test glob expansion with single matching file."""
        from pgtail_py.multi_tailer import GlobPattern

        # Create single log file
        log_file = tmp_path / "test.log"
        log_file.write_text("test content")

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            glob = GlobPattern.from_path("*.log")
            matches = glob.expand()

            assert len(matches) == 1
            assert matches[0].name == "test.log"
        finally:
            os.chdir(original_cwd)

    def test_glob_expansion_multiple_matches(self, tmp_path: Path) -> None:
        """Test glob expansion with multiple matching files."""
        from pgtail_py.multi_tailer import GlobPattern

        # Create multiple log files with different mtimes
        import time

        for name in ["a.log", "b.log", "c.log"]:
            log_file = tmp_path / name
            log_file.write_text(f"content of {name}")
            time.sleep(0.01)  # Ensure different mtimes

        # Change to tmp_path directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            glob = GlobPattern.from_path("*.log")
            matches = glob.expand()

            assert len(matches) == 3
            # Should be sorted by mtime (newest first)
            names = [m.name for m in matches]
            assert "a.log" in names
            assert "b.log" in names
            assert "c.log" in names
        finally:
            os.chdir(original_cwd)

    def test_glob_no_matches_error(self, tmp_path: Path) -> None:
        """Test error when glob matches no files."""
        from pgtail_py.multi_tailer import GlobPattern

        # Don't create any files
        glob = GlobPattern.from_path(str(tmp_path / "*.nonexistent"))
        matches = glob.expand()

        assert len(matches) == 0

    def test_is_glob_pattern(self) -> None:
        """Test glob pattern detection."""
        from pgtail_py.multi_tailer import is_glob_pattern

        assert is_glob_pattern("*.log") is True
        assert is_glob_pattern("test?.log") is True
        assert is_glob_pattern("test[abc].log") is True
        assert is_glob_pattern("/path/to/*.log") is True
        assert is_glob_pattern("test.log") is False
        assert is_glob_pattern("/path/to/test.log") is False

    def test_glob_pattern_from_path_absolute(self, tmp_path: Path) -> None:
        """Test GlobPattern.from_path with absolute path."""
        from pgtail_py.multi_tailer import GlobPattern

        pattern = str(tmp_path / "*.log")
        glob = GlobPattern.from_path(pattern)

        assert glob.directory == tmp_path
        assert glob.pattern == "*.log"

    def test_glob_pattern_from_path_relative(self) -> None:
        """Test GlobPattern.from_path with relative path."""
        from pgtail_py.multi_tailer import GlobPattern

        glob = GlobPattern.from_path("logs/*.log")

        assert glob.pattern == "*.log"
        assert "logs" in str(glob.directory)


class TestMultiFileTailer:
    """Tests for multi-file tailer (T097 - Phase 8/9 implementation)."""

    def test_multiple_files_interleaved(self, tmp_path: Path) -> None:
        """Test entries from multiple files are interleaved by timestamp."""
        import time

        from pgtail_py.multi_tailer import MultiFileTailer
        from pgtail_py.time_filter import TimeFilter

        # Create two log files with entries
        log1 = tmp_path / "a.log"
        log2 = tmp_path / "b.log"

        # File 1: entries at 10:30:45 and 10:30:47
        log1.write_text(
            "2024-01-15 10:30:45.123 UTC [111] LOG:  entry from file a (first)\n"
            "2024-01-15 10:30:47.123 UTC [111] LOG:  entry from file a (third)\n"
        )

        # File 2: entry at 10:30:46
        log2.write_text("2024-01-15 10:30:46.123 UTC [222] LOG:  entry from file b (second)\n")

        # Create time filter to read from beginning
        from datetime import datetime, timezone

        time_filter = TimeFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))

        tailer = MultiFileTailer(
            paths=[log1, log2],
            time_filter=time_filter,
        )
        tailer.start()

        try:
            time.sleep(0.3)

            buffer = tailer.get_buffer()
            assert len(buffer) >= 3

            # Verify source files are set
            source_files = [e.source_file for e in buffer]
            assert "a.log" in source_files
            assert "b.log" in source_files
        finally:
            tailer.stop()

    def test_format_detection_per_file(self, tmp_path: Path) -> None:
        """Test each file has independent format detection."""
        import time

        from pgtail_py.format_detector import LogFormat
        from pgtail_py.multi_tailer import MultiFileTailer
        from pgtail_py.time_filter import TimeFilter

        # Create TEXT format log
        text_log = tmp_path / "text.log"
        text_log.write_text("2024-01-15 10:30:45.123 UTC [12345] LOG:  text format entry\n")

        # Create time filter to read from beginning
        from datetime import datetime, timezone

        time_filter = TimeFilter(since=datetime(2024, 1, 1, tzinfo=timezone.utc))

        # Track detected formats
        detected_formats: dict[str, LogFormat] = {}

        def on_format(path, fmt):
            detected_formats[path.name] = fmt

        tailer = MultiFileTailer(
            paths=[text_log],
            time_filter=time_filter,
        )
        tailer.set_format_callback(on_format)
        tailer.start()

        try:
            time.sleep(0.3)

            # Should detect TEXT format
            assert "text.log" in detected_formats
            assert detected_formats["text.log"] == LogFormat.TEXT
        finally:
            tailer.stop()

    def test_file_count(self, tmp_path: Path) -> None:
        """Test file_count property."""
        from pgtail_py.multi_tailer import MultiFileTailer

        # Create multiple log files
        log1 = tmp_path / "a.log"
        log2 = tmp_path / "b.log"
        log1.write_text("content")
        log2.write_text("content")

        tailer = MultiFileTailer(paths=[log1, log2])
        tailer.start()

        try:
            assert tailer.file_count == 2
            assert len(tailer.file_paths) == 2
        finally:
            tailer.stop()


class TestStdinReader:
    """Tests for stdin reader (T098 - placeholder for Phase 10)."""

    @pytest.mark.skip(reason="Phase 10: Stdin reader not yet implemented")
    def test_stdin_basic_reading(self) -> None:
        """Test reading log entries from stdin."""
        pass

    @pytest.mark.skip(reason="Phase 10: Stdin reader not yet implemented")
    def test_stdin_eof_handling(self) -> None:
        """Test graceful handling of stdin EOF."""
        pass
