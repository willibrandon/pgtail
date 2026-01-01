"""Version reading, update checking, and installation method detection for pgtail.

This module provides:
- get_version(): Read installed version from package metadata
- InstallMethod: Enum for installation methods (pip, pipx, uv, homebrew, winget, binary)
- detect_install_method(): Detect how pgtail was installed
- get_upgrade_command(): Get the appropriate upgrade command for the installation method
- UpdateInfo, ReleaseAsset, ReleaseInfo: Dataclasses for update checking
"""

from __future__ import annotations

import importlib.metadata
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
