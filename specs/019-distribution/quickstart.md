# Quickstart: pgtail Distribution

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This guide covers the implementation steps for pgtail distribution features: GitHub installation, binary releases, update checking, Homebrew tap, and winget integration.

---

## Prerequisites

### Development Environment

- Python 3.10+
- uv (recommended) or pip
- Git
- GitHub account with:
  - Access to create `willibrandon/homebrew-tap` repository
  - Personal Access Token with `repo` scope

### Secrets Configuration

Configure these secrets in the pgtail repository:

| Secret | Value | Purpose |
|--------|-------|---------|
| `HOMEBREW_TAP_TOKEN` | PAT with `repo` scope | Push to homebrew-tap |
| `WINGET_PKGS_TOKEN` | PAT with `public_repo` scope | Submit to winget-pkgs |

---

## Implementation Order

### Phase 1: Verify pip/pipx/uv Installation

**Goal**: Confirm existing pyproject.toml works for GitHub-based installation.

```bash
# Test pip install from GitHub
pip install git+https://github.com/willibrandon/pgtail.git
pgtail --version

# Test with specific version tag
pip install git+https://github.com/willibrandon/pgtail.git@v0.1.0

# Test pipx
pipx install git+https://github.com/willibrandon/pgtail.git

# Test uv
uv pip install git+https://github.com/willibrandon/pgtail.git
```

**Verification**:
- [ ] `pgtail` command available in PATH
- [ ] `pgtail --version` shows correct version
- [ ] All dependencies installed correctly

---

### Phase 2: Add Version and Update Checking

**Files to create/modify**:
- `pgtail_py/version.py` (new)
- `pgtail_py/cli_main.py` (modify)
- `pgtail_py/config.py` (modify)

#### Step 2.1: Create version.py

```python
# pgtail_py/version.py
"""Version management and update checking."""

import json
import sys
import threading
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from typing import Callable

RELEASES_URL = "https://api.github.com/repos/willibrandon/pgtail/releases/latest"
CHECK_INTERVAL = timedelta(hours=24)
TIMEOUT = 5


class InstallMethod(Enum):
    """Installation method for pgtail."""
    PIP = "pip"
    PIPX = "pipx"
    UV = "uv"
    HOMEBREW = "homebrew"
    WINGET = "winget"
    BINARY = "binary"


@dataclass
class UpdateInfo:
    """Information about an available update."""
    current_version: str
    latest_version: str
    install_method: InstallMethod
    upgrade_command: str


def get_version() -> str:
    """Get the installed pgtail version."""
    try:
        return version("pgtail")
    except PackageNotFoundError:
        return "0.0.0-dev"


def detect_install_method() -> InstallMethod:
    """Detect how pgtail was installed."""
    # Implementation from research.md
    ...


def get_upgrade_command(method: InstallMethod) -> str:
    """Get the upgrade command for the installation method."""
    commands = {
        InstallMethod.PIP: "pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
        InstallMethod.PIPX: "pipx upgrade pgtail",
        InstallMethod.UV: "uv pip install --upgrade git+https://github.com/willibrandon/pgtail.git",
        InstallMethod.HOMEBREW: "brew upgrade pgtail",
        InstallMethod.WINGET: "winget upgrade willibrandon.pgtail",
        InstallMethod.BINARY: "https://github.com/willibrandon/pgtail/releases/latest",
    }
    return commands.get(method, commands[InstallMethod.BINARY])


def check_latest_version() -> str | None:
    """Fetch latest version from GitHub Releases API."""
    # Implementation from contracts/github-releases-api.md
    ...


def check_update_async(config, notify_callback: Callable[[UpdateInfo], None]) -> None:
    """Check for updates in background thread."""
    # Implementation details in data-model.md
    ...
```

#### Step 2.2: Add CLI Flags

Modify `cli_main.py` to add `--version` and `--check-update`:

```python
# In cli_main.py
import typer
from pgtail_py.version import get_version, check_update_sync

app = typer.Typer()

@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
    check_update: bool = typer.Option(False, "--check-update", help="Check for updates"),
):
    if version:
        print(f"pgtail {get_version()}")
        raise typer.Exit()

    if check_update:
        check_update_sync()
        raise typer.Exit()
```

#### Step 2.3: Add Config Setting

In `config.py`, add the updates section schema:

```python
# Add to config schema
CONFIG_SCHEMA = {
    ...
    "updates": {
        "check": {"type": bool, "default": True},
        "last_check": {"type": str, "default": ""},
        "last_version": {"type": str, "default": ""},
    },
}
```

