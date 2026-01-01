# Research: Nuitka Migration for Binary Distribution

**Feature Branch**: `020-nuitka-migration`
**Date**: 2026-01-01
**Status**: Complete

## Executive Summary

This research consolidates findings for migrating pgtail from PyInstaller to Nuitka for binary distribution. Key decisions resolve around: compilation modes, critical flags, WiX MSI generation, winget manifest format, Homebrew formula updates, and GitHub Actions CI patterns.

---

## 1. Nuitka Build Configuration

### 1.1 Compilation Mode Decision

**Decision**: Use `--mode=standalone` (NOT `--mode=onefile`)

**Rationale**:
- `--mode=standalone` creates a folder with executable + dependencies = instant startup
- `--mode=onefile` extracts to temp directory at runtime = startup overhead (same problem as PyInstaller)
- Windows has additional onefile problems: repeated unpacking, firewall issues

**Alternatives Considered**:
- `--mode=onefile` with `--onefile-tempdir-spec="{CACHE_DIR}/pgtail"` caches extraction but still has first-run delay
- Rejected in favor of standalone for consistent sub-1-second startup

### 1.2 Required Nuitka Flags

```bash
nuitka \
    --mode=standalone \
    --output-dir=dist \
    --output-filename=pgtail \
    --include-package=pgtail_py \
    --include-package=psutil \
    --include-package-data=certifi \
    --include-module=pgtail_py.detector_unix \
    --include-module=pgtail_py.detector_windows \
    --include-module=pgtail_py.notifier_unix \
    --include-module=pgtail_py.notifier_windows \
    --python-flag=no_asserts \
    --assume-yes-for-downloads \
    pgtail_py/__main__.py
```

**Flag Breakdown**:

| Flag | Purpose |
|------|---------|
| `--mode=standalone` | Self-contained folder distribution |
| `--output-dir=dist` | Build output location |
| `--output-filename=pgtail` | Remove .bin suffix on Unix |
| `--include-package=pgtail_py` | Ensure all modules included |
| `--include-package=psutil` | Native extension with platform-specific DLLs |
| `--include-package-data=certifi` | CA bundle for SSL (cacert.pem) |
| `--include-module=*_unix/*_windows` | Conditional imports Nuitka can't detect |
| `--python-flag=no_asserts` | Safe optimization, removes assert statements |
| `--assume-yes-for-downloads` | Unattended CI builds |

### 1.3 Flags to AVOID

| Flag | Why Avoid |
|------|-----------|
| `--python-flag=no_docstrings` | **BREAKS Typer CLI** - Typer uses docstrings for `--help` output |
| `--python-flag=static_hashes` | Not a valid CPython flag (build failure) |
| `--mode=onefile` | Reintroduces extraction overhead |

### 1.4 Output Structure

Nuitka standalone output:
```
dist/pgtail.dist/
├── pgtail              (executable, or pgtail.exe on Windows)
├── library.zip         (Python modules)
├── textual/            (package data)
├── rich/               (package data)
├── certifi/            (CA certificates)
└── ... (platform-specific DLLs)
```

**Rename after build**: `pgtail.dist/` → `pgtail-{platform}-{arch}/`

---

## 2. Version Fallback Implementation

### 2.1 Decision

**Decision**: Add hardcoded `__version__` fallback in `pgtail_py/__init__.py`

**Rationale**:
- Compiled binaries lack `.dist-info` metadata from `importlib.metadata`
- Hardcoded version is simpler than bundling egg-info directory
- Version must be synchronized with `pyproject.toml` on each release

### 2.2 Implementation

**pgtail_py/__init__.py**:
```python
"""pgtail - PostgreSQL log tailer with auto-detection and color output."""

__version__ = "0.2.0"
```

**pgtail_py/version.py** (update `get_version()`):
```python
def get_version() -> str:
    """Get the installed version of pgtail."""
    try:
        return importlib.metadata.version("pgtail")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for compiled binaries without metadata
        from pgtail_py import __version__
        return __version__
```

---

## 3. WiX Toolset 5.x MSI Generation

### 3.1 Installation

```bash
# Install WiX as global .NET tool
dotnet tool install --global wix --version 5.0.0

# Verify
wix --version
```

### 3.2 UpgradeCode GUID

**Decision**: Generate stable UpgradeCode GUID once, keep forever.

```
UpgradeCode: F8E7D6C5-B4A3-9281-7654-321098FEDCBA
```

**Rules**:
- UpgradeCode MUST remain constant across all versions
- ProductCode uses `Id="*"` (auto-generated per build)
- Only first 3 version parts matter for upgrade detection (1.0.0.x = 1.0.0)

