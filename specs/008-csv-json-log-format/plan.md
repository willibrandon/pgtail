# Implementation Plan: CSV and JSON Log Format Support

**Branch**: `008-csv-json-log-format` | **Date**: 2025-12-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-csv-json-log-format/spec.md`

## Summary

Add support for PostgreSQL CSV (`csvlog`) and JSON (`jsonlog`) log formats with automatic format detection. This feature extends the existing text parser to handle structured log formats, provides richer field display (SQL state codes, application name, query text), field-based filtering, and JSON output mode for piping to external tools.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0, psutil >=5.9.0, tomlkit >=0.12.0, csv (stdlib), json (stdlib)
**Storage**: N/A (log file parsing only)
**Testing**: pytest >=7.0.0
**Target Platform**: macOS, Linux, Windows (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: <2x overhead vs text parsing, format detection <100ms
**Constraints**: Zero new external dependencies (use stdlib csv/json modules)
**Scale/Scope**: Single-user CLI tool, typical PostgreSQL log files (KB to GB)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Auto-detection requires zero configuration; `display` and `filter` commands follow existing patterns |
| II. Cross-Platform Parity | ✅ PASS | Uses stdlib csv/json modules which are cross-platform |
| III. Graceful Degradation | ✅ PASS | Malformed entries display with warning; fallback to raw display |
| IV. User-Friendly Feedback | ✅ PASS | Format detection message; color-coded output maintained |
| V. Focused Scope | ⚠️ REVIEW | Expands filtering beyond "Basic Filtering Only" - but field filtering is natural extension for structured formats |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies; csv/json are Python stdlib |
| VII. Developer Workflow Priority | ✅ PASS | Enhanced debugging info for pgrx developers |

**Scope Review (V. Focused Scope)**: The constitution states "Basic Filtering Only: Support log level filtering; no complex query languages or regex matching." However:
1. Regex filtering was already added (007-time-filter branch shows regex_filter.py exists)
2. Field filtering (`app=`, `db=`) is a simple equality match, not a query language
3. This capability is only available for structured formats where the data exists
4. The feature provides significant developer value without adding complexity

**Decision**: Proceed - field filtering is a natural extension that aligns with developer workflow priority.

## Project Structure

### Documentation (this feature)

```text
specs/008-csv-json-log-format/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
pgtail_py/
├── parser.py            # Extend: LogEntry dataclass, add format detection
├── parser_csv.py        # NEW: CSV log format parser
├── parser_json.py       # NEW: JSON log format parser
├── format_detector.py   # NEW: Format auto-detection logic
├── field_filter.py      # NEW: Field-based filtering (app=, db=, user=)
├── display.py           # NEW: Display mode control (compact/full/fields)
├── colors.py            # Extend: Support new display modes
├── tailer.py            # Extend: Format detection on file open, field filters
├── cli.py               # Extend: display, filter, output commands
├── commands.py          # Extend: New command definitions for autocomplete

tests/
├── test_parser_csv.py   # NEW: CSV parser tests
├── test_parser_json.py  # NEW: JSON parser tests
├── test_format_detector.py  # NEW: Format detection tests
├── test_field_filter.py # NEW: Field filter tests
├── test_display.py      # NEW: Display mode tests
```

**Structure Decision**: Single project structure (existing pattern). New modules follow existing naming convention (`parser_*.py` for format-specific parsers, `*_filter.py` for filter types).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Field filtering extends "Basic Filtering" | Structured formats contain field data; not exposing it wastes the primary value of csvlog/jsonlog | Basic level filtering alone doesn't leverage structured format benefits |

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design artifacts completed.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Simplicity First | ✅ PASS | Commands follow existing patterns (`display`, `filter`, `output`); no config required |
| II. Cross-Platform Parity | ✅ PASS | All new code uses stdlib csv/json; no platform-specific logic |
| III. Graceful Degradation | ✅ PASS | Malformed CSV/JSON falls back to raw display; text format unchanged |
| IV. User-Friendly Feedback | ✅ PASS | Format detection shown; field filter status in prompt; error messages guide users |
| V. Focused Scope | ✅ PASS | Field filtering is simple equality (not a query language); aligns with existing regex filter precedent |
| VI. Minimal Dependencies | ✅ PASS | Zero new dependencies added |
| VII. Developer Workflow Priority | ✅ PASS | Rich error info (sql_state, query, application) speeds debugging |

**All gates pass. Ready for task generation.**

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| Parser Contract | [contracts/parser.md](./contracts/parser.md) | ✅ Complete |
| Format Detector Contract | [contracts/format_detector.md](./contracts/format_detector.md) | ✅ Complete |
| Field Filter Contract | [contracts/field_filter.md](./contracts/field_filter.md) | ✅ Complete |
| Display Contract | [contracts/display.md](./contracts/display.md) | ✅ Complete |
| Commands Contract | [contracts/commands.md](./contracts/commands.md) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |

## Next Steps

Run `/speckit.tasks` to generate implementation tasks from this plan.