---

### Phase 3: Create Release Workflow

**File to create**: `.github/workflows/release.yml`

Copy the workflow from `contracts/release-workflow.md`.

**Test locally** (optional):
```bash
# Build binary locally
uv run pyinstaller --onefile --name pgtail pgtail_py/__main__.py
./dist/pgtail --version
```

---

### Phase 4: Create Homebrew Tap

**Repository**: `willibrandon/homebrew-tap`

1. Create repository on GitHub
2. Add `README.md` and `Formula/pgtail.rb` (initial placeholder)
3. First release will auto-update the formula

```bash
# Create and push
mkdir homebrew-tap && cd homebrew-tap
mkdir Formula
# Add pgtail.rb from contracts/homebrew-formula.md (with placeholder SHA256s)
git init
git add .
git commit -m "Initial tap setup"
git remote add origin git@github.com:willibrandon/homebrew-tap.git
git push -u origin main
```

---

### Phase 5: Prepare winget Manifest

**First submission is manual**:

1. Fork `microsoft/winget-pkgs`
2. Create directory: `manifests/w/willibrandon/pgtail/0.1.0/`
3. Add manifest files from `contracts/winget-manifest.md`
4. Submit PR

Subsequent updates will be automated by the release workflow.

---

### Phase 6: Update Documentation

**File to modify**: `README.md`

Add installation section:

```markdown
## Installation

### pip/pipx/uv (Python 3.10+)

```bash
# pip
pip install git+https://github.com/willibrandon/pgtail.git

# pipx (recommended for CLI tools)
pipx install git+https://github.com/willibrandon/pgtail.git

# uv
uv pip install git+https://github.com/willibrandon/pgtail.git
```

### Homebrew (macOS/Linux)

```bash
brew tap willibrandon/tap
brew install pgtail
```

### winget (Windows)

```powershell
winget install willibrandon.pgtail
```

### Binary Download

Download the pre-built binary for your platform from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest).

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | `pgtail-macos-arm64` |
| macOS (Intel) | `pgtail-macos-x86_64` |
| Linux (x86_64) | `pgtail-linux-x86_64` |
| Linux (ARM64) | `pgtail-linux-arm64` |
| Windows | `pgtail-windows-x86_64.exe` |

### Upgrading

| Install Method | Upgrade Command |
|----------------|-----------------|
| pip | `pip install --upgrade git+https://github.com/willibrandon/pgtail.git` |
| pipx | `pipx upgrade pgtail` |
| Homebrew | `brew upgrade pgtail` |
| winget | `winget upgrade willibrandon.pgtail` |
| Binary | Re-download from releases |
```

---

## Release Process

### Creating a Release

```bash
# 1. Update version in pyproject.toml
# 2. Commit changes
git add pyproject.toml
git commit -m "Bump version to 0.2.0"

# 3. Create and push tag
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

### What Happens Automatically

1. GitHub Actions builds binaries for all 5 platforms
2. Creates GitHub Release with binaries and checksums
3. Updates Homebrew formula in homebrew-tap
4. Submits PR to winget-pkgs

---

## Testing Checklist

### Pre-Release

- [ ] `pgtail --version` shows correct version
- [ ] `pgtail --check-update` works
- [ ] Startup update notification works (when newer version exists)
- [ ] All tests pass
- [ ] pyproject.toml version matches tag

### Post-Release

- [ ] Binaries attached to GitHub Release
- [ ] SHA256 checksums attached
- [ ] homebrew-tap formula updated
- [ ] winget-pkgs PR submitted

### Installation Methods

- [ ] `pip install git+...` works
- [ ] `pipx install git+...` works
- [ ] `uv pip install git+...` works
- [ ] `brew install willibrandon/tap/pgtail` works
- [ ] `winget install willibrandon.pgtail` works (after approval)
- [ ] Binary download runs on all platforms

---

## Troubleshooting

### Binary won't run on macOS

macOS Gatekeeper blocks unsigned binaries:
```bash
# Allow the binary
xattr -d com.apple.quarantine pgtail-macos-arm64
# Or: System Preferences → Security & Privacy → Allow
```

### Windows SmartScreen warning

Click "More info" → "Run anyway"

### Homebrew formula not updating

Check if homebrew-tap push succeeded:
```bash
cd homebrew-tap
git log -1
```

Manually update if needed:
```bash
brew update
brew upgrade pgtail
```

### winget PR not merging

- Check PR status on microsoft/winget-pkgs
- Respond to review comments within 7 days
- Ensure SHA256 matches binary
