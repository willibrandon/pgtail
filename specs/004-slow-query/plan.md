# Implementation Plan: Slow Query Detection and Highlighting

**Branch**: `004-slow-query` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-slow-query/spec.md`

## Summary

Add slow query detection and visual highlighting to pgtail based on configurable duration thresholds. Parse query duration from PostgreSQL log entries and apply progressive coloring (yellow → orange → red/bold) based on severity. Include session-scoped statistics command for duration distribution analysis.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (REPL/colors), psutil >=5.9.0 (process detection)
**Storage**: N/A (session-scoped in-memory only)
**Testing**: pytest with pytest-cov
**Target Platform**: macOS, Linux, Windows
**Project Type**: Single CLI application
**Performance Goals**: Statistics calculation <500ms for 10,000+ queries, real-time highlighting with no perceptible latency
**Constraints**: No external dependencies beyond existing (prompt_toolkit, psutil), memory-efficient stats collection
**Scale/Scope**: Session-scoped statistics (unlimited duration collection during single pgtail session)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Two simple commands (`slow`, `stats`), default thresholds work out-of-box |
| II. Cross-Platform Parity | ✅ PASS | No platform-specific code required, uses existing prompt_toolkit styles |
| III. Graceful Degradation | ✅ PASS | Malformed durations ignored, highlighting continues with other log entries |
| IV. User-Friendly Feedback | ✅ PASS | Clear threshold confirmation, color-coded output, percentile breakdown |
| V. Focused Scope | ✅ PASS | Extends existing log viewing capability, no new domains introduced |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies required, uses stdlib for percentile calculations |
| VII. Developer Workflow Priority | ✅ PASS | Helps identify slow queries during extension development |

**Gate Result**: PASS - All principles satisfied. No complexity tracking required.

## Project Structure

### Documentation (this feature)

```text
specs/004-slow-query/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI command interface)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── __init__.py
├── __main__.py
├── cli.py               # MODIFY: Add slow_command, stats_command handlers
├── colors.py            # MODIFY: Add slow query styles (warning/slow/critical)
├── commands.py          # MODIFY: Add 'slow' and 'stats' to COMMANDS dict
├── parser.py            # MODIFY: Extract duration from LogEntry
├── slow_query.py        # NEW: SlowQueryConfig, DurationStats, duration parsing
├── tailer.py            # MODIFY: Pass slow query config to filtering/display
├── filter.py            # (no changes)
├── regex_filter.py      # (no changes)
└── ...

tests/
├── test_slow_query.py   # NEW: Unit tests for duration parsing, stats, thresholds
└── ...
```

**Structure Decision**: Single project structure. New `slow_query.py` module isolates slow query logic following existing patterns (e.g., `regex_filter.py` for regex filtering).
