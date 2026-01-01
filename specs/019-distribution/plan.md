# Implementation Plan: pgtail Distribution

**Branch**: `019-distribution` | **Date**: 2026-01-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-distribution/spec.md`

## Summary

Cross-platform distribution for pgtail without PyPI dependency. Users install via pip/pipx/uv from GitHub, download pre-built binaries, or use package managers (Homebrew, winget). GitHub Actions releases binaries for 5 platforms on tag push. pgtail detects its installation method and shows appropriate upgrade commands when updates are available.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: PyInstaller (binary building), GitHub Actions, Homebrew (Ruby formula), winget (YAML manifest)
**Storage**: N/A (no persistence for distribution; update check uses config file already in place)
**Testing**: pytest (existing), manual testing of installation methods, GitHub Actions workflow testing
**Target Platform**: macOS arm64, macOS x86_64, Linux x86_64, Linux arm64, Windows x86_64
**Project Type**: single (CLI tool with existing structure)
**Performance Goals**: Installation < 60 seconds (pip), binary download < 30 seconds, startup update check < 500ms (non-blocking)
**Constraints**: Binary size < 50MB, release workflow < 15 minutes, update check API calls rate-limited
**Scale/Scope**: 5 binary platforms, 4 package manager methods (pip/pipx/uv/binary), 2 external repos (homebrew-tap, winget-pkgs PR)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Check (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Single command installation for each method; no configuration required |
| II. Cross-Platform Parity | PASS | All 5 platforms supported with identical feature set |
| III. Graceful Degradation | PASS | Update check fails silently if offline; installation methods independent |
| IV. User-Friendly Feedback | PASS | Clear upgrade commands per installation method; version display |
| V. Focused Scope | PASS | Distribution only; no new features beyond update checking |
| VI. Minimal Dependencies | PASS | PyInstaller dev-only; no runtime deps added for update check |
| VII. Developer Workflow Priority | PASS | pip/uv install from GitHub works immediately; no PyPI wait |

**Gate Status**: PASS - No violations requiring justification.

### Post-Design Check (Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Single `version.py` module handles all update logic; no complex abstractions |
| II. Cross-Platform Parity | PASS | InstallMethod enum covers all platforms; detection heuristics work everywhere |
| III. Graceful Degradation | PASS | All API failures return None; try/except wraps all network calls |
| IV. User-Friendly Feedback | PASS | Upgrade commands are method-specific; clear notification format |
| V. Focused Scope | PASS | Update checking is minimal; no analytics, no auto-update |
| VI. Minimal Dependencies | PASS | Uses stdlib urllib.request, importlib.metadata; no new runtime deps |
| VII. Developer Workflow Priority | PASS | 10-second goal maintained; update check is non-blocking background thread |

**Post-Design Gate Status**: PASS - Design adheres to all constitutional principles.

## Project Structure

### Documentation (this feature)

```text
specs/019-distribution/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
# Existing structure (no changes to layout)
pgtail_py/
├── __init__.py
├── __main__.py          # Entry point
├── cli_main.py          # CLI entry (pgtail command)
├── config.py            # Existing config support (update settings here)
├── version.py           # NEW: Version reading and update checking
└── ...                  # Existing modules unchanged

# GitHub Actions (new/modified)
.github/
└── workflows/
    ├── ci.yml           # Existing CI (unchanged)
    ├── docs.yml         # Existing docs (unchanged)
    └── release.yml      # NEW: Tag-triggered release workflow

# PyInstaller (existing, updated)
pgtail.spec              # Existing spec (platform-specific modifications)

# New external repositories (created separately)
# willibrandon/homebrew-tap/
#   └── Formula/
#       └── pgtail.rb    # Homebrew formula

# winget-pkgs PR (submitted to microsoft/winget-pkgs)
# manifests/w/willibrandon/pgtail/0.1.0/
#   ├── willibrandon.pgtail.yaml
#   ├── willibrandon.pgtail.installer.yaml
#   └── willibrandon.pgtail.locale.en-US.yaml
```

**Structure Decision**: Minimal additions to existing structure. New `version.py` module for update checking. New `release.yml` workflow. External repos for Homebrew tap and winget manifest.

## Complexity Tracking

No violations - no complexity justification needed.

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `pgtail_py/version.py` | Version reading, update checking, installation method detection |
| `.github/workflows/release.yml` | Multi-platform binary build and GitHub Release creation |
| `willibrandon/homebrew-tap/Formula/pgtail.rb` | Homebrew formula (external repo) |
| winget manifest files | winget package definition (PR to microsoft/winget-pkgs) |

### Modified Files

| File | Change |
|------|--------|
| `pgtail_py/cli_main.py` | Add `--version` and `--check-update` flags |
| `pgtail_py/config.py` | Add `updates.check` setting |
| `pyproject.toml` | Verify entry points and metadata for GitHub install |
| `README.md` | Document all installation methods |
| `pgtail.spec` | Update for cross-platform builds if needed |

## Implementation Phases

### Phase 0: Research (complete before Phase 1)

- PyInstaller cross-platform binary building best practices
- GitHub Actions matrix builds for macOS/Linux/Windows
- GitHub Releases API for update checking
- Installation method detection heuristics
- Homebrew formula structure and tap requirements
- winget manifest format and submission process

### Phase 1: Design (contracts, data model)

- Update check API contract (GitHub Releases API)
- Version configuration schema
- Installation method detection logic
- Homebrew formula structure
- winget manifest structure

### Phase 2: Tasks (generated by /speckit.tasks)

Tasks will cover:
1. pip/pipx/uv GitHub installation verification
2. GitHub Actions release workflow
3. Update checking implementation
4. Homebrew tap and formula creation
5. winget manifest creation and submission
6. README documentation updates
