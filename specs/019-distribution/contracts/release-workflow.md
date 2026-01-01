# Contract: GitHub Actions Release Workflow

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This contract defines the GitHub Actions workflow for building and releasing pgtail binaries across all supported platforms.

---

## Workflow File

**Location**: `.github/workflows/release.yml`

---

## Trigger

```yaml
on:
  push:
    tags:
      - 'v*'
```

Workflow triggers when a version tag is pushed:
```bash
git tag v0.1.0
git push origin v0.1.0
```

---

## Jobs Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        release.yml                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    build (matrix)                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │  │
│  │  │ macOS   │ │ macOS   │ │ Linux   │ │ Linux   │     │  │
│  │  │ arm64   │ │ x86_64  │ │ x86_64  │ │ arm64   │     │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘     │  │
│  │       │           │           │           │          │  │
│  │  ┌────┴───────────┴───────────┴───────────┴────┐     │  │
│  │  │              upload artifacts               │     │  │
│  │  └─────────────────────────────────────────────┘     │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   build-windows                       │  │
│  │  ┌─────────┐                                          │  │
│  │  │ Windows │                                          │  │
│  │  │ x86_64  │                                          │  │
│  │  └────┬────┘                                          │  │
│  │       │                                               │  │
│  │  upload artifact                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               release (needs: build*)                 │  │
│  │  download all artifacts                               │  │
│  │  calculate checksums                                  │  │
│  │  create GitHub Release                                │  │
│  │  attach binaries + checksums                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            update-homebrew (needs: release)           │  │
│  │  update Formula/pgtail.rb                             │  │
│  │  push to homebrew-tap                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │             update-winget (needs: release)            │  │
│  │  generate manifest                                    │  │
│  │  submit PR to winget-pkgs                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Build Matrix

| Platform | Runner | Binary Name |
|----------|--------|-------------|
| macOS arm64 | `macos-14` | `pgtail-macos-arm64` |
| macOS x86_64 | `macos-13` | `pgtail-macos-x86_64` |
| Linux x86_64 | `ubuntu-latest` | `pgtail-linux-x86_64` |
| Linux arm64 | `ubuntu-24.04-arm` | `pgtail-linux-arm64` |
| Windows x86_64 | `windows-latest` | `pgtail-windows-x86_64.exe` |

---

