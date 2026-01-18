# Implementation Plan: Windows Store Distribution

**Branch**: `024-windows-store` | **Date**: 2026-01-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/024-windows-store/spec.md`

## Summary

Add Microsoft Store distribution for pgtail to eliminate SmartScreen warnings, provide automatic updates, and enable free code signing. This requires:
1. Building MSIX packages for x64 and ARM64 architectures
2. Creating AppxManifest.xml with AppExecutionAlias for CLI invocation
3. Generating required logo assets from pgtail.ico
4. Automating Store submission via Partner Center API

## Technical Context

**Language/Version**: Python 3.12 (existing), PowerShell (workflow scripts), XML (manifest)
**Primary Dependencies**: Nuitka (existing build tool), Windows SDK (MakeAppx.exe), Partner Center API
**Storage**: N/A (build artifacts only)
**Testing**: GitHub Actions workflow verification, local MSIX install/uninstall testing
**Target Platform**: Windows 10 1809+ (build 17763), Windows 11, x64 and ARM64
**Project Type**: Single project with CI/CD workflow additions
**Performance Goals**: MSIX package size under 35MB each (x64 and ARM64)
**Constraints**: Workflow timeout under 30 minutes, 3 retries with exponential backoff for uploads
**Scale/Scope**: Single app, automated submissions on every release

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ Pass | No user configuration required; Store install is zero-config |
| II. Cross-Platform Parity | ✅ Pass | Feature is Windows-specific by nature; other platforms unaffected |
| III. Graceful Degradation | ✅ Pass | Workflow failures report clearly; Store submission doesn't block release |
| IV. User-Friendly Feedback | ✅ Pass | Store shows "Verified publisher"; no cryptic warnings |
| V. Focused Scope | ✅ Pass | Distribution method only; no new functionality in pgtail itself |
| VI. Minimal Dependencies | ✅ Pass | Uses Windows SDK tools already on runners; no new runtime dependencies |
| VII. Developer Workflow Priority | ✅ Pass | Eliminates SmartScreen friction for Windows developers |

**Quality Standards**:
- File Size Limit: N/A (workflow files, manifest, no Python source additions)
- Type Hints: N/A (no Python code changes)
- Linting: YAML workflow validated

## Project Structure

### Documentation (this feature)

```text
specs/024-windows-store/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
# Existing structure (unchanged)
pgtail_py/               # Python source (no changes)
tests/                   # Tests (no changes)

# New files for this feature
msix/
├── AppxManifest.xml     # Package manifest template
└── Assets/
    ├── StoreLogo.png         # 50x50
    ├── Square44x44Logo.png   # 44x44
    ├── Square150x150Logo.png # 150x150
    └── Wide310x150Logo.png   # 310x150

art/
└── pgtail.ico           # Existing (source for asset generation)

.github/workflows/
└── release.yml          # Extended with build-msix, update-store jobs
```

**Structure Decision**: Extend existing single-project structure with `msix/` directory for Store packaging assets and manifest. No changes to Python source structure.

## Complexity Tracking

No violations requiring justification. All additions are workflow-level (YAML) and packaging assets (XML, PNG).

## Files to Create/Modify

### New Files

| File | Purpose | LOC Estimate |
|------|---------|--------------|
| `msix/AppxManifest.xml` | MSIX package manifest with AppExecutionAlias | ~50 |
| `msix/Assets/StoreLogo.png` | 50x50 Store listing logo | Binary |
| `msix/Assets/Square44x44Logo.png` | 44x44 taskbar icon | Binary |
| `msix/Assets/Square150x150Logo.png` | 150x150 Start menu tile | Binary |
| `msix/Assets/Wide310x150Logo.png` | 310x150 wide tile | Binary |
| `specs/024-windows-store/research.md` | Research findings | ~150 |
| `specs/024-windows-store/data-model.md` | Entity documentation | ~80 |
| `specs/024-windows-store/quickstart.md` | Setup guide | ~100 |
| `specs/024-windows-store/contracts/partner-center-api.md` | API contract | ~120 |

### Modified Files

| File | Changes | LOC Delta |
|------|---------|-----------|
| `.github/workflows/release.yml` | Add build-windows-arm64, build-msix, update-store jobs | +300 |

## Implementation Phases

### Phase 1: Asset Generation
- Generate PNG assets from pgtail.ico at required sizes
- Create AppxManifest.xml template with placeholders

### Phase 2: ARM64 Build Support
- Add `build-windows-arm64` job to release.yml
- Configure Nuitka cross-compilation or ARM64 runner

### Phase 3: MSIX Package Build
- Add `build-msix` job that creates x64 and ARM64 MSIX packages
- Use MakeAppx.exe from Windows SDK
- Test AppExecutionAlias works for CLI invocation

### Phase 4: Store Submission Automation
- Add `update-store` job for Partner Center API
- Implement OAuth authentication with Azure AD
- Handle pending submission cleanup, upload, commit, status polling

### Phase 5: Documentation
- Document maintainer setup process
- Add troubleshooting guide for common certification issues
