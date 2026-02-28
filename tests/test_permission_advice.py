"""Tests for pgtail_py.permission_advice module."""

from pgtail_py.permission_advice import (
    get_conf_permission_advice,
    get_log_permission_advice,
    get_logs_not_found_advice,
)


class TestGetLogPermissionAdvice:
    """Tests for get_log_permission_advice()."""

    def test_returns_list_of_strings(self) -> None:
        lines = get_log_permission_advice()
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)
        assert len(lines) > 0

    def test_linux_plain_text(self) -> None:
        lines = get_log_permission_advice(rich_markup=False, platform="linux")
        text = "\n".join(lines)
        assert "log_file_mode = 0640" in text
        assert "sudo usermod -aG postgres $USER" in text
        assert "/var/log/postgresql" in text
        assert "icacls" not in text
        assert "Administrator" not in text

    def test_linux_rich_markup(self) -> None:
        lines = get_log_permission_advice(rich_markup=True, platform="linux")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert "[dim]" in text
        assert "log_file_mode = 0640" in text
        assert "sudo usermod -aG postgres $USER" in text

    def test_macos_uses_homebrew_path(self) -> None:
        lines = get_log_permission_advice(rich_markup=False, platform="darwin")
        text = "\n".join(lines)
        assert "/usr/local/var/log/postgresql" in text
        assert "log_file_mode = 0640" in text
        assert "sudo usermod -aG postgres $USER" in text

    def test_macos_rich_markup(self) -> None:
        lines = get_log_permission_advice(rich_markup=True, platform="darwin")
        text = "\n".join(lines)
        assert "/usr/local/var/log/postgresql" in text
        assert "[cyan]" in text

    def test_windows_plain_text(self) -> None:
        lines = get_log_permission_advice(rich_markup=False, platform="win32")
        text = "\n".join(lines)
        assert "Administrator" in text
        assert "icacls" in text
        assert "C:/PgLogs" in text
        assert "services.msc" in text
        # Must NOT contain Unix-specific advice
        assert "sudo" not in text
        assert "log_file_mode" not in text
        assert "usermod" not in text

    def test_windows_rich_markup(self) -> None:
        lines = get_log_permission_advice(rich_markup=True, platform="win32")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert "Administrator" in text
        assert "icacls" in text
        assert "services.msc" in text
        assert "sudo" not in text

    def test_no_0644_anywhere(self) -> None:
        """Ensure 0644 is never suggested (0640 is the correct recommendation)."""
        for plat in ("linux", "darwin", "win32"):
            for markup in (True, False):
                lines = get_log_permission_advice(rich_markup=markup, platform=plat)
                text = "\n".join(lines)
                assert "0644" not in text, f"Found 0644 on {plat} markup={markup}"


class TestGetConfPermissionAdvice:
    """Tests for get_conf_permission_advice()."""

    def test_returns_list_of_strings(self) -> None:
        lines = get_conf_permission_advice("/etc/postgresql/17/main/postgresql.conf")
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)

    def test_linux_includes_conf_path(self) -> None:
        conf = "/etc/postgresql/17/main/postgresql.conf"
        lines = get_conf_permission_advice(conf, rich_markup=False, platform="linux")
        text = "\n".join(lines)
        assert conf in text
        assert "sudo -u postgres" in text

    def test_linux_rich_markup(self) -> None:
        conf = "/etc/postgresql/17/main/postgresql.conf"
        lines = get_conf_permission_advice(conf, rich_markup=True, platform="linux")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert conf in text

    def test_windows_plain_text(self) -> None:
        conf = r"C:\Program Files\PostgreSQL\17\data\postgresql.conf"
        lines = get_conf_permission_advice(conf, rich_markup=False, platform="win32")
        text = "\n".join(lines)
        assert "Administrator" in text
        assert "icacls" in text
        assert conf in text
        assert "sudo" not in text

    def test_windows_rich_markup(self) -> None:
        conf = r"C:\Program Files\PostgreSQL\17\data\postgresql.conf"
        lines = get_conf_permission_advice(conf, rich_markup=True, platform="win32")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert "Administrator" in text

    def test_macos_plain_text(self) -> None:
        conf = "/usr/local/var/lib/postgresql/17/postgresql.conf"
        lines = get_conf_permission_advice(conf, rich_markup=False, platform="darwin")
        text = "\n".join(lines)
        assert "sudo -u postgres" in text
        assert conf in text


class TestGetLogsNotFoundAdvice:
    """Tests for get_logs_not_found_advice()."""

    def test_returns_list_of_strings(self) -> None:
        lines = get_logs_not_found_advice()
        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)

    def test_linux_plain_text(self) -> None:
        lines = get_logs_not_found_advice(rich_markup=False, platform="linux")
        text = "\n".join(lines)
        assert "restricted data directory" in text
        assert "log_file_mode = 0640" in text
        assert "/var/log/postgresql" in text

    def test_linux_rich_markup(self) -> None:
        lines = get_logs_not_found_advice(rich_markup=True, platform="linux")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert "log_file_mode = 0640" in text

    def test_macos_uses_homebrew_path(self) -> None:
        lines = get_logs_not_found_advice(rich_markup=False, platform="darwin")
        text = "\n".join(lines)
        assert "/usr/local/var/log/postgresql" in text

    def test_windows_plain_text(self) -> None:
        lines = get_logs_not_found_advice(rich_markup=False, platform="win32")
        text = "\n".join(lines)
        assert "logging_collector = on" in text
        assert "services.msc" in text
        assert "Administrator" in text
        assert "C:/PgLogs" in text
        assert "sudo" not in text
        assert "log_file_mode" not in text

    def test_windows_rich_markup(self) -> None:
        lines = get_logs_not_found_advice(rich_markup=True, platform="win32")
        text = "\n".join(lines)
        assert "[cyan]" in text
        assert "logging_collector = on" in text
        assert "services.msc" in text

    def test_no_0644_anywhere(self) -> None:
        """Ensure 0644 is never suggested."""
        for plat in ("linux", "darwin", "win32"):
            for markup in (True, False):
                lines = get_logs_not_found_advice(rich_markup=markup, platform=plat)
                text = "\n".join(lines)
                assert "0644" not in text, f"Found 0644 on {plat} markup={markup}"
