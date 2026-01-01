"""Version reading, update checking, and installation method detection for pgtail.

This module provides:
- get_version(): Read installed version from package metadata
- InstallMethod: Enum for installation methods (pip, pipx, uv, homebrew, winget, binary)
- detect_install_method(): Detect how pgtail was installed
- get_upgrade_command(): Get the appropriate upgrade command for the installation method
- UpdateInfo, ReleaseAsset, ReleaseInfo: Dataclasses for update checking
- fetch_latest_release(): Fetch latest release from GitHub API
- is_newer_available(): Check if a newer version is available
- check_update_async(): Non-blocking startup update check
- check_update_sync(): Blocking update check for --check-update flag
"""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import ssl
import sys
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pgtail_py.config import ConfigSchema

# GitHub Releases API endpoint
RELEASES_URL = "https://api.github.com/repos/willibrandon/pgtail/releases/latest"

# API request timeout in seconds
API_TIMEOUT = 5

# Rate limit interval for startup checks
CHECK_INTERVAL = timedelta(hours=24)

# Repository URL for direct downloads
GITHUB_RELEASES_PAGE = "https://github.com/willibrandon/pgtail/releases"


def get_version() -> str:
    """Get the installed version of pgtail.

    Returns:
        Version string (e.g., "0.1.0") or "0.0.0-dev" if not installed as a package.
    """
    try:
        return importlib.metadata.version("pgtail")
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0-dev"


class InstallMethod(Enum):
    """Installation method for pgtail.

    Each value corresponds to a different way pgtail can be installed,
    and determines the appropriate upgrade command to show to users.
    """

    PIP = "pip"
    PIPX = "pipx"
    UV = "uv"
    HOMEBREW = "homebrew"
    WINGET = "winget"
    BINARY = "binary"


@dataclass
class UpdateInfo:
    """Information about an available update.

    Attributes:
        current_version: Currently installed version (e.g., "0.1.0")
        latest_version: Latest available version (e.g., "0.2.0")
        install_method: Detected installation method
        upgrade_command: Platform-specific upgrade command
        release_url: URL to release page
        checked_at: When the check was performed
    """

    current_version: str
    latest_version: str
    install_method: InstallMethod
    upgrade_command: str
    release_url: str
    checked_at: datetime


@dataclass
class ReleaseAsset:
    """Binary asset from GitHub Release.

    Attributes:
        name: Asset filename (e.g., "pgtail-macos-arm64")
        browser_download_url: Direct download URL
        size: File size in bytes
        content_type: MIME type
    """

    name: str
    browser_download_url: str
    size: int
    content_type: str


@dataclass
class ReleaseInfo:
    """GitHub Release information.

    Attributes:
        tag_name: Git tag (e.g., "v0.1.0")
        name: Release title
        body: Release notes (markdown)
        html_url: URL to release page
        assets: Attached binary files
        published_at: Publication timestamp
    """

    tag_name: str
    name: str
    body: str
    html_url: str
    assets: list[ReleaseAsset]
    published_at: datetime


# =============================================================================
# Installation Method Detection (T069-T075)
# =============================================================================


def detect_install_method() -> InstallMethod:
    """Detect how pgtail was installed using heuristic-based detection.

    Detection order (first match wins):
    1. pipx - sys.executable in .local/pipx/venvs/pgtail
    2. Homebrew - sys.executable under /opt/homebrew, /usr/local/Cellar, /home/linuxbrew
    3. winget - Windows with LOCALAPPDATA/Microsoft/WinGet path or registry
    4. uv - sys.executable in .venv or uv tool path
    5. pip - sys.prefix contains site-packages (not in venv)
    6. binary - fallback when no other method detected

    Returns:
        InstallMethod enum value representing detected installation method.
    """
    executable = sys.executable
    prefix = sys.prefix

    # T071: pipx detection - check if sys.executable contains .local/pipx/venvs/pgtail
    if _detect_pipx(executable):
        return InstallMethod.PIPX

    # T073: Homebrew detection - check common Homebrew paths
    if _detect_homebrew(executable):
        return InstallMethod.HOMEBREW

    # T074: winget detection - Windows-specific check
    if sys.platform == "win32" and _detect_winget(executable):
        return InstallMethod.WINGET

    # T072: uv detection - check for .venv or uv tool markers
    if _detect_uv(executable, prefix):
        return InstallMethod.UV

    # T070: pip detection - check if site-packages in prefix but not in venv
    if _detect_pip(executable, prefix):
        return InstallMethod.PIP

    # T075: binary fallback - no other method detected
    return InstallMethod.BINARY


