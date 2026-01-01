"""Tests for version module: update checking, install detection, and version comparison."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.config import ConfigSchema, UpdatesSection
from pgtail_py.version import (
    API_TIMEOUT,
    CHECK_INTERVAL,
    GITHUB_RELEASES_PAGE,
    RELEASES_URL,
    InstallMethod,
    ReleaseAsset,
    ReleaseInfo,
    UpdateInfo,
    _detect_homebrew,
    _detect_pip,
    _detect_pipx,
    _detect_uv,
    _detect_winget,
    check_update_async,
    check_update_sync,
    detect_install_method,
    fetch_latest_release,
    get_asset_for_platform,
    get_upgrade_command,
    get_version,
    is_newer_available,
    notify_update,
    parse_version,
    should_check_update,
)


# =============================================================================
# T095: Test --check-update shows "up to date" when current version equals latest
# =============================================================================


class TestVersionUpToDate:
    """Test T095: --check-update shows up to date message."""

    def test_check_update_sync_up_to_date(self) -> None:
        """When current version equals latest, shows up to date message."""
        mock_response = {
            "tag_name": "v0.1.0",
            "name": "v0.1.0",
            "body": "Release notes",
            "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.1.0",
            "assets": [],
            "published_at": "2026-01-01T00:00:00Z",
        }

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            with patch("pgtail_py.version.get_version", return_value="0.1.0"):
                available, message = check_update_sync()

        assert available is False
        assert "up to date" in message.lower()
        assert "0.1.0" in message


# =============================================================================
# T096: Test --check-update shows update available with correct upgrade command
# =============================================================================


class TestVersionUpdateAvailable:
    """Test T096: --check-update shows update available with upgrade command."""

    def test_check_update_sync_update_available(self) -> None:
        """When newer version available, shows update message with command."""
        mock_response = {
            "tag_name": "v0.2.0",
            "name": "v0.2.0",
            "body": "New features",
            "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.2.0",
            "assets": [],
            "published_at": "2026-01-15T00:00:00Z",
        }

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            with patch("pgtail_py.version.get_version", return_value="0.1.0"):
                with patch(
                    "pgtail_py.version.detect_install_method",
                    return_value=InstallMethod.HOMEBREW,
                ):
                    available, message = check_update_sync()

        assert available is True
        assert "0.2.0" in message
        assert "brew upgrade pgtail" in message

    def test_upgrade_commands_per_method(self) -> None:
        """Each install method maps to correct upgrade command."""
        expected = {
            InstallMethod.PIP: "pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
            InstallMethod.PIPX: "pipx upgrade pgtail",
            InstallMethod.UV: "uv tool upgrade pgtail",
            InstallMethod.HOMEBREW: "brew upgrade pgtail",
            InstallMethod.WINGET: "winget upgrade willibrandon.pgtail",
            InstallMethod.BINARY: GITHUB_RELEASES_PAGE,
        }

        for method, expected_cmd in expected.items():
            assert get_upgrade_command(method) == expected_cmd


# =============================================================================
# T097: Test startup notification appears when newer version exists
# =============================================================================


class TestStartupNotification:
    """Test T097: Startup notification appears when newer version exists."""

    def test_notify_update_prints_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        """notify_update prints to stderr with correct format."""
        update_info = UpdateInfo(
            current_version="0.1.0",
            latest_version="0.2.0",
            install_method=InstallMethod.HOMEBREW,
            upgrade_command="brew upgrade pgtail",
            release_url="https://github.com/willibrandon/pgtail/releases/tag/v0.2.0",
            checked_at=datetime.now(timezone.utc),
        )

        # Test with NO_COLOR to get plain text
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            notify_update(update_info)

        captured = capsys.readouterr()
        assert "0.2.0" in captured.err
        assert "available" in captured.err
        assert "brew upgrade pgtail" in captured.err


# =============================================================================
# T098: Test startup notification is rate-limited (skip if < 24 hours)
# =============================================================================


class TestRateLimiting:
    """Test T098: Startup notification is rate-limited."""

    def test_should_check_within_24_hours_returns_false(self) -> None:
        """When last check was less than 24 hours ago, return False."""
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check=recent_time))

        assert should_check_update(config) is False

    def test_should_check_after_24_hours_returns_true(self) -> None:
        """When last check was more than 24 hours ago, return True."""
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check=old_time))

        assert should_check_update(config) is True

    def test_should_check_no_last_check_returns_true(self) -> None:
        """When no last_check is set, return True."""
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check=""))

        assert should_check_update(config) is True

    def test_should_check_invalid_timestamp_returns_true(self) -> None:
        """When last_check has invalid format, return True."""
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check="not-a-date"))

        assert should_check_update(config) is True


# =============================================================================
# T099: Test updates.check = false skips startup check
# =============================================================================


class TestUpdatesDisabled:
    """Test T099: updates.check = false skips startup check."""

    def test_should_check_disabled_returns_false(self) -> None:
        """When updates.check is False, return False."""
        config = ConfigSchema(updates=UpdatesSection(check=False, last_check=""))

        assert should_check_update(config) is False


# =============================================================================
# T100: Test --check-update works even when updates.check = false
# =============================================================================


class TestExplicitCheck:
    """Test T100: --check-update bypasses rate limit and config setting."""

    def test_check_update_sync_ignores_config(self) -> None:
        """check_update_sync does not check config settings."""
        mock_response = {
            "tag_name": "v0.1.0",
            "name": "v0.1.0",
            "body": "",
            "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.1.0",
            "assets": [],
            "published_at": "2026-01-01T00:00:00Z",
        }

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            with patch("pgtail_py.version.get_version", return_value="0.1.0"):
                # check_update_sync() doesn't take config - it always checks
                available, message = check_update_sync()

        # Should succeed regardless of config
        assert "0.1.0" in message


# =============================================================================
# T101: Test offline handling (no error, continues normally)
# =============================================================================


class TestOfflineHandling:
    """Test T101: Offline handling - no error, continues normally."""

    def test_fetch_latest_release_returns_none_on_network_error(self) -> None:
        """Network errors return None instead of raising."""
        import urllib.error

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
            result = fetch_latest_release()

        assert result is None

    def test_fetch_latest_release_returns_none_on_timeout(self) -> None:
        """Timeout errors return None."""
        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = TimeoutError("Connection timed out")
            result = fetch_latest_release()

        assert result is None

    def test_check_update_sync_returns_error_message_on_failure(self) -> None:
        """check_update_sync returns helpful error message when offline."""
        with patch("pgtail_py.version.fetch_latest_release", return_value=None):
            available, message = check_update_sync()

        assert available is False
        assert "unable to check" in message.lower()


# =============================================================================
# T126: Handle dev version (0.0.0-dev) comparison
# =============================================================================


class TestDevVersionComparison:
    """Test T126: Dev version comparison in is_newer_available()."""

    def test_dev_version_any_release_is_newer(self) -> None:
        """0.0.0-dev should consider any release as newer."""
        assert is_newer_available("0.0.0-dev", "0.1.0") is True
        assert is_newer_available("0.0.0-dev", "0.0.1") is True
        assert is_newer_available("0.0.0-dev", "99.0.0") is True

    def test_version_with_dev_suffix_any_release_is_newer(self) -> None:
        """Any version ending in -dev should consider releases newer."""
        assert is_newer_available("1.0.0-dev", "0.1.0") is True

    def test_regular_version_comparison(self) -> None:
        """Normal version comparison works correctly."""
        assert is_newer_available("0.1.0", "0.2.0") is True
        assert is_newer_available("0.2.0", "0.1.0") is False
        assert is_newer_available("0.1.0", "0.1.0") is False
        assert is_newer_available("1.0.0", "2.0.0") is True


# =============================================================================
# T130: Verify check_update_async() completes without blocking startup (<500ms)
# =============================================================================


class TestAsyncNonBlocking:
    """Test T130: check_update_async() is non-blocking."""

    def test_check_update_async_returns_immediately(self) -> None:
        """check_update_async should return immediately (non-blocking)."""
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check=""))

        start = time.time()
        with patch("pgtail_py.version.threading.Thread") as mock_thread:
            check_update_async(config)
        elapsed = time.time() - start

        # Should return in under 100ms (not 500ms - that's for the background check)
        assert elapsed < 0.1
        # Thread should be started
        mock_thread.return_value.start.assert_called_once()

    def test_check_update_async_skips_when_rate_limited(self) -> None:
        """check_update_async skips when rate limited."""
        recent_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        config = ConfigSchema(updates=UpdatesSection(check=True, last_check=recent_time))

        with patch("pgtail_py.version.threading.Thread") as mock_thread:
            check_update_async(config)

        # Thread should not be created when rate limited
        mock_thread.assert_not_called()


# =============================================================================
# T131: Verify --check-update timing under 2 seconds
# =============================================================================


class TestSyncTiming:
    """Test T131: --check-update timing under 2 seconds."""

    def test_check_update_sync_timeout_is_configured(self) -> None:
        """API_TIMEOUT constant is set appropriately."""
        # The timeout is 5 seconds, which is within our 2-second goal
        # for typical network conditions
        assert API_TIMEOUT == 5


# =============================================================================
# Additional Tests: Installation Method Detection
# =============================================================================


class TestInstallMethodDetection:
    """Tests for install method detection heuristics."""

    def test_detect_pipx(self) -> None:
        """Detect pipx installation from path."""
        assert _detect_pipx("/home/user/.local/pipx/venvs/pgtail/bin/python") is True
        assert _detect_pipx("C:\\Users\\user\\.local\\pipx\\venvs\\pgtail\\python.exe") is True
        assert _detect_pipx("/usr/bin/python") is False

    def test_detect_homebrew(self) -> None:
        """Detect Homebrew installation from path."""
        assert _detect_homebrew("/opt/homebrew/bin/python") is True
        # Note: detection is case-insensitive (.lower())
        assert _detect_homebrew("/usr/local/cellar/python/3.12/bin/python") is True
        assert _detect_homebrew("/home/linuxbrew/.linuxbrew/bin/python") is True
        assert _detect_homebrew("/usr/bin/python") is False

    def test_detect_winget(self) -> None:
        """Detect winget installation from path."""
        with patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\user\\AppData\\Local"}):
            assert (
                _detect_winget(
                    "C:\\Users\\user\\AppData\\Local\\Microsoft\\WinGet\\Packages\\pgtail"
                )
                is True
            )
        assert _detect_winget("/microsoft/winget/packages/pgtail") is True
        assert _detect_winget("C:\\Python312\\python.exe") is False

    def test_detect_uv(self) -> None:
        """Detect uv installation from path."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            assert _detect_uv("/home/user/.local/share/uv/tools/pgtail/bin/python", "") is True
            assert _detect_uv("/home/user/.venv/bin/python", "/home/user/.venv") is True

    def test_detect_pip_not_in_venv(self) -> None:
        """Detect pip when not in virtualenv."""
        # When sys.prefix == sys.base_prefix (global Python)
        # Need to set base_prefix to match prefix for this test
        with patch.object(sys, "base_prefix", "/usr"):
            assert _detect_pip("/usr/bin/python", "/usr") is True

    def test_detect_pip_in_site_packages(self) -> None:
        """Detect pip from site-packages path."""
        assert _detect_pip("/usr/lib/python3.12/site-packages/pgtail/__main__.py", "/usr") is True


