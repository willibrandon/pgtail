# Research: pgtail Distribution

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This document consolidates research for cross-platform pgtail distribution without PyPI dependency. Topics covered: PyInstaller cross-platform builds, GitHub Actions release workflow, GitHub Releases API for update checking, installation method detection, Homebrew tap creation, and winget manifest submission.

---

## 1. PyInstaller Cross-Platform Binary Building

### Decision
Use GitHub Actions matrix strategy with native runners for each platform. PyInstaller cannot cross-compile.

### Rationale
PyInstaller bundles a full native Python interpreter, so a binary built on macOS won't run on Windows. Each platform requires its own build runner.

### Alternatives Considered
- **Cross-compilation**: Not possible with PyInstaller
- **Docker for Linux builds**: Adds complexity; GitHub runners are simpler
- **Third-party services (Nuitka, cx_Freeze)**: Less mature, PyInstaller is industry standard

### Technical Details

**Platform Matrix**:
| Platform | GitHub Runner | Binary Name |
|----------|--------------|-------------|
| macOS arm64 | `macos-14` (M1) | `pgtail-macos-arm64` |
| macOS x86_64 | `macos-13` | `pgtail-macos-x86_64` |
| Linux x86_64 | `ubuntu-latest` | `pgtail-linux-x86_64` |
| Linux arm64 | `ubuntu-24.04-arm` | `pgtail-linux-arm64` |
| Windows x86_64 | `windows-latest` | `pgtail-windows-x86_64.exe` |

**PyInstaller Command**:
```bash
pyinstaller --onefile --name pgtail pgtail_py/__main__.py
```

**Key Considerations**:
- Use `fail-fast: false` in matrix to prevent one failure stopping all builds
- PyInstaller 6.0+ supports Python 3.8-3.14
- Linux arm64 runners available via `ubuntu-24.04-arm`
- macOS arm64 runners: `macos-14` (M1 chip), `macos-latest` is currently arm64