def _detect_pipx(executable: str) -> bool:
    """Check if installed via pipx.

    pipx installs packages in ~/.local/pipx/venvs/<package>/.
    On Windows: %USERPROFILE%/.local/pipx/venvs/<package>/

    Args:
        executable: Path to Python executable.

    Returns:
        True if pipx installation detected.
    """
    # Normalize path separators for cross-platform
    normalized = executable.replace("\\", "/").lower()
    return ".local/pipx/venvs/pgtail" in normalized or "/pipx/venvs/pgtail/" in normalized


def _detect_homebrew(executable: str) -> bool:
    """Check if installed via Homebrew.

    Homebrew installs to:
    - macOS ARM: /opt/homebrew/
    - macOS Intel: /usr/local/Cellar/
    - Linux: /home/linuxbrew/.linuxbrew/

    Args:
        executable: Path to Python executable.

    Returns:
        True if Homebrew installation detected.
    """
    homebrew_prefixes = (
        "/opt/homebrew",
        "/usr/local/cellar",
        "/home/linuxbrew",
        "/home/linuxbrew/.linuxbrew",
    )
    normalized = executable.lower()
    return any(normalized.startswith(prefix) for prefix in homebrew_prefixes)


def _detect_winget(executable: str) -> bool:
    """Check if installed via winget.

    winget portable apps are installed to:
    - %LOCALAPPDATA%/Microsoft/WinGet/Packages/
    - Or detected via registry

    Args:
        executable: Path to Python executable.

    Returns:
        True if winget installation detected.
    """
    # Check LOCALAPPDATA/Microsoft/WinGet path
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        winget_path = os.path.join(localappdata, "Microsoft", "WinGet", "Packages")
        if executable.lower().startswith(winget_path.lower()):
            return True

    # Check if executable is in a known winget location
    normalized = executable.replace("\\", "/").lower()

    # Registry check is complex and may require admin; skip for now
    # The above heuristics should cover most cases
    return "/microsoft/winget/" in normalized


def _detect_uv(executable: str, prefix: str) -> bool:
    """Check if installed via uv.

    uv tool installs to:
    - ~/.local/share/uv/tools/<package>/
    - Or uses .venv directories

    Args:
        executable: Path to Python executable.
        prefix: sys.prefix value.

    Returns:
        True if uv installation detected.
    """
    normalized = executable.replace("\\", "/").lower()

    # Check for uv tool installation path
    if "/uv/tools/pgtail/" in normalized or "/.local/share/uv/tools/" in normalized:
        return True

    # Check for .venv with uv marker file
    venv_path = os.path.dirname(os.path.dirname(executable))
    uv_marker = os.path.join(venv_path, ".uv")
    if os.path.exists(uv_marker):
        return True

    # Check if running from uv-created venv (common pattern)
    return "/.venv/" in normalized and os.path.exists(os.path.join(venv_path, "uv.lock"))


def _detect_pip(executable: str, prefix: str) -> bool:
    """Check if installed via pip (global or user install).

    pip installs to site-packages. We detect this when:
    - Not in a virtualenv (sys.prefix == sys.base_prefix)
    - Or in a recognizable pip install location

    Args:
        executable: Path to Python executable.
        prefix: sys.prefix value.

    Returns:
        True if pip installation detected.
    """
    # Check if we're NOT in a virtualenv
    base_prefix = getattr(sys, "base_prefix", sys.prefix)

    # If prefix equals base_prefix, not in a venv (likely pip global/user)
    if prefix == base_prefix:
        return True

    # Also detect if explicitly in site-packages path
    normalized = executable.replace("\\", "/").lower()
    return "/site-packages/" in normalized


# =============================================================================
# Upgrade Command Generation (T076)
# =============================================================================


def get_upgrade_command(method: InstallMethod) -> str:
    """Get the appropriate upgrade command for the installation method.

    Args:
        method: The detected installation method.

    Returns:
        Shell command string or URL for upgrading.
    """
    commands = {
        InstallMethod.PIP: "pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
        InstallMethod.PIPX: "pipx upgrade pgtail",
        InstallMethod.UV: "uv tool upgrade pgtail",
        InstallMethod.HOMEBREW: "brew upgrade pgtail",
        InstallMethod.WINGET: "winget upgrade willibrandon.pgtail",
        InstallMethod.BINARY: GITHUB_RELEASES_PAGE,
    }
    return commands[method]


# =============================================================================
# GitHub API Functions (T077-T080)
# =============================================================================