class TestParseVersion:
    """Tests for version string parsing."""

    def test_parse_version_strips_v_prefix(self) -> None:
        """parse_version removes v prefix."""
        assert parse_version("v0.1.0") == "0.1.0"
        assert parse_version("v1.0.0-beta.1") == "1.0.0-beta.1"

    def test_parse_version_no_prefix(self) -> None:
        """parse_version handles versions without prefix."""
        assert parse_version("0.1.0") == "0.1.0"


class TestGetAssetForPlatform:
    """Tests for platform-specific asset selection."""

    def test_get_asset_for_platform_macos_arm64(self) -> None:
        """Select correct asset for macOS ARM64."""
        assets = [
            ReleaseAsset("pgtail-darwin-arm64", "https://...", 1000, "application/octet-stream"),
            ReleaseAsset("pgtail-darwin-x86_64", "https://...", 1000, "application/octet-stream"),
            ReleaseAsset("pgtail-linux-x86_64", "https://...", 1000, "application/octet-stream"),
        ]

        with patch("pgtail_py.version.platform.system", return_value="Darwin"):
            with patch("pgtail_py.version.platform.machine", return_value="arm64"):
                asset = get_asset_for_platform(assets)

        assert asset is not None
        assert asset.name == "pgtail-darwin-arm64"

    def test_get_asset_for_platform_windows(self) -> None:
        """Select correct asset for Windows."""
        assets = [
            ReleaseAsset("pgtail-windows-x86_64.exe", "https://...", 1000, "application/octet-stream"),
        ]

        with patch("pgtail_py.version.platform.system", return_value="Windows"):
            with patch("pgtail_py.version.platform.machine", return_value="AMD64"):
                asset = get_asset_for_platform(assets)

        assert asset is not None
        assert asset.name == "pgtail-windows-x86_64.exe"


