# Data Model: pgtail Distribution

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This document defines the data entities, configuration schema, and state management for pgtail distribution features. Covers installation method detection, update checking, and version management.

---

## Entities

### InstallMethod (Enum)

Represents the method used to install pgtail on the current system.

```python
from enum import Enum

class InstallMethod(Enum):
    """Installation method for pgtail."""
    PIP = "pip"
    PIPX = "pipx"
    UV = "uv"
    HOMEBREW = "homebrew"
    WINGET = "winget"
    BINARY = "binary"
```

**Properties**:
| Value | Description | Upgrade Command Pattern |
|-------|-------------|------------------------|
| `PIP` | Installed via pip from GitHub | `pip install --upgrade git+https://...` |
| `PIPX` | Installed via pipx | `pipx upgrade pgtail` |
| `UV` | Installed via uv | `uv pip install --upgrade git+https://...` |
| `HOMEBREW` | Installed via Homebrew tap | `brew upgrade pgtail` |
| `WINGET` | Installed via Windows Package Manager | `winget upgrade willibrandon.pgtail` |
| `BINARY` | Standalone binary download | GitHub Releases URL |

---

### UpdateInfo

Information about an available update.

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    install_method: InstallMethod
    upgrade_command: str
    release_url: str
    checked_at: datetime
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `current_version` | `str` | Currently installed version (e.g., "0.1.0") |
| `latest_version` | `str` | Latest available version (e.g., "0.2.0") |
| `install_method` | `InstallMethod` | Detected installation method |
| `upgrade_command` | `str` | Platform-specific upgrade command |
| `release_url` | `str` | URL to release page |
| `checked_at` | `datetime` | When the check was performed |

---

### ReleaseAsset

Represents a binary asset attached to a GitHub Release.

```python
@dataclass
class ReleaseAsset:
    """Binary asset from GitHub Release."""
    name: str
    browser_download_url: str
    size: int
    content_type: str
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Asset filename (e.g., "pgtail-macos-arm64") |
| `browser_download_url` | `str` | Direct download URL |
| `size` | `int` | File size in bytes |
| `content_type` | `str` | MIME type |

---

### ReleaseInfo

Represents a GitHub Release.

```python
@dataclass
class ReleaseInfo:
    """GitHub Release information."""
    tag_name: str
    name: str
    body: str
    html_url: str
    assets: list[ReleaseAsset]
    published_at: datetime
```

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `tag_name` | `str` | Git tag (e.g., "v0.1.0") |
| `name` | `str` | Release title |
| `body` | `str` | Release notes (markdown) |
| `html_url` | `str` | URL to release page |
| `assets` | `list[ReleaseAsset]` | Attached binary files |
| `published_at` | `datetime` | Publication timestamp |

---

## Configuration Schema

### Update Configuration

Extension to existing config.toml schema for update checking settings.

```toml
[updates]
check = true                           # Enable startup update check
last_check = "2026-01-01T00:00:00Z"    # ISO 8601 timestamp
last_version = "0.1.0"                 # Version at last check (for caching)
```

**Fields**:
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `updates.check` | `bool` | `true` | Enable/disable startup update check |
| `updates.last_check` | `str` (ISO 8601) | `""` | Timestamp of last check |
| `updates.last_version` | `str` | `""` | Latest version seen at last check |

**Validation Rules**:
- `check`: Must be boolean
- `last_check`: Valid ISO 8601 datetime or empty string
- `last_version`: Valid semver string or empty string

---

## State Transitions

### Update Check Flow

```
┌─────────────────┐
│  App Startup    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│ updates.check?  │────────────▶│  Skip Check     │
└────────┬────────┘             └─────────────────┘
         │ Yes
         ▼
┌─────────────────┐     Yes     ┌─────────────────┐
│ <24h since last │────────────▶│  Skip Check     │
│   check?        │             └─────────────────┘
└────────┬────────┘
         │ No
         ▼
┌─────────────────┐
│ Background      │
│ Thread: Fetch   │
│ /releases/latest│
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│ API Success?    │────────────▶│ Silent Fail     │
└────────┬────────┘             │ (Continue)      │
         │ Yes                  └─────────────────┘
         ▼
┌─────────────────┐
│ Update          │
│ last_check time │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│ Newer version?  │────────────▶│ No notification │
└────────┬────────┘             └─────────────────┘
         │ Yes
         ▼
┌─────────────────┐
│ Detect install  │
│ method          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Print upgrade   │
│ notification    │
│ to stderr       │
└─────────────────┘
```

### Explicit Check Flow (--check-update)

```
┌─────────────────┐
│ pgtail          │
│ --check-update  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Fetch           │
│ /releases/latest│
│ (no rate limit) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│ API Success?    │────────────▶│ Print error     │
└────────┬────────┘             │ Exit 1          │
         │ Yes                  └─────────────────┘
         ▼
┌─────────────────┐
│ Detect install  │
│ method          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     No      ┌─────────────────┐
│ Newer version?  │────────────▶│ Print "up to    │
└────────┬────────┘             │ date" message   │
         │ Yes                  │ Exit 0          │
         ▼                      └─────────────────┘
┌─────────────────┐
│ Print update    │
│ available       │
│ with upgrade cmd│
│ Exit 0          │
└─────────────────┘
```

---

## File Artifacts

### Binary Naming Convention

| Platform | Architecture | Filename |
|----------|--------------|----------|
| macOS | arm64 | `pgtail-macos-arm64` |
| macOS | x86_64 | `pgtail-macos-x86_64` |
| Linux | x86_64 | `pgtail-linux-x86_64` |
| Linux | arm64 | `pgtail-linux-arm64` |
| Windows | x86_64 | `pgtail-windows-x86_64.exe` |

**Pattern**: `pgtail-{os}-{arch}[.exe]`

### Release Asset Checksums

For Homebrew and winget formulas, SHA256 checksums are required:

```
pgtail-macos-arm64.sha256
pgtail-macos-x86_64.sha256
pgtail-linux-x86_64.sha256
pgtail-linux-arm64.sha256
pgtail-windows-x86_64.exe.sha256
```

---

## Relationships

```
┌─────────────────┐
│   Config File   │
│  (config.toml)  │
└────────┬────────┘
         │ contains
         ▼
┌─────────────────┐
│ [updates]       │
│ section         │
└────────┬────────┘
         │ used by
         ▼
┌─────────────────┐         ┌─────────────────┐
│ UpdateChecker   │────────▶│ GitHub API      │
│ (new module)    │  calls  │ /releases/latest│
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ produces                  │ returns
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ UpdateInfo      │◀────────│ ReleaseInfo     │
└────────┬────────┘  parsed └─────────────────┘
         │
         │ includes
         ▼
┌─────────────────┐
│ InstallMethod   │
│ (detected)      │
└─────────────────┘
```

---

## Validation Rules

### Version String
- Must match pattern: `^v?\d+\.\d+\.\d+(-[\w.]+)?$`
- Examples: `0.1.0`, `v0.1.0`, `1.0.0-beta.1`
- Comparison uses `packaging.version.Version`

### Upgrade Command
- Must be non-empty string
- For `BINARY` method, must be valid URL
- For others, must be valid shell command

### Config File Updates
- `last_check` updated atomically with `last_version`
- File lock during write (existing config.py pattern)
- Missing keys use defaults
