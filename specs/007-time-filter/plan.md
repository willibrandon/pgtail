# Implementation Plan: Time-Based Filtering

**Branch**: `007-time-filter` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-time-filter/spec.md`

## Summary

Add time-based filtering commands (`since`, `until`, `between`) to pgtail, enabling developers to filter PostgreSQL log entries by time range. Supports relative times (5m, 2h, 1d), absolute times (14:30, 14:30:45), and ISO 8601 timestamps. Extends the existing filter architecture with a new TimeFilter component that integrates with level and regex filters.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, re (stdlib), datetime (stdlib)
**Storage**: N/A (local log file reading only)
**Testing**: pytest
**Target Platform**: macOS, Linux, Windows (cross-platform parity required)
**Project Type**: Single CLI application
**Performance Goals**: Sub-second response for typical log files (<100MB); time-filtered viewing should not noticeably delay initial display
**Constraints**: Must work with standard PostgreSQL log formats; timestamps parsed by existing parser.py
**Scale/Scope**: Local log files, typically 1KB-100MB; no remote or aggregated logs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Commands are intuitive (`since 5m`, `between 14:30 15:00`); no configuration required |
| II. Cross-Platform Parity | PASS | Uses Python stdlib datetime; no platform-specific code needed |
| III. Graceful Degradation | PASS | Entries without timestamps are skipped gracefully; spec requires clear feedback |
| IV. User-Friendly Feedback | PASS | Spec requires clear time range display and helpful error messages |
| V. Focused Scope | PASS | Time filtering is a core log viewing feature, not scope creep |
| VI. Minimal Dependencies | PASS | Uses only stdlib (datetime, re); no new dependencies |
| VII. Developer Workflow Priority | PASS | Directly supports "what happened in the last 5 minutes?" investigation |

**Gate Result**: PASS - No violations. Proceed with implementation.

## Project Structure

### Documentation (this feature)

```text
specs/007-time-filter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py          # Package init
├── __main__.py          # Entry point
├── cli.py               # REPL loop, command handlers, AppState (MODIFY)
├── commands.py          # Command definitions, PgtailCompleter (MODIFY)
├── config.py            # Configuration schema
├── colors.py            # Color output styles
├── detector.py          # PostgreSQL instance detection
├── detector_unix.py     # Unix-specific detection
├── detector_windows.py  # Windows-specific detection
├── enable_logging.py    # Enable logging_collector
├── export.py            # Export/pipe functionality (contains parse_since)
├── filter.py            # LogLevel enum, level filtering
├── instance.py          # Instance dataclass
├── parser.py            # Log line parsing, LogEntry dataclass
├── regex_filter.py      # Regex pattern filtering
├── slow_query.py        # Slow query detection
├── tailer.py            # Log file tailing (MODIFY)
├── terminal.py          # Terminal utilities
└── time_filter.py       # NEW: Time parsing and filtering module

tests/
├── test_detector.py
├── test_filter.py
├── test_parser.py
├── test_regex_filter.py
├── test_slow_query.py
└── test_time_filter.py  # NEW: Time filter tests
```

**Structure Decision**: Single project structure. New `time_filter.py` module contains time parsing and TimeFilter class. Modifications to cli.py (AppState, command handlers), commands.py (completions), and tailer.py (time filter support).

## Complexity Tracking

No violations to justify - design follows existing patterns.