### Sources
- [espressif/python-binary-action](https://github.com/espressif/python-binary-action)
- [ai-mindset/py-cross-compile](https://github.com/ai-mindset/py-cross-compile)
- [Build a multi OS Python app with PyInstaller and GitHub Actions](https://data-dive.com/multi-os-deployment-in-cloud-using-pyinstaller-and-github-actions/)
- [PyInstaller PyPI](https://pypi.org/project/pyinstaller/)

---

## 2. GitHub Actions Release Workflow

### Decision
Use `softprops/action-gh-release` triggered by version tag push (`v*`). Auto-generate release notes from commits.

### Rationale
Most popular action with active maintenance. Supports file glob patterns for asset upload and automatic release note generation.

### Alternatives Considered
- **actions/create-release** (official): Archived, not maintained
- **github-action-publish-binaries**: Less feature-rich
- **Manual release creation**: Defeats automation purpose

### Technical Details

**Workflow Trigger**:
```yaml
on:
  push:
    tags:
      - 'v*'
```

**Release Action Usage**:
```yaml
- uses: softprops/action-gh-release@v2
  with:
    files: |
      dist/pgtail-*
    generate_release_notes: true
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Key Features**:
- If tag already has a release, updates existing release with new assets
- Supports glob patterns for files
- `generate_release_notes: true` creates notes from commits since last tag
- Requires `GITHUB_TOKEN` with write permissions (Settings → Actions → General)

**Workflow Structure**:
1. Build job: Matrix builds binaries for all platforms
2. Upload artifacts: Each platform uploads its binary
3. Release job: `needs: build`, downloads all artifacts, creates release

### Sources
- [softprops/action-gh-release](https://github.com/softprops/action-gh-release)
- [GitHub: Managing releases in a repository](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)

---

## 3. GitHub Releases API for Update Checking

### Decision
Use unauthenticated requests to `/repos/{owner}/{repo}/releases/latest` with ETag caching for rate limit efficiency.

### Rationale
Public repo releases are accessible without authentication. ETag validation doesn't count against rate limit. Simple implementation with stdlib `urllib.request`.

### Alternatives Considered
- **PyGithub library**: Heavy dependency for simple use case
- **lastversion tool**: External dependency, overkill
- **Authenticated requests**: Unnecessary for public repo, adds complexity

### Technical Details

**API Endpoint**:
```
GET https://api.github.com/repos/willibrandon/pgtail/releases/latest
```

**Response Fields**:
```json
{
  "tag_name": "v0.2.0",
  "body": "Release notes...",
  "assets": [
    {
      "name": "pgtail-macos-arm64",
      "browser_download_url": "https://github.com/...",
      "size": 12345678
    }
  ]
}
```

**Rate Limits**:
- Unauthenticated: 60 requests/hour
- Authenticated: 5,000 requests/hour
- ETag conditional requests: Don't count against limit

**Implementation Strategy**:
```python
import urllib.request
import json

def check_latest_version() -> str | None:
    url = "https://api.github.com/repos/willibrandon/pgtail/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get("tag_name", "").lstrip("v")
    except Exception:
        return None
```

**Rate Limiting Strategy**:
- Cache last check timestamp in config file
- Skip startup check if < 24 hours since last check
- `--check-update` bypasses rate limit (explicit user request)

### Sources
- [GitHub REST API: Releases](https://docs.github.com/en/rest/releases/releases)
- [GitHub REST API: Rate limits](https://docs.github.com/en/rest/rate-limit)
- [dvershinin/lastversion](https://github.com/dvershinin/lastversion) - ETag caching strategy

---

## 4. Installation Method Detection

### Decision
Use heuristic-based detection checking paths, environment variables, and executable locations.

### Rationale
No single reliable method exists. Combination of heuristics covers most cases with fallback to "binary" (GitHub Releases URL).

### Alternatives Considered
- **Package metadata only**: Not available for binary installs
- **Environment variable injection**: Requires changes to all installers
- **User configuration**: Violates "zero configuration" principle

### Technical Details

**Detection Heuristics**:

| Install Method | Detection Logic |
|----------------|-----------------|
| pip (user) | `sys.prefix` contains `site-packages`, not in venv |
| pip (venv) | `sys.prefix != sys.base_prefix` |
| pipx | `sys.executable` contains `.local/pipx/venvs/pgtail` |
| uv | `sys.executable` contains `.venv` or UV marker |
| Homebrew (macOS) | `sys.executable.startswith("/opt/homebrew")` or `/usr/local/Cellar` |
| Homebrew (Linux) | `sys.executable.startswith("/home/linuxbrew")` |
| winget | Windows registry check or `LOCALAPPDATA/Microsoft/winget` |
| Binary | Fallback - none of above match |

**Implementation**:
```python
import sys
import os
from enum import Enum

class InstallMethod(Enum):
    PIP = "pip"
    PIPX = "pipx"
    UV = "uv"
    HOMEBREW = "homebrew"
    WINGET = "winget"
    BINARY = "binary"

def detect_install_method() -> InstallMethod:
    exe = sys.executable.lower()

    # Homebrew detection
    if "/opt/homebrew" in exe or "/usr/local/Cellar" in exe:
        return InstallMethod.HOMEBREW
    if "/home/linuxbrew" in exe:
        return InstallMethod.HOMEBREW

    # pipx detection
    if "pipx" in exe and "venvs" in exe:
        return InstallMethod.PIPX

    # winget detection (Windows)
    if sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata and "microsoft\\winget" in exe.lower():
            return InstallMethod.WINGET

    # pip/uv detection (in venv or site-packages)
    if sys.prefix != sys.base_prefix:
        # Running in a venv - could be uv or pip
        if ".venv" in exe or "uv" in exe:
            return InstallMethod.UV
        return InstallMethod.PIP

    # Fallback to binary
    return InstallMethod.BINARY
```

**Upgrade Commands by Method**:
```python
UPGRADE_COMMANDS = {
    InstallMethod.PIP: "pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
    InstallMethod.PIPX: "pipx upgrade pgtail",
    InstallMethod.UV: "uv pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
    InstallMethod.HOMEBREW: "brew upgrade pgtail",
    InstallMethod.WINGET: "winget upgrade willibrandon.pgtail",
    InstallMethod.BINARY: "https://github.com/willibrandon/pgtail/releases/latest",
}
```

### Sources
- [Homebrew and Python](https://docs.brew.sh/Homebrew-and-Python)
- [pipx GitHub](https://github.com/pypa/pipx)
- [pipx issue #1074](https://github.com/pypa/pipx/issues/1074) - venv detection discussion

---

## 5. Homebrew Tap and Formula

### Decision
Create `willibrandon/homebrew-tap` repository with formula that downloads pre-built binaries based on platform/architecture.

### Rationale
Tap repository allows custom formulas outside homebrew-core. Binary downloads avoid build-time dependencies. Platform-specific blocks handle macOS/Linux and arm64/x86_64.

### Alternatives Considered
- **Submit to homebrew-core**: Requires high popularity threshold, longer review
- **Cask (for macOS only)**: Casks are for GUI apps, not CLIs
- **Build from source in formula**: Adds Python dependency, longer install time

### Technical Details

**Repository Structure**:
```
homebrew-tap/
├── README.md
└── Formula/
    └── pgtail.rb
```

**Formula Template** (`Formula/pgtail.rb`):
```ruby
class Pgtail < Formula
  desc "PostgreSQL log tailer with auto-detection and color output"
  homepage "https://github.com/willibrandon/pgtail"
  license "MIT"
  version "0.1.0"

  on_macos do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-macos-arm64"
      sha256 "PLACEHOLDER_SHA256_MACOS_ARM64"
    end
    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-macos-x86_64"
      sha256 "PLACEHOLDER_SHA256_MACOS_X86_64"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-linux-arm64"
      sha256 "PLACEHOLDER_SHA256_LINUX_ARM64"
    end
    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-linux-x86_64"
      sha256 "PLACEHOLDER_SHA256_LINUX_X86_64"
    end
  end

  def install
    binary_name = "pgtail-#{OS.mac? ? "macos" : "linux"}-#{Hardware::CPU.arm? ? "arm64" : "x86_64"}"
    bin.install binary_name => "pgtail"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pgtail --version")
  end
end
```

**Installation Command**:
```bash
brew tap willibrandon/tap
brew install pgtail
```

**Automated Formula Updates**:
Release workflow updates formula via:
1. Calculate SHA256 of each binary
2. Clone homebrew-tap repo
3. Update version and SHA256 values in pgtail.rb
4. Commit and push (or open PR)

### Sources
- [How to Create and Maintain a Tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
- [Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Adding Software to Homebrew](https://docs.brew.sh/Adding-Software-to-Homebrew)

---

## 6. winget Manifest and Submission

### Decision
Create multi-file manifest and submit PR to `microsoft/winget-pkgs`. Use `wingetcreate` tool for initial creation and updates.

### Rationale
Multi-file format (version, locale, installer) is recommended for best user experience. Automated PR submission keeps package current.

### Alternatives Considered
- **Single-file manifest**: Less maintainable, deprecated
- **Manual PR creation**: Error-prone, slow
- **Chocolatey instead**: Less official, requires separate package repo

### Technical Details

**Manifest Directory Structure**:
```
manifests/w/willibrandon/pgtail/0.1.0/
├── willibrandon.pgtail.yaml              (version)
├── willibrandon.pgtail.locale.en-US.yaml (locale)
└── willibrandon.pgtail.installer.yaml    (installer)
```

**willibrandon.pgtail.yaml** (version):
```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.6.0
```

**willibrandon.pgtail.locale.en-US.yaml**:
```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
PackageLocale: en-US
Publisher: willibrandon
PublisherUrl: https://github.com/willibrandon
PackageName: pgtail
PackageUrl: https://github.com/willibrandon/pgtail
License: MIT
LicenseUrl: https://github.com/willibrandon/pgtail/blob/main/LICENSE
ShortDescription: PostgreSQL log tailer with auto-detection and color output
Tags:
  - postgresql
  - log
  - cli
  - database
  - developer-tools
ManifestType: defaultLocale
ManifestVersion: 1.6.0
```

**willibrandon.pgtail.installer.yaml**:
```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
Platform:
  - Windows.Desktop
MinimumOSVersion: 10.0.18362.0
InstallerType: portable
Installers:
  - Architecture: x64
    InstallerUrl: https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-windows-x86_64.exe
    InstallerSha256: PLACEHOLDER_SHA256_WINDOWS
    Commands:
      - pgtail
ManifestType: installer
ManifestVersion: 1.6.0
```

**Key Requirements**:
- Silent install mandatory (portable EXE works)
- Unique PackageIdentifier
- One PR per version
- 7-day response window for review feedback

**Automated Submission**:
```bash
# Install wingetcreate
winget install wingetcreate

# Create/update manifest
wingetcreate update willibrandon.pgtail --version 0.1.0 \
  --urls https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-windows-x86_64.exe \
  --submit
```

### Sources
- [Create your package manifest](https://learn.microsoft.com/en-us/windows/package-manager/package/manifest)
- [Submit your manifest to the repository](https://learn.microsoft.com/en-us/windows/package-manager/package/repository)
- [microsoft/winget-create](https://github.com/microsoft/winget-create)
- [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

---

## 7. Version Management

### Decision
Single source of truth in `pyproject.toml`. Read at runtime using `importlib.metadata`.

### Rationale
Standard Python packaging practice. Works with pip, pipx, uv, and binary builds (PyInstaller embeds metadata).

### Alternatives Considered
- **Separate VERSION file**: Extra file to maintain
- **Git tags only**: Not accessible at runtime without git
- **Hardcoded in code**: Easy to forget updating

### Technical Details

**pyproject.toml** (already configured):
```toml
[project]
name = "pgtail"
version = "0.1.0"
```

**Runtime Version Access**:
```python
from importlib.metadata import version, PackageNotFoundError

def get_version() -> str:
    try:
        return version("pgtail")
    except PackageNotFoundError:
        return "0.0.0-dev"
```

**Version Comparison**:
```python
from packaging.version import Version

def is_newer_available(current: str, latest: str) -> bool:
    try:
        return Version(latest) > Version(current)
    except Exception:
        return False
```

Note: `packaging` is already a transitive dependency via pip/setuptools.

---

## 8. Update Notification UX

### Decision
Non-blocking startup check with one-line stderr notification. Respect NO_COLOR and quiet hours config.

### Rationale
Update checks shouldn't delay normal operation. Stderr keeps stdout clean for piping. Existing notification infrastructure (from notify feature) can be reused.

### Technical Details

**Notification Format**:
```
pgtail v0.2.0 available (current: v0.1.0). Upgrade: brew upgrade pgtail
```

**Implementation Pattern**:
```python
import threading

def check_update_async():
    """Run update check in background thread."""
    def _check():
        if not should_check_update():  # Rate limit check
            return
        latest = check_latest_version()
        if latest and is_newer_available(get_version(), latest):
            upgrade_cmd = get_upgrade_command()
            notify_update(get_version(), latest, upgrade_cmd)

    thread = threading.Thread(target=_check, daemon=True)
    thread.start()
```

**Rate Limit Storage** (in existing config):
```toml
[updates]
check = true
last_check = "2026-01-01T00:00:00Z"
```

**--check-update Flag**:
```
$ pgtail --check-update
pgtail v0.1.0 (up to date)

$ pgtail --check-update  # when update available
pgtail v0.1.0 → v0.2.0 available
Upgrade: brew upgrade pgtail
```

---

## Summary of Decisions

| Topic | Decision |
|-------|----------|
| Binary Building | PyInstaller with GitHub Actions matrix (5 platforms) |
| Release Workflow | softprops/action-gh-release on tag push |
| Update Checking | GitHub Releases API, unauthenticated, ETag caching |
| Install Detection | Heuristic-based (paths, env vars, fallback to binary) |
| Homebrew | Custom tap with platform-specific binary downloads |
| winget | Multi-file manifest, wingetcreate for automation |
| Version Source | pyproject.toml with importlib.metadata |
| Notification UX | Non-blocking stderr with install-specific upgrade command |
