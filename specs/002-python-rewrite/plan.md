# Implementation Plan: pgtail Python Rewrite

**Branch**: `002-python-rewrite` | **Date**: 2025-12-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-python-rewrite/spec.md`

## Summary

Rewrite pgtail from Go to Python using python-prompt-toolkit to resolve terminal color issues on Linux. The Python implementation will have 100% feature parity with the Go version while leveraging prompt_toolkit's superior terminal detection and color support across all platforms.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit, psutil, watchdog
**Storage**: File-based (command history in platform-appropriate location)
**Testing**: pytest
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single project
**Performance Goals**: <2s startup, <500ms log latency, <100ms autocomplete
**Constraints**: <50MB executable size, 80-column minimum terminal width
**Scale/Scope**: Single-user CLI tool, local PostgreSQL instances only

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Same command set as Go version; zero configuration required |
| II. Cross-Platform Parity | PASS | Using psutil/watchdog (cross-platform); platform code isolated |
| III. Graceful Degradation | PASS | Spec requires partial results and skip-on-failure behavior |
| IV. User-Friendly Feedback | PASS | Color-coded output, actionable errors specified |
| V. Focused Scope | PASS | Local-only, tail-only, detection-only as specified |
| VI. Minimal Dependencies | PASS | Only 3 dependencies (prompt_toolkit, psutil, watchdog) - all approved |
| VII. Developer Workflow Priority | PASS | pgrx detection prioritized, 10-second goal in success criteria |

**Technical Constraints Check**:
- Language: Python 3.10+ ✓
- Build Target: PyInstaller for single executable ✓
- Terminal Support: prompt_toolkit handles all major terminals ✓
- Minimum Width: 80 columns specified ✓

**Quality Standards Check**:
- Test Coverage: pytest for core logic ✓
- Error Handling: No unhandled exceptions ✓
- Documentation: Module docstrings required ✓
- Linting: ruff ✓
- Type Hints: Required for public functions ✓

## Project Structure

### Documentation (this feature)

```text
specs/002-python-rewrite/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py          # Package init with version
├── __main__.py          # Entry point (python -m pgtail_py)
├── cli.py               # REPL loop and command handlers
├── commands.py          # Command definitions and completers
├── detector.py          # PostgreSQL instance detection
├── detector_unix.py     # Unix-specific detection (macOS, Linux)
├── detector_windows.py  # Windows-specific detection
├── instance.py          # Instance dataclass
├── tailer.py            # Log file tailing with watchdog
├── parser.py            # PostgreSQL log line parsing
├── filter.py            # Log level filtering
├── colors.py            # Color output using prompt_toolkit styles
└── config.py            # History file paths, platform detection

tests/
├── __init__.py
├── test_detector.py     # Instance detection tests
├── test_parser.py       # Log parsing tests
├── test_filter.py       # Level filtering tests
├── test_tailer.py       # File watching tests
└── test_commands.py     # Command handling tests
```

**Structure Decision**: Single project layout using `pgtail_py/` as the Python package to avoid conflict with the existing Go `pgtail` directory. Tests in parallel `tests/` directory following pytest conventions.

## Complexity Tracking

No constitution violations to justify.