## Workflow Specification

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: macos-14
            target: macos-arm64
            binary: pgtail-macos-arm64
          - os: macos-13
            target: macos-x86_64
            binary: pgtail-macos-x86_64
          - os: ubuntu-latest
            target: linux-x86_64
            binary: pgtail-linux-x86_64
          - os: ubuntu-24.04-arm
            target: linux-arm64
            binary: pgtail-linux-arm64

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Build binary
        run: |
          uv run pyinstaller --onefile --name ${{ matrix.binary }} pgtail_py/__main__.py

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.binary }}
          path: dist/${{ matrix.binary }}
          retention-days: 1

  build-windows:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Build binary
        run: |
          uv run pyinstaller --onefile --name pgtail-windows-x86_64 pgtail_py/__main__.py

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: pgtail-windows-x86_64.exe
          path: dist/pgtail-windows-x86_64.exe
          retention-days: 1

  release:
    needs: [build, build-windows]
    runs-on: ubuntu-latest

    outputs:
      sha256_macos_arm64: ${{ steps.checksums.outputs.macos_arm64 }}
      sha256_macos_x86_64: ${{ steps.checksums.outputs.macos_x86_64 }}
      sha256_linux_x86_64: ${{ steps.checksums.outputs.linux_x86_64 }}
      sha256_linux_arm64: ${{ steps.checksums.outputs.linux_arm64 }}
      sha256_windows: ${{ steps.checksums.outputs.windows }}

    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Prepare release files
        run: |
          mkdir -p release
          cp artifacts/pgtail-macos-arm64/pgtail-macos-arm64 release/
          cp artifacts/pgtail-macos-x86_64/pgtail-macos-x86_64 release/
          cp artifacts/pgtail-linux-x86_64/pgtail-linux-x86_64 release/
          cp artifacts/pgtail-linux-arm64/pgtail-linux-arm64 release/
          cp artifacts/pgtail-windows-x86_64.exe/pgtail-windows-x86_64.exe release/

      - name: Make binaries executable
        run: |
          chmod +x release/pgtail-macos-arm64
          chmod +x release/pgtail-macos-x86_64
          chmod +x release/pgtail-linux-x86_64
          chmod +x release/pgtail-linux-arm64

      - name: Calculate checksums
        id: checksums
        run: |
          cd release
          sha256sum pgtail-macos-arm64 > pgtail-macos-arm64.sha256
          sha256sum pgtail-macos-x86_64 > pgtail-macos-x86_64.sha256
          sha256sum pgtail-linux-x86_64 > pgtail-linux-x86_64.sha256
          sha256sum pgtail-linux-arm64 > pgtail-linux-arm64.sha256
          sha256sum pgtail-windows-x86_64.exe > pgtail-windows-x86_64.exe.sha256

          echo "macos_arm64=$(cat pgtail-macos-arm64.sha256 | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "macos_x86_64=$(cat pgtail-macos-x86_64.sha256 | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "linux_x86_64=$(cat pgtail-linux-x86_64.sha256 | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "linux_arm64=$(cat pgtail-linux-arm64.sha256 | cut -d' ' -f1)" >> $GITHUB_OUTPUT
          echo "windows=$(cat pgtail-windows-x86_64.exe.sha256 | cut -d' ' -f1)" >> $GITHUB_OUTPUT

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            release/pgtail-macos-arm64
            release/pgtail-macos-x86_64
            release/pgtail-linux-x86_64
            release/pgtail-linux-arm64
            release/pgtail-windows-x86_64.exe
            release/*.sha256
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  update-homebrew:
    needs: release
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Update Homebrew Formula
        env:
          HOMEBREW_TAP_TOKEN: ${{ secrets.HOMEBREW_TAP_TOKEN }}
        run: |
          VERSION="${GITHUB_REF_NAME#v}"

          git clone https://x-access-token:${HOMEBREW_TAP_TOKEN}@github.com/willibrandon/homebrew-tap.git tap

          cat > tap/Formula/pgtail.rb << 'FORMULA'
          class Pgtail < Formula
            desc "PostgreSQL log tailer with auto-detection and color output"
            homepage "https://github.com/willibrandon/pgtail"
            license "MIT"
            version "${{ github.ref_name }}"

            on_macos do
              on_arm do
                url "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-macos-arm64"
                sha256 "${{ needs.release.outputs.sha256_macos_arm64 }}"

                def install
                  bin.install "pgtail-macos-arm64" => "pgtail"
                end
              end

              on_intel do
                url "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-macos-x86_64"
                sha256 "${{ needs.release.outputs.sha256_macos_x86_64 }}"

                def install
                  bin.install "pgtail-macos-x86_64" => "pgtail"
                end
              end
            end

            on_linux do
              on_arm do
                url "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-linux-arm64"
                sha256 "${{ needs.release.outputs.sha256_linux_arm64 }}"

                def install
                  bin.install "pgtail-linux-arm64" => "pgtail"
                end
              end

              on_intel do
                url "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-linux-x86_64"
                sha256 "${{ needs.release.outputs.sha256_linux_x86_64 }}"

                def install
                  bin.install "pgtail-linux-x86_64" => "pgtail"
                end
              end
            end

            test do
              assert_match version.to_s, shell_output("#{bin}/pgtail --version")
            end
          end
          FORMULA

          # Replace version placeholder
          sed -i "s/\${{ github.ref_name }}/${GITHUB_REF_NAME}/g" tap/Formula/pgtail.rb

          cd tap
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add Formula/pgtail.rb
          git commit -m "Update pgtail to ${GITHUB_REF_NAME}"
          git push

  update-winget:
    needs: release
    runs-on: windows-latest

    steps:
      - name: Install wingetcreate
        run: |
          winget install wingetcreate --accept-source-agreements --accept-package-agreements

      - name: Submit to winget
        env:
          WINGET_PKGS_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
        run: |
          $version = "${{ github.ref_name }}".TrimStart("v")
          $url = "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-windows-x86_64.exe"

          wingetcreate update willibrandon.pgtail `
            --version $version `
            --urls $url `
            --submit `
            --token $env:WINGET_PKGS_TOKEN
```

---

## Required Secrets

| Secret | Purpose | Scope |
|--------|---------|-------|
| `GITHUB_TOKEN` | Create release, upload assets | Automatic |
| `HOMEBREW_TAP_TOKEN` | Push to homebrew-tap repo | `repo` scope PAT |
| `WINGET_PKGS_TOKEN` | Submit PR to winget-pkgs | `public_repo` scope PAT |

---

## Release Artifacts

| File | Description |
|------|-------------|
| `pgtail-macos-arm64` | macOS Apple Silicon binary |
| `pgtail-macos-x86_64` | macOS Intel binary |
| `pgtail-linux-x86_64` | Linux x86_64 binary |
| `pgtail-linux-arm64` | Linux ARM64 binary |
| `pgtail-windows-x86_64.exe` | Windows x64 executable |
| `*.sha256` | SHA256 checksums for each binary |

---

## Timing Expectations

| Job | Expected Duration |
|-----|-------------------|
| build (per platform) | 2-4 minutes |
| build-windows | 3-5 minutes |
| release | 1-2 minutes |
| update-homebrew | 1 minute |
| update-winget | 2-3 minutes |
| **Total** | ~10-15 minutes |

---

## Error Handling

### Build Failures

- `fail-fast: false` ensures one platform failure doesn't stop others
- Failed builds prevent release job from running
- Notifications via GitHub Actions email

### Release Failures

- If release job fails, artifacts still available for 1 day
- Can manually create release and upload artifacts
- Re-run workflow by re-pushing tag

### Package Manager Update Failures

- Homebrew/winget updates are separate jobs
- Failures don't affect release
- Can be manually triggered or re-run