def _get_ssl_context() -> ssl.SSLContext | None:
    """Get SSL context with certifi CA bundle for PyInstaller compatibility."""
    try:
        # PyInstaller bundles certifi data at _MEIPASS/certifi/cacert.pem
        if hasattr(sys, "_MEIPASS"):
            cacert_path = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")  # type: ignore[attr-defined]
            if os.path.exists(cacert_path):
                return ssl.create_default_context(cafile=cacert_path)

        # Fall back to certifi module (normal Python environment)
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return None


def fetch_latest_release() -> ReleaseInfo | None:
    """Fetch latest release from GitHub Releases API.

    Makes a GET request to GitHub API with proper headers and timeout.
    Handles all errors silently by returning None.

    Returns:
        ReleaseInfo if successful, None on any error.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"pgtail/{get_version()}",
    }

    req = urllib.request.Request(RELEASES_URL, headers=headers)
    ssl_context = _get_ssl_context()

    if os.environ.get("PGTAIL_DEBUG"):
        print(f"DEBUG: ssl_context={ssl_context}", file=sys.stderr)
        if hasattr(sys, "_MEIPASS"):
            cacert = os.path.join(sys._MEIPASS, "certifi", "cacert.pem")  # type: ignore[attr-defined]
            print(f"DEBUG: _MEIPASS={sys._MEIPASS}", file=sys.stderr)  # type: ignore[attr-defined]
            print(f"DEBUG: cacert exists={os.path.exists(cacert)}", file=sys.stderr)

    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT, context=ssl_context) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
            return _parse_release_response(data)
    except urllib.error.HTTPError as e:
        # 403 (rate limit), 404 (no releases), etc.
        if os.environ.get("PGTAIL_DEBUG"):
            print(f"DEBUG: HTTPError: {e}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        # Network errors, DNS failures, SSL errors, etc.
        if os.environ.get("PGTAIL_DEBUG"):
            print(f"DEBUG: URLError: {e}", file=sys.stderr)
        return None
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Malformed JSON or missing fields
        return None
    except TimeoutError:
        # Request timeout
        return None
    except Exception:
        # Catch-all for any other unexpected errors
        return None


def _parse_release_response(data: dict[str, Any]) -> ReleaseInfo:
    """Parse GitHub API response into ReleaseInfo.

    Args:
        data: Raw JSON response from GitHub API.

    Returns:
        Parsed ReleaseInfo object.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If datetime parsing fails.
    """
    assets = [
        ReleaseAsset(
            name=asset["name"],
            browser_download_url=asset["browser_download_url"],
            size=asset.get("size", 0),
            content_type=asset.get("content_type", "application/octet-stream"),
        )
        for asset in data.get("assets", [])
    ]

    # Parse ISO 8601 datetime
    published_str = data.get("published_at", "")
    if published_str:
        published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
    else:
        published_at = datetime.now(timezone.utc)

    return ReleaseInfo(
        tag_name=data["tag_name"],
        name=data.get("name", data["tag_name"]),
        body=data.get("body", ""),
        html_url=data["html_url"],
        assets=assets,
        published_at=published_at,
    )


def parse_version(tag_name: str) -> str:
    """Strip v prefix from tag name to get version string.

    Args:
        tag_name: Git tag (e.g., "v0.1.0").

    Returns:
        Version string without v prefix (e.g., "0.1.0").
    """
    return tag_name.lstrip("v")


# =============================================================================
# Version Comparison (T081, T126)
# =============================================================================


def is_newer_available(current: str, latest: str) -> bool:
    """Check if the latest version is newer than current.

    Uses packaging.version.Version for proper semantic version comparison.
    Handles dev versions (0.0.0-dev) specially - any release is newer.

    Args:
        current: Current installed version (e.g., "0.1.0").
        latest: Latest available version (e.g., "0.2.0").

    Returns:
        True if latest > current, False otherwise.
    """
    # Handle dev version - any release is newer
    if current == "0.0.0-dev" or current.endswith("-dev"):
        return True

    try:
        from packaging.version import Version

        return Version(latest) > Version(current)
    except (ImportError, ValueError):
        # Fallback to string comparison if packaging not available
        # or version string is malformed
        return latest > current


# =============================================================================
# Update Check Rate Limiting (T082, T090)
# =============================================================================


def should_check_update(config: ConfigSchema) -> bool:
    """Determine if enough time has passed for a new update check.

    Checks:
    1. Is updates.check enabled in config?
    2. Has 24 hours passed since last_check?

    Args:
        config: Loaded configuration schema.

    Returns:
        True if an update check should be performed.
    """
    # Check if updates are enabled
    if not config.updates.check:
        return False

    # Check rate limit
    last_check_str = config.updates.last_check
    if not last_check_str:
        return True

    try:
        # Normalize Z suffix for fromisoformat
        normalized = last_check_str.replace("Z", "+00:00")
        last_check = datetime.fromisoformat(normalized)
        return datetime.now(timezone.utc) - last_check >= CHECK_INTERVAL
    except ValueError:
        # Invalid timestamp, allow check
        return True


def _update_last_check_time() -> None:
    """Update the last_check timestamp in config after successful API call."""
    from pgtail_py.config import save_config

    now = datetime.now(timezone.utc).isoformat()
    save_config("updates.last_check", now)


# =============================================================================
# Notification Formatting (T084-T086)
# =============================================================================


def notify_update(update_info: UpdateInfo) -> None:
    """Print one-line update notification to stderr.

    Format: pgtail X.Y.Z available. Upgrade with: <command>

    Respects NO_COLOR environment variable.

    Args:
        update_info: Information about the available update.
    """
    version = update_info.latest_version
    command = update_info.upgrade_command
    no_color = os.environ.get("NO_COLOR", "")

    if no_color:
        # Plain output without colors
        msg = f"pgtail {version} available. Upgrade with: {command}"
    else:
        # Colored output: version bold, "available" green, command cyan
        # Using ANSI escape codes directly for stderr
        bold = "\033[1m"
        green = "\033[32m"
        cyan = "\033[36m"
        reset = "\033[0m"
        msg = f"pgtail {bold}{version}{reset} {green}available{reset}. Upgrade with: {cyan}{command}{reset}"

    print(msg, file=sys.stderr)


# =============================================================================
# Async and Sync Update Check Functions (T083, T087)
# =============================================================================


def check_update_async(config: ConfigSchema) -> None:
    """Run update check in background thread (non-blocking startup check).

    Only checks if rate limit allows (24 hours since last check).
    Silently handles all errors without affecting main application.

    Args:
        config: Loaded configuration schema.
    """
    if not should_check_update(config):
        return

    def _background_check() -> None:
        try:
            release = fetch_latest_release()
            if release is None:
                return

            current = get_version()
            latest = parse_version(release.tag_name)

            if is_newer_available(current, latest):
                method = detect_install_method()
                update_info = UpdateInfo(
                    current_version=current,
                    latest_version=latest,
                    install_method=method,
                    upgrade_command=get_upgrade_command(method),
                    release_url=release.html_url,
                    checked_at=datetime.now(timezone.utc),
                )
                notify_update(update_info)

            # Update last check time on successful API call
            _update_last_check_time()
        except Exception:
            # Silent failure - don't affect main application
            pass

    # Run in daemon thread so it doesn't block shutdown
    thread = threading.Thread(target=_background_check, daemon=True)
    thread.start()


def check_update_sync() -> tuple[bool, str]:
    """Synchronous update check for --check-update flag.

    Bypasses rate limit - always checks. Returns result for CLI display.

    Returns:
        Tuple of (update_available, message).
        - If update available: (True, "Update message with command")
        - If up to date: (False, "Up to date message")
        - If error: (False, "Error message")
    """
    release = fetch_latest_release()

    if release is None:
        return (False, "Unable to check for updates. Check your network connection.")

    current = get_version()
    latest = parse_version(release.tag_name)

    if is_newer_available(current, latest):
        method = detect_install_method()
        command = get_upgrade_command(method)
        no_color = os.environ.get("NO_COLOR", "")

        if no_color:
            msg = f"pgtail {latest} is available (current: {current}). Upgrade with: {command}"
        else:
            bold = "\033[1m"
            green = "\033[32m"
            cyan = "\033[36m"
            reset = "\033[0m"
            msg = f"pgtail {bold}{latest}{reset} is {green}available{reset} (current: {current}). Upgrade with: {cyan}{command}{reset}"

        return (True, msg)
    else:
        return (False, f"pgtail {current} is up to date.")


# =============================================================================
# Platform-specific binary asset lookup
# =============================================================================


def get_asset_for_platform(assets: list[ReleaseAsset]) -> ReleaseAsset | None:
    """Get the binary asset for the current platform.

    Args:
        assets: List of release assets.

    Returns:
        Matching asset for current platform, or None if not found.
    """
    os_name = "windows" if platform.system() == "Windows" else platform.system().lower()
    arch = "arm64" if platform.machine() in ("arm64", "aarch64") else "x86_64"

    expected_name = f"pgtail-{os_name}-{arch}"
    if os_name == "windows":
        expected_name += ".exe"

    for asset in assets:
        if asset.name == expected_name:
            return asset

    return None