### 3.3 WiX Source File (pgtail.wxs)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"
     xmlns:util="http://wixtoolset.org/schemas/v4/wxs/util">

  <Package Name="pgtail"
           Version="$(var.Version).0"
           Manufacturer="willibrandon"
           UpgradeCode="F8E7D6C5-B4A3-9281-7654-321098FEDCBA"
           Scope="perMachine">

    <MajorUpgrade DowngradeErrorMessage="A newer version is already installed."
                  AllowSameVersionUpgrades="yes" />
    <MediaTemplate EmbedCab="yes" CompressionLevel="high" />

    <Feature Id="MainFeature" Title="pgtail" Level="1">
      <ComponentGroupRef Id="PgtailFiles" />
      <ComponentRef Id="PathEnvComponent" />
    </Feature>

    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="pgtail">
        <Component Id="PathEnvComponent" Guid="C3D4E5F6-A7B8-9012-CDEF-345678901234">
          <Environment Id="PATH" Name="PATH" Value="[INSTALLFOLDER]"
                       Permanent="no" Part="last" Action="set" System="yes" />
        </Component>
      </Directory>
    </StandardDirectory>
  </Package>
</Wix>
```

### 3.4 Build Commands

```bash
# Harvest files from Nuitka output
wix heat dir dist\pgtail-windows-x86_64 -cg PgtailFiles -dr INSTALLFOLDER \
    -gg -sfrag -srd -sreg -var var.SourceDir -out files.wxs

# Build MSI
wix build pgtail.wxs files.wxs -d SourceDir=dist\pgtail-windows-x86_64 \
    -d Version=0.2.0 -arch x64 -out dist\pgtail-windows-x86_64.msi
```

---

## 4. winget Manifest Format

### 4.1 Directory Structure

```
manifests/w/willibrandon/pgtail/0.2.0/
├── willibrandon.pgtail.yaml                    (version)
├── willibrandon.pgtail.installer.yaml          (installer)
└── willibrandon.pgtail.locale.en-US.yaml       (locale)
```

### 4.2 Version Manifest

```yaml
# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.1.9.0.schema.json
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.2.0
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.9.0
```

### 4.3 Installer Manifest

```yaml
# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.9.0.schema.json
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.2.0
Platform:
  - Windows.Desktop
MinimumOSVersion: 10.0.18362.0
InstallerType: msi
Scope: machine
InstallModes:
  - interactive
  - silent
  - silentWithProgress
UpgradeBehavior: install
Installers:
  - Architecture: x64
    InstallerUrl: https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-windows-x86_64.msi
    InstallerSha256: PLACEHOLDER_SHA256
    ProductCode: '{EXTRACTED_FROM_BUILT_MSI}'  # Auto-generated by WiX, extract with: wix msi info pgtail.msi
ManifestType: installer
ManifestVersion: 1.9.0
```

**Important**: ProductCode MUST be extracted from the built MSI for each release. It is auto-generated by WiX (`Id="*"`) and changes every build. Use `wix msi info <file.msi>` or `Get-AppLockerFileInformation -Path <file.msi> | Select -ExpandProperty Publisher` to extract it.

### 4.4 Locale Manifest

```yaml
# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.9.0.schema.json
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.2.0
PackageLocale: en-US
Publisher: willibrandon
PublisherUrl: https://github.com/willibrandon
PackageName: pgtail
PackageUrl: https://github.com/willibrandon/pgtail
License: MIT
LicenseUrl: https://github.com/willibrandon/pgtail/blob/main/LICENSE
ShortDescription: Interactive PostgreSQL log tailer with auto-detection and color output
Description: pgtail is a command-line tool for tailing PostgreSQL log files with automatic instance detection, log level filtering, and colored output.
Tags:
  - postgresql
  - postgres
  - database
  - logs
  - cli
  - terminal
ManifestType: defaultLocale
ManifestVersion: 1.9.0
```

### 4.5 Submission Process

**New Package (first time)**:
1. Fork microsoft/winget-pkgs to willibrandon/winget-pkgs
2. Clone fork locally
3. Create manifests in correct directory structure
4. Test locally: `winget install --manifest <path>`
5. Push to fork branch, open PR to microsoft/winget-pkgs
6. Submit PR with title: `New package: willibrandon.pgtail version 0.2.0`
7. Wait for validation pipeline + team review (days to weeks)

**Updates (subsequent releases)**:
```bash
# wingetcreate handles fork workflow automatically
wingetcreate update willibrandon.pgtail \
    --version 0.3.0 \
    --urls https://github.com/willibrandon/pgtail/releases/download/v0.3.0/pgtail-windows-x86_64.msi \
    --token $WINGET_PKGS_TOKEN \
    --submit
```

**CI Workflow Note**: The update-winget job MUST push to the fork (willibrandon/winget-pkgs), NOT directly to microsoft/winget-pkgs (no push access). The PR is opened from the fork to upstream.

---

## 5. Homebrew Formula Update

### 5.1 Decision

**Decision**: Update formula to handle tar.gz archives with folder extraction.

**Changes from current formula**:
- URL now downloads `.tar.gz` instead of raw binary
- Install extracts folder, installs to `libexec`, symlinks to `bin`

### 5.2 Updated Formula

```ruby
# typed: false
# frozen_string_literal: true

