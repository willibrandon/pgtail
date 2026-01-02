# Nuitka Migration Design Document

**Feature:** Migrate from PyInstaller to Nuitka for Binary Distribution
**Author:** Claude Code
**Date:** January 1, 2026
**Status:** Proposal
**Revision:** 2 (addressing Codex review feedback)

---

## Executive Summary

This document proposes migrating pgtail's binary distribution from PyInstaller to Nuitka to eliminate the 4.5-second cold start penalty observed in PyInstaller `--onefile` builds. Nuitka compiles Python to C, producing native executables with near-instant startup times while maintaining full CPython compatibility.

**Key Metrics:**
| Metric | PyInstaller (current) | Nuitka (projected) |
|--------|----------------------|-------------------|
| Startup time | 5.1s | <1s |
| Binary size | ~15 MB | ~20-30 MB |
| Build time | ~2 min | ~10-15 min |
| Runtime performance | Same as Python | 10-30% faster |

---

## Problem Statement

### Current Cold Start Performance

```
$ time pgtail --check-update
pgtail 0.1.0 is up to date.
pgtail --check-update  0.23s user 0.09s system 6% cpu 5.100 total

$ time uv run pgtail --check-update
pgtail 0.1.0 is up to date.
uv run pgtail --check-update  0.08s user 0.03s system 16% cpu 0.659 total
```

**Root Cause:** PyInstaller `--onefile` bundles the entire Python runtime and dependencies into a compressed archive. On every execution, this archive is extracted to a temporary directory before the application can start. This extraction overhead adds ~4.5 seconds to every invocation.

### Impact

- Poor user experience for quick operations (`--version`, `--check-update`, `list`)
- Perception of sluggishness compared to native CLI tools
- Defeats the purpose of having a compiled binary for distribution

---

## Current State Analysis

### pgtail Codebase Profile

| Aspect | Value |
|--------|-------|
| Python version | 3.10+ |
| Source files | 64 modules |
| Lines of code | ~20,000 |
| Pure Python | 99.5% |
| Native extensions | 1 (psutil) |

### Runtime Dependencies

| Package | Version | Type | Nuitka Compatibility |
|---------|---------|------|---------------------|
| prompt_toolkit | >=3.0.0 | Pure Python | Supported |
| psutil | >=5.9.0 | **Native extension** | Supported (requires config) |
| tomlkit | >=0.12.0 | Pure Python | Supported |
| pygments | >=2.0 | Pure Python | Supported |
| textual | >=0.89.0 | Pure Python | Supported (fixed in Nuitka 1.4.2+) |
| pyperclip | >=1.8.0 | Pure Python | Supported |
| typer | >=0.9.0 | Pure Python | Supported (**uses docstrings for help**) |
| certifi | >=2023.0.0 | Data files | Requires `--include-package-data` |

### Platform-Specific Code

pgtail contains conditional imports for cross-platform support:

```python
# detector.py
if sys.platform == "win32":
    from pgtail_py import detector_windows as platform_detector
else:
    from pgtail_py import detector_unix as platform_detector
```

**Files with platform-specific logic:**
- `detector.py`, `detector_unix.py`, `detector_windows.py`
- `config.py` (config paths)
- `notifier.py`, `notifier_unix.py`, `notifier_windows.py`
- `version.py` (install method detection)

### Current Build Process

```yaml
# .github/workflows/release.yml
uv run pyinstaller --onefile --collect-data certifi \
    --name pgtail-${{ matrix.platform }}-${{ matrix.arch }} \
    pgtail_py/__main__.py
```

**Platforms built:**
- macOS ARM64 (macos-14)
- macOS x86_64 (macos-15-intel)
- Linux x86_64 (ubuntu-latest)
- Linux ARM64 (ubuntu-24.04-arm)
- Windows x86_64 (windows-latest)

### Version Detection

pgtail uses `importlib.metadata.version("pgtail")` to get the version at runtime (`pgtail_py/version.py:47-56`). This requires package metadata (`.dist-info`) to be available. Without it, the fallback returns `0.0.0-dev`.

**This is a critical consideration for Nuitka builds** - we must either:
1. Include the package metadata in the distribution, OR
2. Add a hardcoded `__version__` fallback in the package

---

## Nuitka Overview

### What is Nuitka?

Nuitka is a Python compiler that translates Python source code to C, then compiles it to native machine code. Unlike PyInstaller (which bundles an interpreter), Nuitka produces true compiled executables.

**Key characteristics:**
- Full CPython compatibility (2.6, 2.7, 3.4-3.13)
- Generates C code using libpython for runtime support
- Produces standalone executables or Python extension modules
- Active development with regular releases

### Compilation Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| Accelerated | Default; depends on Python installation | Development/testing |
| Standalone | Self-contained with all dependencies | Distribution (folder) |
| Onefile | Single executable, extracts at runtime | Distribution (single file) |

