# Implementation Plan: Export Logs and Pipe to External Commands

**Branch**: `006-export-pipe` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-export-pipe/spec.md`

## Summary

Add `export` and `pipe` commands to pgtail that write filtered log entries to files or stream them to external processes. Supports three output formats (text, json, csv), continuous export mode with `--follow`, and integrates with the existing filter state (levels, regex, time).

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit>=3.0.0, psutil>=5.9.0, tomlkit>=0.12.0 (existing)
**Storage**: Local filesystem for export files
**Testing**: pytest>=7.0.0 with pytest-cov>=4.0.0
**Target Platform**: macOS, Linux, Windows (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: Export 10,000+ entries without noticeable delay; stream output without buffering all in memory
**Constraints**: <100MB memory for large exports; must handle log rotation during continuous export
**Scale/Scope**: Single-user CLI tool; exports typically 1K-100K log entries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
|-----------|--------|-----------|
| I. Simplicity First | PASS | Commands follow existing patterns (`export file.log`, `pipe grep pattern`); no complex configuration needed |
| II. Cross-Platform Parity | PASS | Uses Python stdlib for file I/O and subprocess; pathlib for paths; no platform-specific code needed |
| III. Graceful Degradation | PASS | Handles errors (permission denied, disk full, command not found) with clear messages; partial exports report count |
| IV. User-Friendly Feedback | PASS | Shows export progress/count; clear error messages with suggestions |
| V. Focused Scope | PASS | Stays within tailing/filtering focus; explicitly excludes cloud upload, compression, scheduling |
| VI. Minimal Dependencies | PASS | Uses Python stdlib (json, csv, subprocess, pathlib); no new dependencies required |
| VII. Developer Workflow Priority | PASS | Enables quick extraction of filtered logs for bug reports and debugging |

**Gate Status: PASSED** - No constitution violations detected.

## Project Structure

### Documentation (this feature)

```text
specs/006-export-pipe/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI command signatures)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py
├── __main__.py          # Entry point
├── cli.py               # REPL loop, command handlers, AppState (MODIFY)
├── commands.py          # Command definitions, PgtailCompleter (MODIFY)
├── config.py            # Configuration file support
├── colors.py            # Color output styling
├── detector.py          # Platform dispatcher for instance detection
├── detector_unix.py     # Unix/macOS detection
├── detector_windows.py  # Windows-specific detection
├── enable_logging.py    # Enable logging_collector
├── filter.py            # LogLevel enum, level filtering
├── instance.py          # Instance dataclass
├── parser.py            # LogEntry dataclass, log parsing
├── regex_filter.py      # Regex pattern filtering
├── slow_query.py        # Slow query detection
├── tailer.py            # Log file tailing
├── terminal.py          # Terminal utilities
└── export.py            # NEW: Export formatting and file writing

tests/
├── __init__.py
├── test_detector.py
├── test_filter.py
├── test_parser.py
├── test_regex_filter.py
├── test_slow_query.py
└── test_export.py       # NEW: Export tests
```

**Structure Decision**: Single project structure. New export functionality will be implemented in a new `export.py` module to maintain separation of concerns, with command handlers added to `cli.py` following existing patterns.

## Complexity Tracking

No constitution violations requiring justification.