class Pgtail < Formula
  desc "Interactive PostgreSQL log tailer with auto-detection and color output"
  homepage "https://github.com/willibrandon/pgtail"
  license "MIT"
  version "0.2.0"

  on_macos do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-macos-arm64.tar.gz"
      sha256 "SHA_MACOS_ARM64_PLACEHOLDER"
    end
    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-macos-x86_64.tar.gz"
      sha256 "SHA_MACOS_X86_64_PLACEHOLDER"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-linux-arm64.tar.gz"
      sha256 "SHA_LINUX_ARM64_PLACEHOLDER"
    end
    on_intel do
      url "https://github.com/willibrandon/pgtail/releases/download/v#{version}/pgtail-linux-x86_64.tar.gz"
      sha256 "SHA_LINUX_X86_64_PLACEHOLDER"
    end
  end

  def install
    # Determine platform-specific folder name
    if OS.mac?
      folder = Hardware::CPU.arm? ? "pgtail-macos-arm64" : "pgtail-macos-x86_64"
    else
      folder = Hardware::CPU.arm? ? "pgtail-linux-arm64" : "pgtail-linux-x86_64"
    end

    # Install the distribution folder to libexec
    libexec.install Dir["#{folder}/*"]

    # Symlink the executable to bin
    bin.install_symlink libexec/"pgtail"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/pgtail --version")
  end
end
```

### 5.3 Archive Structure

Archives must follow this structure for the formula to work:
```
pgtail-macos-arm64.tar.gz
└── pgtail-macos-arm64/
    ├── pgtail              (executable)
    └── ... (dependencies)
```

---

## 6. GitHub Actions CI Pattern

### 6.1 Why NOT Nuitka-Action

**Decision**: Use `uv run nuitka` instead of Nuitka-Action.

**Rationale**:
- Nuitka-Action runs in system Python, not the uv virtual environment
- Dependencies installed via `uv sync` are not available to Nuitka-Action
- uv's Python installation causes `libpython3.x.so` errors on Ubuntu

### 6.2 Matrix Strategy

```yaml
strategy:
  fail-fast: false
  matrix:
    include:
      - os: macos-14
        platform: macos
        arch: arm64
      - os: macos-15-intel
        platform: macos
        arch: x86_64
      - os: ubuntu-latest
        platform: linux
        arch: x86_64
      - os: ubuntu-24.04-arm
        platform: linux
        arch: arm64
      - os: windows-latest
        platform: windows
        arch: x86_64
```

### 6.3 Build Time Estimates

| Platform | Estimated Time |
|----------|---------------|
| macOS ARM64 | 10-15 min |
| macOS x86_64 | 10-15 min |
| Linux x86_64 | 8-12 min |
| Linux ARM64 | 12-18 min |
| Windows x86_64 | 15-20 min |

**Total workflow**: ~20-25 min (parallel builds)

### 6.4 Recommended Timeout

Set `timeout-minutes: 30` per job for safety margin.

### 6.5 Artifact Naming

| Platform | Archive Name |
|----------|-------------|
| macOS ARM64 | `pgtail-macos-arm64.tar.gz` |
| macOS x86_64 | `pgtail-macos-x86_64.tar.gz` |
| Linux x86_64 | `pgtail-linux-x86_64.tar.gz` |
| Linux ARM64 | `pgtail-linux-arm64.tar.gz` |
| Windows | `pgtail-windows-x86_64.zip` + `pgtail-windows-x86_64.msi` |

### 6.6 Verification Pattern

```yaml
- name: Verify build
  run: |
    ./dist/pgtail-${{ matrix.platform }}-${{ matrix.arch }}/pgtail --version
```

---

## 7. Dependencies to Add

### 7.1 pyproject.toml Update

```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "nuitka>=2.5,<3.0",  # Pin to stable 2.x series
]
```

---

## 8. Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Textual/Rich compilation issues | Use Nuitka >= 2.0 (fixed in 1.4.2+); test thoroughly |
| psutil native extension | Explicit `--include-package=psutil` |
| Dynamic imports missed | Explicit `--include-module` for conditional imports |
| CLI help text blank | NEVER use `--python-flag=no_docstrings` |
| Version shows 0.0.0-dev | Add `__version__` fallback before migration |
| Build timeout | Set 30 min timeout; builds run in parallel |
| winget PR rejection | Follow manifest format precisely; MSI-based submission |

---

## References

- [Nuitka User Manual](https://nuitka.net/user-documentation/user-manual.html)
- [Nuitka Package Configuration](https://nuitka.net/user-documentation/nuitka-package-config.html)
- [WiX Toolset 5.x Documentation](https://docs.firegiant.com/wix/using-wix/)
- [winget-pkgs CONTRIBUTING.md](https://github.com/microsoft/winget-pkgs/blob/master/CONTRIBUTING.md)
- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [uv GitHub Integration](https://docs.astral.sh/uv/guides/integration/github/)
- Local reference: `/Users/brandon/src/winget-pkgs` (winget manifest examples)