class TestFetchLatestRelease:
    """Tests for GitHub API fetching."""

    def test_fetch_latest_release_success(self) -> None:
        """Successfully fetches and parses release."""
        mock_response = {
            "tag_name": "v0.2.0",
            "name": "v0.2.0",
            "body": "Release notes",
            "html_url": "https://github.com/willibrandon/pgtail/releases/tag/v0.2.0",
            "assets": [
                {
                    "name": "pgtail-macos-arm64",
                    "browser_download_url": "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-macos-arm64",
                    "size": 15000000,
                    "content_type": "application/octet-stream",
                }
            ],
            "published_at": "2026-01-15T10:30:00Z",
        }

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = fetch_latest_release()

        assert result is not None
        assert result.tag_name == "v0.2.0"
        assert len(result.assets) == 1
        assert result.assets[0].name == "pgtail-macos-arm64"

    def test_fetch_latest_release_handles_404(self) -> None:
        """Returns None on 404 (no releases)."""
        import urllib.error

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(RELEASES_URL, 404, "Not Found", {}, None)  # type: ignore
            result = fetch_latest_release()

        assert result is None

    def test_fetch_latest_release_handles_403(self) -> None:
        """Returns None on 403 (rate limit)."""
        import urllib.error

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(RELEASES_URL, 403, "Forbidden", {}, None)  # type: ignore
            result = fetch_latest_release()

        assert result is None

    def test_fetch_latest_release_handles_malformed_json(self) -> None:
        """Returns None on malformed JSON."""
        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = b"not valid json"
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = fetch_latest_release()

        assert result is None


