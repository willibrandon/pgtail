# Data Model: Windows Store Distribution

**Feature**: 024-windows-store
**Date**: 2026-01-18

## Overview

This feature involves configuration files and API interactions rather than traditional data persistence. The "entities" are primarily build artifacts and external API objects.

## Build Artifacts

### MSIX Package

Container format for Windows Store distribution.

| Attribute | Type | Description |
|-----------|------|-------------|
| Identity.Name | string | Package identity from Partner Center (e.g., `12345Publisher.pgtail`) |
| Identity.Version | string | X.Y.Z.0 format (e.g., `0.5.0.0`) |
| Identity.Publisher | string | Publisher CN from Partner Center (e.g., `CN=12345678-ABCD-...`) |
| Identity.ProcessorArchitecture | enum | `x64` or `ARM64` |
| DisplayName | string | `pgtail` |
| Description | string | `Interactive PostgreSQL log tailer` |
| Logo | path | `Assets\StoreLogo.png` |

**Relationships**:
- Contains: AppxManifest.xml, Assets/, pgtail/ (application files)
- Submitted to: Partner Center via Store Submission

### AppxManifest.xml

XML configuration declaring package identity and capabilities.

| Element | Purpose |
|---------|---------|
| `<Identity>` | Package identity (name, version, publisher, arch) |
| `<Properties>` | Display name, description, logo |
| `<Dependencies>` | Target Windows version |
| `<Applications>` | Entry point and extensions |
| `<Capabilities>` | Required permissions |

**Key Extension**:
```xml
<uap5:AppExecutionAlias desktop4:Subsystem="console">
  <uap5:ExecutionAlias Alias="pgtail.exe" />
</uap5:AppExecutionAlias>
```

### Logo Assets

PNG images derived from pgtail.ico.

| Asset | Size | Purpose |
|-------|------|---------|
| StoreLogo.png | 50x50 | Store listing thumbnail |
| Square44x44Logo.png | 44x44 | Taskbar, App list |
| Square150x150Logo.png | 150x150 | Start menu tile |
| Wide310x150Logo.png | 310x150 | Wide Start menu tile |

## External API Objects

### Store Submission (Partner Center API)

Represents a version submission for Store certification.

| Field | Type | Description |
|-------|------|-------------|
| id | string | Submission identifier |
| status | enum | `PendingCommit`, `CommitStarted`, `PreProcessing`, `Certification`, `Release`, `Failed` |
| fileUploadUrl | string | SAS URL for Azure Blob Storage upload |
| applicationPackages | array | Package metadata |
| listings | object | Store listing content per language |

**State Transitions**:
```
PendingCommit → CommitStarted → PreProcessing → Certification → Release
                     ↓                              ↓
                   Failed                        Failed
```

### Azure AD Token

OAuth access token for Partner Center API.

| Field | Type | Description |
|-------|------|-------------|
| access_token | string | Bearer token for API calls |
| token_type | string | `Bearer` |
| expires_in | integer | Token validity in seconds |

## GitHub Secrets (Configuration)

Secrets required for automated submission.

| Secret | Source | Purpose |
|--------|--------|---------|
| STORE_CLIENT_ID | Azure AD | Application (client) ID |
| STORE_CLIENT_SECRET | Azure AD | Client secret value |
| STORE_TENANT_ID | Azure AD | Directory (tenant) ID |
| STORE_APP_ID | Partner Center | App ID from reservation |

## File Structure

```text
msix/
├── AppxManifest.xml          # Package manifest template
└── Assets/
    ├── StoreLogo.png         # 50x50
    ├── Square44x44Logo.png   # 44x44
    ├── Square150x150Logo.png # 150x150
    └── Wide310x150Logo.png   # 310x150

# Build output (not committed)
dist/
├── pgtail-windows-x86_64/    # Nuitka x64 output
├── pgtail-windows-arm64/     # Nuitka ARM64 output
├── msix-stage-x64/           # MSIX staging (x64)
├── msix-stage-arm64/         # MSIX staging (ARM64)
├── pgtail-x64.msix           # Built MSIX package (x64)
├── pgtail-arm64.msix         # Built MSIX package (ARM64)
├── pgtail.msixbundle         # Bundle containing both architectures
└── submission.zip            # Upload package for Store
```

## Validation Rules

### Version Format
- Input: Semantic version from tag (e.g., `v0.5.0`, `v0.5.0-rc1`)
- Output: MSIX version format `X.Y.Z.0`
- Rule: Strip `v` prefix and prerelease suffix, append `.0`

### Package Identity
- `Identity.Name` must match Partner Center reservation
- `Identity.Publisher` must match Partner Center publisher CN
- Mismatch causes certification failure

### Asset Requirements
- All assets must be PNG format
- Dimensions must match exactly (not scaled)
- Transparent background recommended
