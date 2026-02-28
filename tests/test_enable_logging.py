"""Tests for pgtail_py.enable_logging module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from pgtail_py.enable_logging import enable_logging, read_postgresql_conf


class TestEnableLoggingStandardLayout:
    """Tests for enable_logging with standard PostgreSQL layout (config in data_dir)."""

    def test_enables_logging(self) -> None:
        """enable_logging sets logging_collector=on in standard layout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("#logging_collector = off\n")

            result = enable_logging(data_dir)

            assert result.success is True
            assert "logging_collector" in result.message.lower() or result.success
            # Verify the config was actually updated
            settings = read_postgresql_conf(conf)
            assert settings["logging_collector"] == "on"

    def test_already_enabled(self) -> None:
        """enable_logging reports already enabled when logging is on."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text(
                "logging_collector = on\n"
                "log_directory = 'log'\n"
                "log_filename = 'postgresql-%Y-%m-%d.log'\n"
            )

            result = enable_logging(data_dir)

            assert result.success is True
            assert "already" in result.message.lower()
            assert result.changes == []

    def test_conf_not_found(self) -> None:
        """enable_logging fails when no postgresql.conf exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            # Don't create postgresql.conf

            result = enable_logging(data_dir)

            assert result.success is False
            assert "not found" in result.message.lower()


class TestEnableLoggingDebianLayout:
    """Tests for enable_logging with Debian/Ubuntu layout."""

    def test_finds_debian_conf_via_config_path(self) -> None:
        """enable_logging uses config_path when provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate Debian layout: config in a different directory
            etc_dir = Path(tmpdir) / "etc"
            etc_dir.mkdir()
            conf = etc_dir / "postgresql.conf"
            conf.write_text("#logging_collector = off\n")

            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            result = enable_logging(data_dir, config_path=conf)

            assert result.success is True
            settings = read_postgresql_conf(conf)
            assert settings["logging_collector"] == "on"

    def test_finds_conf_via_find_postgresql_conf(self) -> None:
        """enable_logging falls back to find_postgresql_conf when config_path is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("#logging_collector = off\n")

            # config_path=None, should find via find_postgresql_conf
            result = enable_logging(data_dir, config_path=None)

            assert result.success is True
            settings = read_postgresql_conf(conf)
            assert settings["logging_collector"] == "on"

    def test_not_found_shows_checked_paths(self) -> None:
        """enable_logging shows paths that were checked when conf is not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "nonexistent"
            data_dir.mkdir()

            result = enable_logging(data_dir)

            assert result.success is False
            assert "not found" in result.message.lower()
            assert "Checked" in result.message


class TestEnableLoggingPermissionErrors:
    """Tests for permission error handling."""

    @patch("pgtail_py.permission_advice.sys")
    def test_read_permission_error_linux(self, mock_sys) -> None:
        """Permission error on read shows Linux-specific advice."""
        mock_sys.platform = "linux"
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = off\n")
            conf.chmod(0o000)

            try:
                result = enable_logging(data_dir)

                assert result.success is False
                assert "Permission denied" in result.message
                # Should contain Linux-specific advice, not "sudo chown $USER"
                assert "sudo -u postgres" in result.message
                assert "chown" not in result.message
            finally:
                conf.chmod(0o644)

    @patch("pgtail_py.permission_advice.sys")
    def test_read_permission_error_windows(self, mock_sys) -> None:
        """Permission error on read shows Windows-specific advice."""
        mock_sys.platform = "win32"
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("logging_collector = off\n")
            conf.chmod(0o000)

            try:
                result = enable_logging(data_dir)

                assert result.success is False
                assert "Permission denied" in result.message
                # Should contain Windows-specific advice
                assert "Administrator" in result.message
                assert "icacls" in result.message
                # Must NOT contain Unix-specific advice
                assert "sudo" not in result.message
            finally:
                conf.chmod(0o644)

    @patch("pgtail_py.permission_advice.sys")
    def test_write_permission_error_linux(self, mock_sys) -> None:
        """Permission error on write shows Linux-specific advice."""
        mock_sys.platform = "linux"
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            conf = data_dir / "postgresql.conf"
            conf.write_text("#logging_collector = off\n")
            # Make readable but not writable
            conf.chmod(0o444)

            try:
                result = enable_logging(data_dir)

                assert result.success is False
                assert "Permission denied" in result.message
                assert "sudo -u postgres" in result.message
            finally:
                conf.chmod(0o644)
