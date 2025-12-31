"""Tests for pgtail_py.detector module."""

import tempfile
from pathlib import Path

from pgtail_py.detector import get_log_info, get_port, get_version, read_current_logfiles


class TestGetVersion:
    """Tests for get_version function."""

    def test_reads_pg_version(self) -> None:
        """Test reading version from PG_VERSION file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            pg_version = data_dir / "PG_VERSION"
            pg_version.write_text("16\n")

            version = get_version(data_dir)
            assert version == "16"

    def test_version_with_minor(self) -> None:
        """Test reading version with minor version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            pg_version = data_dir / "PG_VERSION"
            pg_version.write_text("15.4\n")

            version = get_version(data_dir)
            assert version == "15.4"

    def test_missing_pg_version(self) -> None:
        """Test returns 'unknown' when PG_VERSION missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            version = get_version(data_dir)
            assert version == "unknown"

    def test_nonexistent_directory(self) -> None:
        """Test returns 'unknown' for nonexistent directory."""
        version = get_version(Path("/nonexistent/path"))
        assert version == "unknown"


class TestGetLogInfo:
    """Tests for get_log_info function."""

    def test_logging_disabled(self) -> None:
        """Test returns None when logging_collector is off."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = off\n")

            log_path, log_directory, enabled = get_log_info(data_dir)
            assert log_path is None
            assert log_directory is None
            assert enabled is False

    def test_logging_enabled_no_logs(self) -> None:
        """Test returns None path but enabled=True when no log files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = on\nlog_directory = 'log'\n")

            log_path, log_directory, enabled = get_log_info(data_dir)
            assert log_path is None
            assert log_directory is None  # No log dir yet
            assert enabled is True

    def test_logging_enabled_with_logs(self) -> None:
        """Test returns log path when logs exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = on\nlog_directory = 'log'\n")

            log_dir = data_dir / "log"
            log_dir.mkdir()
            log_file = log_dir / "postgresql-2024-01-15.log"
            log_file.write_text("log content")

            log_path, log_directory, enabled = get_log_info(data_dir)
            assert log_path is not None
            assert log_path.name == "postgresql-2024-01-15.log"
            assert log_directory == log_dir
            assert enabled is True

    def test_missing_conf(self) -> None:
        """Test returns None when postgresql.conf missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            log_path, log_directory, enabled = get_log_info(data_dir)
            assert log_path is None
            assert log_directory is None
            assert enabled is False

    def test_absolute_log_directory(self) -> None:
        """Test handling absolute log_directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            log_dir = Path(tmpdir) / "custom_logs"
            log_dir.mkdir()

            conf = data_dir / "postgresql.conf"
            conf.write_text(f"logging_collector = on\nlog_directory = '{log_dir}'\n")

            log_file = log_dir / "postgresql.log"
            log_file.write_text("log content")

            log_path, log_directory, enabled = get_log_info(data_dir)
            assert log_path is not None
            assert log_directory == log_dir
            assert enabled is True


class TestReadCurrentLogfiles:
    """Tests for read_current_logfiles function."""

    def test_reads_stderr_log_absolute(self) -> None:
        """Test reading absolute stderr log path from current_logfiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            current_logfiles.write_text("stderr /var/log/postgresql/postgresql-2024-01-15.log\n")

            log_path = read_current_logfiles(data_dir)
            assert log_path is not None
            assert log_path == Path("/var/log/postgresql/postgresql-2024-01-15.log")

    def test_reads_stderr_log_relative(self) -> None:
        """Test reading relative stderr log path from current_logfiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            # This is what pgrx uses - relative path
            current_logfiles.write_text("stderr log/postgresql-2024-01-15.log\n")

            log_path = read_current_logfiles(data_dir)
            assert log_path is not None
            assert log_path == data_dir / "log" / "postgresql-2024-01-15.log"

    def test_reads_csvlog(self) -> None:
        """Test reading csvlog path from current_logfiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            current_logfiles.write_text("csvlog /var/log/postgresql/postgresql-2024-01-15.csv\n")

            log_path = read_current_logfiles(data_dir)
            assert log_path is not None
            assert str(log_path).endswith(".csv")

    def test_reads_jsonlog(self) -> None:
        """Test reading jsonlog path from current_logfiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            current_logfiles.write_text("jsonlog /var/log/postgresql/postgresql-2024-01-15.json\n")

            log_path = read_current_logfiles(data_dir)
            assert log_path is not None
            assert str(log_path).endswith(".json")

    def test_multiple_lines_returns_first_match(self) -> None:
        """Test that with multiple log destinations, first match is returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            current_logfiles.write_text(
                "stderr /var/log/postgresql/postgresql.log\n"
                "csvlog /var/log/postgresql/postgresql.csv\n"
            )

            log_path = read_current_logfiles(data_dir)
            assert log_path is not None
            assert str(log_path).endswith(".log")

    def test_missing_file_returns_none(self) -> None:
        """Test returns None when current_logfiles doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            log_path = read_current_logfiles(data_dir)
            assert log_path is None

    def test_invalid_format_returns_none(self) -> None:
        """Test returns None when file has invalid format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            current_logfiles = data_dir / "current_logfiles"
            current_logfiles.write_text("invalid content\n")

            log_path = read_current_logfiles(data_dir)
            assert log_path is None


class TestGetPort:
    """Tests for get_port function."""

    def test_reads_port(self) -> None:
        """Test reading port from postgresql.conf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("port = 5432\n")

            port = get_port(data_dir)
            assert port == 5432

    def test_port_with_quotes(self) -> None:
        """Test reading quoted port value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("port = '5433'\n")

            port = get_port(data_dir)
            assert port == 5433

    def test_missing_port(self) -> None:
        """Test returns None when port not configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = on\n")

            port = get_port(data_dir)
            assert port is None

    def test_missing_conf(self) -> None:
        """Test returns None when conf file missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            port = get_port(data_dir)
            assert port is None

    def test_nonexistent_directory(self) -> None:
        """Test returns None for nonexistent directory."""
        port = get_port(Path("/nonexistent/path"))
        assert port is None