**Recommendation:** Use `--mode=standalone` for pgtail. This avoids the extraction overhead of `--onefile` while still producing a self-contained distribution. The tradeoff is a folder instead of a single file, but startup is near-instant.

### Why Nuitka Over PyInstaller?

| Factor | Nuitka | PyInstaller |
|--------|--------|-------------|
| **Startup time** | Near-instant (native code) | Slow (extracts archive) |
| **Runtime performance** | 10-30% faster (compiled) | Same as interpreter |
| **Binary size** | Larger (~2x standalone) | Smaller |
| **Build time** | Slower (C compilation) | Fast |
| **Compatibility** | Excellent | Excellent |
| **Obfuscation** | Built-in (commercial) | None |

Sources: [Nuitka vs PyInstaller comparison](https://coderslegacy.com/nuitka-vs-pyinstaller/), [KRRT7 analysis](https://krrt7.dev/en/blog/nuitka-vs-pyinstaller)

---

## Technical Design

### Compilation Strategy

Use `--mode=standalone` instead of `--mode=onefile`:

```bash
nuitka \
    --mode=standalone \
    --output-dir=dist \
    --output-filename=pgtail \
    pgtail_py/__main__.py
```

**Rationale:**
- Standalone mode eliminates extraction overhead (instant startup)
- Onefile mode would reintroduce the same problem as PyInstaller
- Distribution is a folder, but can be archived (tar.gz/zip) for downloads

### Module Inclusion

pgtail uses lazy imports and conditional platform imports. Nuitka's static analysis may miss these:

```bash
# Explicit module inclusion for dynamic imports
--include-module=pgtail_py.detector_unix
--include-module=pgtail_py.detector_windows
--include-module=pgtail_py.notifier_unix
--include-module=pgtail_py.notifier_windows

# Include entire package to ensure nothing is missed
--include-package=pgtail_py
```

### Data File Handling

```bash
# certifi CA bundle for HTTPS
--include-package-data=certifi

# Theme files (if not compiled)
--include-data-dir=pgtail_py/themes=pgtail_py/themes
```

### Native Extension: psutil

psutil contains platform-specific C extensions (`_psutil_osx.so`, `_psutil_windows.pyd`). Nuitka handles these automatically in standalone mode, but explicit inclusion ensures reliability:

```bash
--include-package=psutil
```

**Known issues (resolved):**
- [Issue #673](https://github.com/Nuitka/Nuitka/issues/673): Module not found - fixed with `--standalone`
- [Issue #2155](https://github.com/Nuitka/Nuitka/issues/2155): Missing DLL on Windows - fixed in Nuitka 1.5.6+

### Textual Framework

Textual (the TUI framework pgtail uses) had a [known issue](https://github.com/Nuitka/Nuitka/issues/2025) with Nuitka 1.4 causing assertion failures in the Rich library. This was fixed in Nuitka 1.4.2+.

**Requirement:** Use Nuitka >= 2.0 (current stable is 2.5+)

### Optimization Flags

```bash
# Remove assert statements (safe optimization)
--python-flag=no_asserts
```

**Flags NOT to use:**
- ~~`--python-flag=no_docstrings`~~ - **DO NOT USE**: Typer relies on docstrings for CLI help text. Using this flag would make `pgtail list --help`, `pgtail tail --help`, etc. display blank descriptions.
- ~~`--python-flag=static_hashes`~~ - **DOES NOT EXIST**: This is not a valid CPython flag and will cause the build to fail.

### Version Metadata Solution

The current `get_version()` function uses `importlib.metadata.version("pgtail")` which requires `.dist-info` metadata. Two options:

**Option A: Include package metadata**
```bash
# Include the egg-info directory in the build (note: it's pgtail.egg-info, not pgtail_py.egg-info)
--include-data-dir=pgtail.egg-info=pgtail.egg-info
```

**Option B: Add hardcoded fallback**
```python
# In pgtail_py/__init__.py
__version__ = "0.2.0"

# In pgtail_py/version.py
def get_version() -> str:
    try:
        return importlib.metadata.version("pgtail")
    except importlib.metadata.PackageNotFoundError:
        from pgtail_py import __version__
        return __version__
```

**Recommendation:** Use Option B (hardcoded fallback). It's simpler, doesn't require build-time metadata generation, and the version is already defined in `pyproject.toml` - we just need to duplicate it.

### Complete Build Command

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

---

## GitHub Actions Integration

### Why NOT use Nuitka-Action

The official [Nuitka-Action](https://github.com/Nuitka/Nuitka-Action) runs `python -m nuitka` in the base system interpreter, NOT in the uv virtual environment. This means:

1. Project dependencies installed via `uv sync` won't be available
2. The build will fail because imports can't be resolved

**Solution:** Run Nuitka directly via `uv run nuitka` to ensure the virtual environment is active.

### Pinning Nuitka Version

Using `nuitka-version: main` in CI means every release build uses nightly Nuitka snapshots - high risk for regressions.

**Solution:** Pin to a stable release in `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "nuitka>=2.5,<3.0",  # Pin to stable 2.x series
]
```

### Artifact Naming Convention

All artifacts follow a consistent pattern:

| Component | Format |
|-----------|--------|
| Archive name | `pgtail-{platform}-{arch}.tar.gz` (Unix) or `.zip` (Windows) |
| Folder inside archive | `pgtail-{platform}-{arch}/` |
| Executable inside folder | `pgtail` (Unix) or `pgtail.exe` (Windows) |

**Examples:**
```
pgtail-macos-arm64.tar.gz
└── pgtail-macos-arm64/
    ├── pgtail              # main executable
    ├── libpython3.12.so    # runtime
    └── ...                 # other dependencies

pgtail-windows-x86_64.zip
└── pgtail-windows-x86_64/
    ├── pgtail.exe          # main executable
    ├── python312.dll       # runtime
    └── ...                 # other dependencies
```

### Updated Workflow

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  issues: write

jobs:
  build-unix:
    runs-on: ${{ matrix.os }}
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

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies (including Nuitka)
        run: uv sync --extra dev

      - name: Build with Nuitka
        run: |
          uv run nuitka \
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

      - name: Rename and verify build
        run: |
          mv dist/pgtail.dist dist/pgtail-${{ matrix.platform }}-${{ matrix.arch }}
          ./dist/pgtail-${{ matrix.platform }}-${{ matrix.arch }}/pgtail --version

      - name: Create archive
        run: |
          cd dist
          tar -czvf pgtail-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz \
            pgtail-${{ matrix.platform }}-${{ matrix.arch }}/

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: pgtail-${{ matrix.platform }}-${{ matrix.arch }}
          path: dist/pgtail-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz
          retention-days: 1

  build-windows:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - name: Extract version from tag
        id: version
        shell: pwsh
        run: |
          $version = "${{ github.ref_name }}" -replace '^v', ''
          echo "version=$version" >> $env:GITHUB_OUTPUT

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies (including Nuitka)
        run: uv sync --extra dev

      - name: Build with Nuitka
        run: |
          uv run nuitka `
            --mode=standalone `
            --output-dir=dist `
            --output-filename=pgtail `
            --include-package=pgtail_py `
            --include-package=psutil `
            --include-package-data=certifi `
            --include-module=pgtail_py.detector_unix `
            --include-module=pgtail_py.detector_windows `
            --include-module=pgtail_py.notifier_unix `
            --include-module=pgtail_py.notifier_windows `
            --python-flag=no_asserts `
            --assume-yes-for-downloads `
            pgtail_py/__main__.py

      - name: Rename and verify build
        run: |
          Move-Item dist\pgtail.dist dist\pgtail-windows-x86_64
          .\dist\pgtail-windows-x86_64\pgtail.exe --version

      - name: Create ZIP archive
        run: |
          cd dist
          7z a pgtail-windows-x86_64.zip pgtail-windows-x86_64\

      - name: Build MSI installer with WiX
        run: |
          # Install WiX toolset
          dotnet tool install --global wix --version 5.0.0

          # Use heat to harvest all files from the Nuitka output
          # This properly enumerates every DLL, PYD, and exe
          wix extension add WixToolset.Util.wixext
          wix extension add WixToolset.UI.wixext

          # Create WiX source file
          @"
          <?xml version="1.0" encoding="UTF-8"?>
          <Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"
               xmlns:util="http://wixtoolset.org/schemas/v4/wxs/util">

            <Package Name="pgtail"
                     Version="${{ steps.version.outputs.version }}.0"
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
          "@ | Out-File -FilePath pgtail.wxs -Encoding UTF8

          # Harvest files from the Nuitka output directory
          wix heat dir dist\pgtail-windows-x86_64 -cg PgtailFiles -dr INSTALLFOLDER `
            -gg -sfrag -srd -sreg -var var.SourceDir -out files.wxs

          # Build the MSI
          wix build pgtail.wxs files.wxs -d SourceDir=dist\pgtail-windows-x86_64 `
            -arch x64 -out dist\pgtail-windows-x86_64.msi

      - name: Verify MSI
        run: |
          if (Test-Path dist\pgtail-windows-x86_64.msi) {
            Write-Host "MSI built successfully: $((Get-Item dist\pgtail-windows-x86_64.msi).Length / 1MB) MB"
          } else {
            Write-Error "MSI build failed"
            exit 1
          }

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: pgtail-windows-x86_64
          path: |
            dist/pgtail-windows-x86_64.zip
            dist/pgtail-windows-x86_64.msi
          retention-days: 1

  release:
    needs: [build-unix, build-windows]
    runs-on: ubuntu-latest
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Prepare release files
        run: |
          mkdir -p release
          mv artifacts/pgtail-macos-arm64/pgtail-macos-arm64.tar.gz release/
          mv artifacts/pgtail-macos-x86_64/pgtail-macos-x86_64.tar.gz release/
          mv artifacts/pgtail-linux-x86_64/pgtail-linux-x86_64.tar.gz release/
          mv artifacts/pgtail-linux-arm64/pgtail-linux-arm64.tar.gz release/
          mv artifacts/pgtail-windows-x86_64/pgtail-windows-x86_64.zip release/
          mv artifacts/pgtail-windows-x86_64/pgtail-windows-x86_64.msi release/

      - name: Calculate SHA256 checksums
        id: checksums
        run: |
          cd release
          for f in pgtail-*; do
            sha256sum "$f" > "$f.sha256"
          done
          cat *.sha256

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            release/pgtail-macos-arm64.tar.gz
            release/pgtail-macos-arm64.tar.gz.sha256
            release/pgtail-macos-x86_64.tar.gz
            release/pgtail-macos-x86_64.tar.gz.sha256
            release/pgtail-linux-x86_64.tar.gz
            release/pgtail-linux-x86_64.tar.gz.sha256
            release/pgtail-linux-arm64.tar.gz
            release/pgtail-linux-arm64.tar.gz.sha256
            release/pgtail-windows-x86_64.zip
            release/pgtail-windows-x86_64.zip.sha256
            release/pgtail-windows-x86_64.msi
            release/pgtail-windows-x86_64.msi.sha256
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  update-homebrew:
    needs: release
    runs-on: ubuntu-latest
    steps:
      - name: Extract version from tag
        id: version
        run: |
          VERSION="${GITHUB_REF#refs/tags/v}"
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Clone homebrew-tap repository
        run: |
          git clone https://x-access-token:${{ secrets.HOMEBREW_TAP_TOKEN }}@github.com/willibrandon/homebrew-tap.git
          cd homebrew-tap
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Download checksums
        run: |
          cd homebrew-tap
          for platform in macos-arm64 macos-x86_64 linux-arm64 linux-x86_64; do
            curl -sL "https://github.com/willibrandon/pgtail/releases/download/v${{ steps.version.outputs.version }}/pgtail-${platform}.tar.gz.sha256" \
              -o "pgtail-${platform}.sha256"
          done

      - name: Update formula
        run: |
          cd homebrew-tap
          VERSION="${{ steps.version.outputs.version }}"

          # Read checksums
          SHA_MACOS_ARM64=$(cut -d' ' -f1 pgtail-macos-arm64.sha256)
          SHA_MACOS_X86_64=$(cut -d' ' -f1 pgtail-macos-x86_64.sha256)
          SHA_LINUX_ARM64=$(cut -d' ' -f1 pgtail-linux-arm64.sha256)
          SHA_LINUX_X86_64=$(cut -d' ' -f1 pgtail-linux-x86_64.sha256)

          cat > Formula/pgtail.rb << 'FORMULA'
          # typed: false
          # frozen_string_literal: true

          class Pgtail < Formula
            desc "Interactive PostgreSQL log tailer with auto-detection and color output"
            homepage "https://github.com/willibrandon/pgtail"
            license "MIT"
            version "VERSION_PLACEHOLDER"

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

              # Symlink the executable
              bin.install_symlink libexec/"pgtail"
            end

            test do
              assert_match version.to_s, shell_output("#{bin}/pgtail --version")
            end
          end
          FORMULA

          # Replace placeholders
          sed -i "s/VERSION_PLACEHOLDER/$VERSION/" Formula/pgtail.rb
          sed -i "s/SHA_MACOS_ARM64_PLACEHOLDER/$SHA_MACOS_ARM64/" Formula/pgtail.rb
          sed -i "s/SHA_MACOS_X86_64_PLACEHOLDER/$SHA_MACOS_X86_64/" Formula/pgtail.rb
          sed -i "s/SHA_LINUX_ARM64_PLACEHOLDER/$SHA_LINUX_ARM64/" Formula/pgtail.rb
          sed -i "s/SHA_LINUX_X86_64_PLACEHOLDER/$SHA_LINUX_X86_64/" Formula/pgtail.rb

      - name: Commit and push
        run: |
          cd homebrew-tap
          rm -f pgtail-*.sha256
          git add Formula/pgtail.rb
          git diff --staged --quiet || git commit -m "Update pgtail to ${{ steps.version.outputs.version }}"
          git push origin main

  update-winget:
    needs: release
    runs-on: windows-latest
    steps:
      - name: Extract version from tag
        id: version
        shell: pwsh
        run: |
          $version = "${{ github.ref_name }}" -replace '^v', ''
          echo "version=$version" >> $env:GITHUB_OUTPUT

      - name: Check if package exists in winget-pkgs
        id: check
        shell: pwsh
        run: |
          $response = Invoke-WebRequest -Uri "https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/w/willibrandon/pgtail" -Method Head -SkipHttpErrorCheck
          if ($response.StatusCode -eq 200) {
            echo "exists=true" >> $env:GITHUB_OUTPUT
          } else {
            echo "exists=false" >> $env:GITHUB_OUTPUT
          }

      - name: Install wingetcreate
        shell: pwsh
        run: |
          Invoke-WebRequest -Uri https://aka.ms/wingetcreate/latest -OutFile wingetcreate.exe

      - name: Create new winget manifest (first time)
        if: steps.check.outputs.exists == 'false'
        shell: pwsh
        env:
          WINGET_PKGS_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
          GH_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
        run: |
          $version = "${{ steps.version.outputs.version }}"
          $url = "https://github.com/willibrandon/pgtail/releases/download/v$version/pgtail-windows-x86_64.msi"

          # Download MSI to calculate hash and extract ProductCode
          Invoke-WebRequest -Uri $url -OutFile pgtail.msi
          $hash = (Get-FileHash -Path pgtail.msi -Algorithm SHA256).Hash

          # Extract ProductCode from MSI (auto-generated by WiX, changes per version)
          $productCode = (Get-AppLockerFileInformation -Path pgtail.msi | Select-Object -ExpandProperty Publisher).BinaryName
          # Alternative: Use wix msi info if Get-AppLockerFileInformation doesn't work
          # $productCode = (wix msi info pgtail.msi | Select-String "ProductCode").ToString().Split(":")[1].Trim()

          # Create manifests directory structure
          New-Item -ItemType Directory -Force -Path "manifests/w/willibrandon/pgtail/$version"

          # Generate version manifest
          @"
          PackageIdentifier: willibrandon.pgtail
          PackageVersion: $version
          DefaultLocale: en-US
          ManifestType: version
          ManifestVersion: 1.6.0
          "@ | Out-File -FilePath "manifests/w/willibrandon/pgtail/$version/willibrandon.pgtail.yaml" -Encoding UTF8

          # Generate installer manifest with MSI
          @"
          PackageIdentifier: willibrandon.pgtail
          PackageVersion: $version
          Platform:
            - Windows.Desktop
          MinimumOSVersion: 10.0.18362.0
          InstallerType: msi
          Scope: machine
          InstallModes:
            - interactive
            - silent
            - silentWithProgress
          Installers:
            - Architecture: x64
              InstallerUrl: $url
              InstallerSha256: $hash
              ProductCode: '$productCode'  # Extracted from built MSI, changes per version
          ManifestType: installer
          ManifestVersion: 1.6.0
          "@ | Out-File -FilePath "manifests/w/willibrandon/pgtail/$version/willibrandon.pgtail.installer.yaml" -Encoding UTF8

          # Generate locale manifest
          @"
          PackageIdentifier: willibrandon.pgtail
          PackageVersion: $version
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
          ManifestVersion: 1.6.0
          "@ | Out-File -FilePath "manifests/w/willibrandon/pgtail/$version/willibrandon.pgtail.locale.en-US.yaml" -Encoding UTF8

          # Clone fork (not upstream - we don't have push access to microsoft/winget-pkgs)
          git clone https://x-access-token:$env:WINGET_PKGS_TOKEN@github.com/willibrandon/winget-pkgs.git --depth 1
          Copy-Item -Recurse manifests/w/willibrandon winget-pkgs/manifests/w/
          cd winget-pkgs
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          # Add upstream remote for PR creation
          git remote add upstream https://github.com/microsoft/winget-pkgs.git
          git fetch upstream master --depth 1

          git checkout -b willibrandon.pgtail-$version
          git add manifests/w/willibrandon/pgtail/$version
          git commit -m "New package: willibrandon.pgtail version $version"
          git push origin willibrandon.pgtail-$version

          # Create PR from fork to upstream using gh CLI
          gh pr create --repo microsoft/winget-pkgs `
            --head willibrandon:willibrandon.pgtail-$version `
            --title "New package: willibrandon.pgtail version $version" `
            --body "## Package Information`n`nPackage: willibrandon.pgtail`nVersion: $version`n`nAutomated submission from GitHub Actions release workflow."

      - name: Update existing winget manifest
        if: steps.check.outputs.exists == 'true'
        shell: pwsh
        env:
          WINGET_PKGS_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
        run: |
          $version = "${{ steps.version.outputs.version }}"
          $url = "https://github.com/willibrandon/pgtail/releases/download/v$version/pgtail-windows-x86_64.msi"

          # Use wingetcreate update for existing packages
          .\wingetcreate.exe update willibrandon.pgtail `
            --version $version `
            --urls $url `
            --token $env:WINGET_PKGS_TOKEN `
            --submit

  notify-failure:
    needs: [build-unix, build-windows, release, update-homebrew, update-winget]
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Create failure issue
        uses: actions/github-script@v7
        with:
          script: |
            const { owner, repo } = context.repo;
            const runUrl = `https://github.com/${owner}/${repo}/actions/runs/${context.runId}`;
            const tag = context.ref.replace('refs/tags/', '');

            await github.rest.issues.create({
              owner,
              repo,
              title: `Release ${tag} failed`,
              body: `The release workflow for ${tag} failed.\n\nSee the [workflow run](${runUrl}) for details.`,
              labels: ['bug', 'release']
            });
```

### Build Time Expectations

| Platform | PyInstaller | Nuitka (estimated) |
|----------|-------------|-------------------|
| macOS ARM64 | ~2 min | ~10-15 min |
| macOS x86_64 | ~2 min | ~10-15 min |
| Linux x86_64 | ~2 min | ~8-12 min |
| Linux ARM64 | ~3 min | ~12-18 min |
| Windows x86_64 | ~3 min | ~15-20 min |

**Total workflow time:** ~15-20 min (parallel) vs current ~8-10 min

---

## Distribution Changes

### Current (PyInstaller)

Single executable files:
```
pgtail-macos-arm64      (14.8 MB)
pgtail-macos-x86_64     (15.2 MB)
pgtail-linux-x86_64     (15.5 MB)
pgtail-linux-arm64      (14.9 MB)
pgtail-windows-x86_64.exe (16.1 MB)
```

### Proposed (Nuitka)

Compressed archives containing folders:
```
pgtail-macos-arm64.tar.gz     (~20-25 MB)
├── pgtail-macos-arm64/
│   ├── pgtail
│   └── ... (dependencies)

pgtail-windows-x86_64.zip     (~22-28 MB)
├── pgtail-windows-x86_64/
│   ├── pgtail.exe
│   └── ... (dependencies)
```

### Installation Instructions Update

**macOS/Linux (archive):**
```bash
# Download and extract
curl -L https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-macos-arm64.tar.gz | tar xz

# Install to system
sudo mv pgtail-macos-arm64 /usr/local/lib/pgtail
sudo ln -s /usr/local/lib/pgtail/pgtail /usr/local/bin/pgtail

# Or install to user directory (no sudo)
mkdir -p ~/.local/lib ~/.local/bin
mv pgtail-macos-arm64 ~/.local/lib/pgtail
ln -s ~/.local/lib/pgtail/pgtail ~/.local/bin/pgtail
```

**Windows (archive):**
```powershell
# Download and extract
Invoke-WebRequest -Uri "https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-windows-x86_64.zip" -OutFile pgtail.zip
Expand-Archive pgtail.zip -DestinationPath $env:LOCALAPPDATA

# Add to PATH (current session)
$env:PATH += ";$env:LOCALAPPDATA\pgtail-windows-x86_64"

# Add to PATH (permanent - requires admin or user PATH modification)
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:LOCALAPPDATA\pgtail-windows-x86_64", "User")
```

### Windows Distribution

Windows users get two options:

| Format | Use Case | Install Location |
|--------|----------|------------------|
| **MSI** | winget, enterprise, Program Files | `C:\Program Files\pgtail\` |
| **ZIP** | Manual download, portable, no admin | Extract anywhere |

**MSI Installer (for winget):**

Built with WiX Toolset, the MSI:
- Installs to `Program Files\pgtail\`
- Adds to system PATH
- Registers in Apps & Features
- Supports clean upgrade/uninstall
- Enterprise-friendly (GPO/SCCM compatible)

**ZIP Archive (for manual download):**

The ZIP contains the standalone folder:
- Extract anywhere
- No admin rights needed
- Add to PATH manually or run from extracted location
- Portable across machines

**winget manifest (MSI-based):**
```yaml
# willibrandon.pgtail.installer.yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: "0.2.0"
Platform:
  - Windows.Desktop
MinimumOSVersion: 10.0.18362.0
InstallerType: msi
Installers:
  - Architecture: x64
    InstallerUrl: https://github.com/willibrandon/pgtail/releases/download/v0.2.0/pgtail-windows-x86_64.msi
    InstallerSha256: PLACEHOLDER
ManifestType: installer
ManifestVersion: 1.6.0
```

**Migration strategy:**

1. ~~Close PR #327272~~ ✅ **DONE** (closed 2026-01-01 with comment: "Closing to submit fresh PR with MSI installer after migrating from PyInstaller to Nuitka for v0.2.0")
2. Implement Nuitka migration (this document)
3. Release v0.2.0 immediately after CI passes
4. Submit fresh winget PR with MSI installer
5. One review cycle (~7 days), package goes live with correct format from the start
6. Subsequent releases use `wingetcreate update` normally

---

## Pre-Migration Code Changes

Before switching to Nuitka, make these changes to pgtail:

### 1. Add `__version__` Fallback

Create or update `pgtail_py/__init__.py`:
```python
"""pgtail - Interactive PostgreSQL log tailer."""

__version__ = "0.2.0"
```

Update `pgtail_py/version.py`:
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

### 2. Add Nuitka to Dev Dependencies

Update `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "nuitka>=2.5,<3.0",
]
```

### 3. Update Makefile

Replace PyInstaller `build` target with Nuitka. Update `Makefile`:

```makefile
.PHONY: help run test test-perf lint format build build-test clean shell docs docs-serve

# Detect OS for platform-specific commands
ifeq ($(OS),Windows_NT)
    DETECTED_OS := Windows
    UV := $(USERPROFILE)\.local\bin\uv.exe
else
    DETECTED_OS := $(shell uname -s)
    UV := uv
endif

# Nuitka build output path (normalized architecture)
# uname -m returns: x86_64, amd64, arm64, aarch64
# Normalize to: x86_64, arm64
NUITKA_PLATFORM := $(shell uname -s | tr '[:upper:]' '[:lower:]')
NUITKA_ARCH_RAW := $(shell uname -m)
NUITKA_ARCH := $(if $(filter aarch64,$(NUITKA_ARCH_RAW)),arm64,$(if $(filter amd64,$(NUITKA_ARCH_RAW)),x86_64,$(NUITKA_ARCH_RAW)))
NUITKA_DIST := dist/pgtail-$(NUITKA_PLATFORM)-$(NUITKA_ARCH)

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  run        Run pgtail from source"
	@echo "  test       Run pytest (excludes performance tests)"
	@echo "  test-perf  Run performance tests only"
	@echo "  lint       Run ruff linter"
	@echo "  format     Format code with ruff"
	@echo "  build      Build standalone executable with Nuitka"
	@echo "  build-test Build and run basic verification tests"
	@echo "  clean      Remove build artifacts"
	@echo "  shell      Enter virtual environment shell"
	@echo "  docs       Build documentation site"
	@echo "  docs-serve Serve documentation locally"

# ... (shell, run, test, test-perf, lint, format targets unchanged) ...

build:
ifeq ($(DETECTED_OS),Windows)
	$(UV) run nuitka \
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
	move dist\pgtail.dist dist\pgtail-windows-x86_64
	@echo "Build complete: dist\pgtail-windows-x86_64\pgtail.exe"
else
	$(UV) run nuitka \
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
	mv dist/pgtail.dist $(NUITKA_DIST)
	@echo "Build complete: $(NUITKA_DIST)/pgtail"
endif

build-test: build
ifeq ($(DETECTED_OS),Windows)
	dist\pgtail-windows-x86_64\pgtail.exe --version
	dist\pgtail-windows-x86_64\pgtail.exe list --help
else
	$(NUITKA_DIST)/pgtail --version
	$(NUITKA_DIST)/pgtail list --help
endif

clean:
ifeq ($(DETECTED_OS),Windows)
	-@if exist build rd /s /q build
	-@if exist dist rd /s /q dist
	-@if exist .pytest_cache rd /s /q .pytest_cache
	-@if exist .ruff_cache rd /s /q .ruff_cache
	-@if exist pgtail_py\__pycache__ rd /s /q pgtail_py\__pycache__
	-@if exist tests\__pycache__ rd /s /q tests\__pycache__
	-@if exist site rd /s /q site
	-@if exist pgtail.build rd /s /q pgtail.build
	-@if exist pgtail.dist rd /s /q pgtail.dist
	-@if exist pgtail.onefile-build rd /s /q pgtail.onefile-build
else
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .ruff_cache/ site/
	rm -rf pgtail.build/ pgtail.dist/ pgtail.onefile-build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
endif

# ... (docs, docs-serve targets unchanged) ...
```

**Key changes:**
- `build` target now uses Nuitka instead of PyInstaller
- Added `build-test` target to verify the build works
- Added architecture normalization for consistent output paths
- Added Nuitka build artifacts to `clean` target
- Windows and Unix handled separately due to shell differences

### 4. Add Build Scripts

Create `scripts/build-nuitka.sh`:
```bash
#!/bin/bash
set -euo pipefail

PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

case "$ARCH" in
    x86_64|amd64) ARCH="x86_64" ;;
    arm64|aarch64) ARCH="arm64" ;;
esac

OUTPUT_NAME="pgtail-${PLATFORM}-${ARCH}"

echo "Building pgtail for ${PLATFORM}/${ARCH}..."

uv run nuitka \
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

mv dist/pgtail.dist "dist/${OUTPUT_NAME}"

echo "Build complete: dist/${OUTPUT_NAME}/"
echo "Test with: ./dist/${OUTPUT_NAME}/pgtail --version"
```

---

## Risk Assessment

### High Risk

| Risk | Mitigation |
|------|------------|
| Textual/Rich compilation issues | Use Nuitka >= 2.0; test thoroughly |
| psutil native extension problems | Explicit `--include-package=psutil`; test on all platforms |
| Increased build time breaks CI | Increase timeout; builds run in parallel |

### Medium Risk

| Risk | Mitigation |
|------|------------|
| Larger binary size exceeds limits | Current limit is 50MB; projected ~25MB is safe |
| Platform-specific compilation failures | Test locally before CI; use matrix builds |
| Dynamic imports not detected | Explicit `--include-module` for all conditional imports |
| Version shows 0.0.0-dev | Add `__version__` fallback before migration |

### Low Risk

| Risk | Mitigation |
|------|------------|
| User confusion with folder distribution | Clear installation instructions; Homebrew handles it |
| C compiler availability in CI | GitHub runners have compilers pre-installed |

### Flags Not Used

| Flag | Reason |
|------|--------|
| `--python-flag=no_docstrings` | Breaks Typer CLI help text |
| `--python-flag=static_hashes` | Invalid CPython flag, causes build failure |

---

## Testing Strategy

### Phase 1: Local Validation

1. Apply code changes (version fallback)
2. Build locally on macOS ARM64:
   ```bash
   uv sync --extra dev
   ./scripts/build-nuitka.sh
   ```

3. Verify functionality:
   ```bash
   ./dist/pgtail-darwin-arm64/pgtail --version
   ./dist/pgtail-darwin-arm64/pgtail --check-update
   ./dist/pgtail-darwin-arm64/pgtail list
   ./dist/pgtail-darwin-arm64/pgtail list --help  # Verify docstrings work
   ./dist/pgtail-darwin-arm64/pgtail tail 0
   ```

4. Measure startup time:
   ```bash
   time ./dist/pgtail-darwin-arm64/pgtail --version
   ```

### Phase 2: Cross-Platform CI

1. Create feature branch `feature/nuitka-migration`
2. Add Nuitka workflow alongside existing PyInstaller workflow
3. Build and test on all 5 platforms (4 with full support, Windows without winget)
4. Compare binary sizes and startup times

### Phase 3: Beta Release

1. Release v0.2.0-beta.1 with Nuitka builds
2. Gather user feedback on:
   - Installation experience
   - Startup performance
   - Any runtime issues

### Phase 4: Production Release

1. Remove PyInstaller workflow
2. Release v0.2.0 with Nuitka builds
3. Update documentation and Homebrew formula

---

## Rollback Plan

If Nuitka builds prove problematic:

1. Revert to PyInstaller workflow (preserved in git history)
2. Release patch version with PyInstaller builds
3. Document issues encountered for future reference

The PyInstaller workflow is well-tested and can be restored within minutes.

---

## Success Criteria

1. **Startup time < 1 second** for `pgtail --version`
2. **All existing functionality works** (REPL, tail mode, detection, notifications)
3. **CLI help text displays correctly** (`pgtail list --help` shows descriptions)
4. **Version displays correctly** (`pgtail --version` shows actual version, not 0.0.0-dev)
5. **Binary size < 50 MB** per platform
6. **Build time < 30 minutes** total workflow
7. **Zero regressions** in test suite
8. **Homebrew installation works** (`brew install willibrandon/tap/pgtail`)
9. **winget installation works** (`winget install pgtail`) with MSI installer
10. **All 5 platforms build successfully** (macOS ARM64/x86_64, Linux ARM64/x86_64, Windows x86_64)
11. **Windows ZIP available** for portable/manual installation

---

## References

- [Nuitka User Manual](https://nuitka.net/user-documentation/user-manual.html)
- [Nuitka GitHub](https://github.com/Nuitka/Nuitka)
- [Nuitka-Action](https://github.com/Nuitka/Nuitka-Action)
- [Nuitka vs PyInstaller](https://coderslegacy.com/nuitka-vs-pyinstaller/)
- [Nuitka Package Configuration](https://nuitka.net/user-documentation/nuitka-package-config.html)
- [Textual Nuitka Issue #2025](https://github.com/Nuitka/Nuitka/issues/2025) (fixed in 1.4.2)
- [psutil Nuitka Issues](https://github.com/Nuitka/Nuitka/issues/673)

---

## Appendix: Makefile Integration

```makefile
# Add to existing Makefile

# Helper to normalize architecture (matches build-nuitka.sh logic)
# uname -m returns: x86_64, amd64, arm64, aarch64
# We normalize to: x86_64, arm64
NUITKA_PLATFORM := $(shell uname -s | tr '[:upper:]' '[:lower:]')
NUITKA_ARCH_RAW := $(shell uname -m)
NUITKA_ARCH := $(if $(filter aarch64,$(NUITKA_ARCH_RAW)),arm64,$(if $(filter amd64,$(NUITKA_ARCH_RAW)),x86_64,$(NUITKA_ARCH_RAW)))
NUITKA_DIST := dist/pgtail-$(NUITKA_PLATFORM)-$(NUITKA_ARCH)

build-nuitka:
	./scripts/build-nuitka.sh

build-nuitka-test: build-nuitka
	$(NUITKA_DIST)/pgtail --version
	$(NUITKA_DIST)/pgtail list --help
```
