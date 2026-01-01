# Contract: winget Manifest

**Branch**: `019-distribution` | **Date**: 2026-01-01

## Overview

This contract defines the Windows Package Manager (winget) manifest structure for pgtail, submitted as a PR to `microsoft/winget-pkgs`.

---

## Directory Structure

```
manifests/w/willibrandon/pgtail/0.1.0/
├── willibrandon.pgtail.yaml
├── willibrandon.pgtail.locale.en-US.yaml
└── willibrandon.pgtail.installer.yaml
```

---

## Manifest Files

### Version Manifest: `willibrandon.pgtail.yaml`

```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.6.0
```

---

### Locale Manifest: `willibrandon.pgtail.locale.en-US.yaml`

```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
PackageLocale: en-US
Publisher: willibrandon
PublisherUrl: https://github.com/willibrandon
PublisherSupportUrl: https://github.com/willibrandon/pgtail/issues
PrivacyUrl: https://github.com/willibrandon/pgtail
Author: willibrandon
PackageName: pgtail
PackageUrl: https://github.com/willibrandon/pgtail
License: MIT
LicenseUrl: https://github.com/willibrandon/pgtail/blob/main/LICENSE
Copyright: Copyright (c) willibrandon
ShortDescription: PostgreSQL log tailer with auto-detection and color output
Description: >-
  pgtail is an interactive CLI tool for tailing PostgreSQL log files.
  It auto-detects PostgreSQL instances and provides real-time log streaming
  with level filtering, color output, and vim-style navigation.
Moniker: pgtail
Tags:
  - postgresql
  - log
  - tail
  - cli
  - database
  - developer-tools
  - postgres
ReleaseNotesUrl: https://github.com/willibrandon/pgtail/releases/tag/v0.1.0
ManifestType: defaultLocale
ManifestVersion: 1.6.0
```

---

### Installer Manifest: `willibrandon.pgtail.installer.yaml`

```yaml
PackageIdentifier: willibrandon.pgtail
PackageVersion: 0.1.0
Platform:
  - Windows.Desktop
MinimumOSVersion: 10.0.18362.0
InstallerType: portable
Commands:
  - pgtail
Installers:
  - Architecture: x64
    InstallerUrl: https://github.com/willibrandon/pgtail/releases/download/v0.1.0/pgtail-windows-x86_64.exe
    InstallerSha256: PLACEHOLDER_SHA256_WINDOWS
ManifestType: installer
ManifestVersion: 1.6.0
```

---

## Required Fields Summary

| Field | Value | File |
|-------|-------|------|
| `PackageIdentifier` | `willibrandon.pgtail` | All |
| `PackageVersion` | `0.1.0` | All |
| `DefaultLocale` | `en-US` | version |
| `Publisher` | `willibrandon` | locale |
| `PackageName` | `pgtail` | locale |
| `License` | `MIT` | locale |
| `ShortDescription` | Description text | locale |
| `InstallerType` | `portable` | installer |
| `InstallerUrl` | GitHub Release URL | installer |
| `InstallerSha256` | SHA256 hash | installer |
| `ManifestType` | Type identifier | All |
| `ManifestVersion` | `1.6.0` | All |

---

## Installation Commands

### End User

```powershell
# Search
winget search pgtail

# Install
winget install willibrandon.pgtail

# Show info
winget show willibrandon.pgtail
```

### Upgrade

```powershell
winget upgrade willibrandon.pgtail
```

### Uninstall

```powershell
winget uninstall willibrandon.pgtail
```

---

## Portable Installer Behavior

Since pgtail is a portable executable (no installer):

- `InstallerType: portable` tells winget this is a standalone EXE
- `Commands: [pgtail]` enables `pgtail` from command line after install
- winget places the EXE in a location on PATH
- No silent install switches needed

---

## Submission Process

### Initial Submission

1. **Fork** `microsoft/winget-pkgs`

2. **Create manifest directory**:
   ```
   manifests/w/willibrandon/pgtail/0.1.0/
   ```

3. **Add all three manifest files**

4. **Validate locally**:
   ```powershell
   winget validate manifests/w/willibrandon/pgtail/0.1.0/
   ```

5. **Submit PR** to `microsoft/winget-pkgs`

6. **Wait for review** (automated checks + human review)

### Update Process

For new versions:

1. Create new version directory: `manifests/w/willibrandon/pgtail/0.2.0/`
2. Copy and update all three manifest files
3. Submit PR

### Automated Updates (Release Workflow)

```yaml
- name: Update winget manifest
  if: runner.os == 'Windows'
  env:
    WINGET_PKGS_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
  run: |
    # Install wingetcreate
    winget install wingetcreate

    # Update and submit
    wingetcreate update willibrandon.pgtail `
      --version ${{ github.ref_name }} `
      --urls "https://github.com/willibrandon/pgtail/releases/download/${{ github.ref_name }}/pgtail-windows-x86_64.exe" `
      --submit `
      --token ${{ secrets.WINGET_PKGS_TOKEN }}
```

---

## Validation Requirements

### Automated Checks

- YAML syntax valid
- Required fields present
- SHA256 matches downloaded file
- InstallerUrl accessible
- No malware detected

### Manual Review Criteria

- Publisher matches GitHub account
- Package functions as described
- No duplicate package identifiers

---

## Testing

### Local Validation

```powershell
# Validate manifest
winget validate manifests/w/willibrandon/pgtail/0.1.0/

# Test in sandbox (requires Windows Sandbox feature)
.\Tools\SandboxTest.ps1 manifests/w/willibrandon/pgtail/0.1.0/
```

### Expected Validation Output

```
Manifest validation succeeded.
```

---

## Version Numbering

- Must use semantic versioning: `MAJOR.MINOR.PATCH`
- No `v` prefix in PackageVersion (use `0.1.0` not `v0.1.0`)
- Each version gets its own directory

---

## Token Requirements

For automated PR submission:

1. **Create GitHub Personal Access Token** with `public_repo` scope
2. **Store as secret** `WINGET_PKGS_TOKEN` in pgtail repository
3. **Token must have access** to fork `microsoft/winget-pkgs`

---

## Review Timeline

- **Automated validation**: ~10 minutes
- **Human review**: 1-7 days
- **PR merge**: After approval

If changes requested:
- 7-day window to respond
- PR auto-closed if no response
