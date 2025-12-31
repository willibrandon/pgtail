# Implementation Plan: Status Bar Tail Mode

**Branch**: `016-status-bar-tail` | **Date**: 2025-12-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-status-bar-tail/spec.md`

## Summary

Replace the simple streaming tail command with a split-screen interface featuring scrollable log output, a status bar with live stats and filter state, and an always-visible command input line. Uses prompt_toolkit's Application and HSplit layout for three-pane TUI, with thread-safe log streaming from the existing LogTailer.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (Application, HSplit, Window, FormattedTextControl, BufferControl, TextArea)
**Storage**: In-memory ring buffer (10,000 lines max), no persistence
**Testing**: pytest with prompt_toolkit test utilities
**Target Platform**: macOS, Linux, Windows (cross-platform terminal)
**Project Type**: Single CLI application
**Performance Goals**: UI latency <50ms, status bar updates <100ms, 1000+ lines/sec throughput
**Constraints**: <50MB memory for 10,000 line buffer, responsive during high log volume
**Scale/Scope**: Single-user local CLI, single PostgreSQL instance at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| I. Simplicity First | Zero configuration, memorable commands | ✅ PASS | Reuses existing commands (`level`, `filter`, `since`, etc.); no new config required |
| II. Cross-Platform Parity | Works identically on macOS/Linux/Windows | ✅ PASS | prompt_toolkit is cross-platform; no new platform-specific code |
| III. Graceful Degradation | Never crash on failures | ✅ PASS | Small terminal warning; tailing continues if detection fails |
| IV. User-Friendly Feedback | Actionable errors, state visibility | ✅ PASS | Status bar shows all active filters; inline command feedback |
| V. Focused Scope | Local only, tailing only, no admin | ✅ PASS | Enhances existing tail command; no new scope expansion |
| VI. Minimal Dependencies | Justified additions only | ✅ PASS | No new dependencies; uses existing prompt_toolkit features |
| VII. Developer Workflow | 10-second goal, auto-detection | ✅ PASS | Faster filter iteration without pause/resume cycle |

**Gate Status**: ✅ All gates PASS - proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/016-status-bar-tail/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
pgtail_py/
├── tail_app.py          # NEW: TailApp main application coordinator
├── tail_buffer.py       # NEW: Ring buffer with scroll position management
├── tail_status.py       # NEW: Status bar state and formatting
├── tail_layout.py       # NEW: HSplit layout builder
├── cli_tail.py          # NEW: Tail mode command handlers (inline commands)
├── cli.py               # MODIFY: Entry point to launch tail mode
├── tailer.py            # EXISTING: Log streaming (minimal changes)
├── display.py           # EXISTING: FormattedText formatting
├── colors.py            # EXISTING: Style definitions
├── error_stats.py       # EXISTING: Error tracking
├── connection_stats.py  # EXISTING: Connection tracking
├── filter.py            # EXISTING: Level filtering
├── regex_filter.py      # EXISTING: Regex filtering
├── time_filter.py       # EXISTING: Time filtering
└── commands.py          # MODIFY: Add tail mode command completions

tests/
├── test_tail_buffer.py  # NEW: Ring buffer unit tests
├── test_tail_status.py  # NEW: Status bar formatting tests
├── test_tail_app.py     # NEW: Integration tests (mock tailer)
└── test_cli_tail.py     # NEW: Command handler tests
```

**Structure Decision**: Extends existing single-project structure in `pgtail_py/`. New modules prefixed with `tail_` for discoverability. Reuses existing filter, display, and stats modules without modification where possible.

## Complexity Tracking

> No constitution violations - all gates passed.

*N/A - no complexity justifications required.*

## Constitution Check (Post-Design)

*Re-evaluation after Phase 1 design completion.*

| Principle | Status | Post-Design Notes |
|-----------|--------|-------------------|
| I. Simplicity First | ✅ PASS | 5 new modules (`tail_*.py`) with clear responsibilities; no configuration changes |
| II. Cross-Platform Parity | ✅ PASS | All prompt_toolkit components used are cross-platform (HSplit, Window, Application) |
| III. Graceful Degradation | ✅ PASS | Small terminal warning; scroll bounds clamping; filter errors shown inline |
| IV. User-Friendly Feedback | ✅ PASS | Status bar provides constant visibility; PAUSED +N new shows missed entries |
| V. Focused Scope | ✅ PASS | Design stays within tailing scope; no new external features |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies confirmed; uses existing prompt_toolkit features only |
| VII. Developer Workflow | ✅ PASS | Eliminates pause/resume cycle; <100ms filter response |

**Post-Design Gate Status**: ✅ All gates PASS - ready for Phase 2 (/speckit.tasks)

## Artifacts Generated

| Artifact | Path | Description |
|----------|------|-------------|
| Research | [research.md](./research.md) | prompt_toolkit patterns, thread safety, scroll handling |
| Data Model | [data-model.md](./data-model.md) | Entity definitions, relationships, invariants |
| Contracts | [contracts/](./contracts/) | Python Protocol interfaces for all new modules |
| Quickstart | [quickstart.md](./quickstart.md) | Usage guide with demo and commands |

## Next Steps

Run `/speckit.tasks` to generate implementation tasks from this plan.