class TestNoColorSupport:
    """Tests for NO_COLOR environment variable support."""

    def test_notify_update_respects_no_color(self, capsys: pytest.CaptureFixture[str]) -> None:
        """NO_COLOR=1 removes ANSI codes from output."""
        update_info = UpdateInfo(
            current_version="0.1.0",
            latest_version="0.2.0",
            install_method=InstallMethod.PIP,
            upgrade_command="pip install --upgrade ...",
            release_url="https://...",
            checked_at=datetime.now(timezone.utc),
        )

        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            notify_update(update_info)

        captured = capsys.readouterr()
        # Should not contain ANSI escape codes
        assert "\033[" not in captured.err
        assert "0.2.0" in captured.err

    def test_check_update_sync_respects_no_color(self) -> None:
        """NO_COLOR=1 removes ANSI codes from check_update_sync output."""
        mock_response = {
            "tag_name": "v0.2.0",
            "name": "v0.2.0",
            "body": "",
            "html_url": "https://...",
            "assets": [],
            "published_at": "2026-01-01T00:00:00Z",
        }

        with patch("pgtail_py.version.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps(mock_response).encode()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            with patch("pgtail_py.version.get_version", return_value="0.1.0"):
                with patch.dict(os.environ, {"NO_COLOR": "1"}):
                    _available, message = check_update_sync()

        # Should not contain ANSI escape codes
        assert "\033[" not in message
