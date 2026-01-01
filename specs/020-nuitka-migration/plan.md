# Implementation Plan: Nuitka Migration for Binary Distribution

**Branch**: `020-nuitka-migration` | **Date**: 2026-01-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-nuitka-migration/spec.md`

## Summary

Migrate pgtail's binary distribution from PyInstaller to Nuitka to eliminate the 4.5-second cold start penalty. PyInstaller `--onefile` extracts a compressed archive on every execution, adding significant startup overhead. Nuitka compiles Python to C, producing native executables with near-instant startup (<1 second). The migration uses `--mode=standalone` (folder-based distribution) to avoid Nuitka's onefile extraction overhead.

## Technical Context

**Language/Version**: Python 3.10+ (targeting Python 3.12 for builds)
**Primary Dependencies**:
- Nuitka >= 2.5 (Python-to-C compiler, pinned to stable 2.x series)
- WiX Toolset 5.x (MSI installer builder for Windows, installed via `dotnet tool install`)
- prompt_toolkit >= 3.0.0 (REPL with autocomplete)
- textual >= 0.89.0 (TUI framework for tail mode)
- psutil >= 5.9.0 (native extension for process detection)
- typer >= 0.9.0 (CLI framework using docstrings for help)
- certifi >= 2023.0.0 (CA bundle for HTTPS)

**Storage**: N/A (no persistence for this feature; config file already in place)
**Testing**: pytest with pytest-asyncio (existing test suite)
**Target Platform**: 5 platforms - macOS ARM64, macOS x86_64, Linux x86_64, Linux ARM64, Windows x86_64
**Project Type**: Single CLI application
**Performance Goals**: Binary startup time < 1 second (down from 5.1 seconds)
**Constraints**: Binary size < 50 MB per platform; CI workflow time < 30 minutes
**Scale/Scope**: 64 source modules (~20,000 LOC); 99.5% pure Python with 1 native extension (psutil)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Justification |
|-----------|-------------|--------|---------------|
| I. Simplicity First | Zero configuration, memorable commands | **PASS** | Migration changes build process, not user experience |
| II. Cross-Platform Parity | Identical behavior on macOS/Linux/Windows | **PASS** | All 5 platforms build and function identically |
| III. Graceful Degradation | Never crash on failures | **PASS** | Version fallback handles missing metadata gracefully |
| IV. User-Friendly Feedback | Actionable error messages | **PASS** | Clear errors for missing dependencies, SSL failures |
| V. Focused Scope | Local only, tailing only | **PASS** | No scope expansion - only distribution changes |
| VI. Minimal Dependencies | Justified additions only | **PASS** | Nuitka is build-time only, not runtime; WiX is Windows CI only |
| VII. Developer Workflow Priority | 10-second goal | **PASS** | Startup improvement directly supports this goal |
| Technical Constraints | Python 3.10+, single executable | **PASS** | Python 3.10+ maintained; executable now in folder |
| Quality Standards | Tests, linting, type hints, <900 LOC | **PASS** | No source file changes required |

**Constitution Gate**: PASSED - No violations.

## Project Structure

### Documentation (this feature)

```text
specs/020-nuitka-migration/
├── plan.md              # This file
├── research.md          # Phase 0: Nuitka flags, WiX patterns, winget format
├── data-model.md        # Phase 1: Build artifact structure
├── quickstart.md        # Phase 1: Local build verification steps
├── contracts/           # Phase 1: CI workflow structure
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
# Existing structure (no changes to source layout)
pgtail_py/
├── __init__.py          # Add __version__ = "0.2.0" fallback
├── version.py           # Update get_version() to use fallback
├── cli_main.py          # Entry point (unchanged)
└── ... (64 modules)

# Build artifacts and scripts
scripts/
└── build-nuitka.sh      # New: Nuitka build helper script

.github/workflows/
└── release.yml          # Update: PyInstaller → Nuitka

# Makefile targets updated (build, build-test, clean)
Makefile

# Package manager integration
# homebrew-tap (external repo): Formula/pgtail.rb updated for archive distribution
# winget-pkgs (external repo): manifests/w/willibrandon/pgtail/ (new MSI-based manifest)
```

**Structure Decision**: Single project structure maintained. Build output changes from single executable to folder distribution packaged as tar.gz/zip/MSI.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
