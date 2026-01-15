# Implementation Plan: Semantic Log Highlighting

**Branch**: `023-semantic-highlighting` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-semantic-highlighting/spec.md`

## Summary

Implement a composable semantic highlighting system for PostgreSQL log output with 29 pattern-based highlighters. The system will automatically colorize timestamps, PIDs, SQLSTATE codes, durations, table names, LSNs, and 23 other pattern types using priority-ordered highlighters with overlap prevention. Existing SQL highlighting infrastructure (sql_highlighter.py, sql_tokenizer.py) will be migrated into the new unified system.

## Technical Context

**Language/Version**: Python 3.10+ (targeting Python 3.12 for builds)
**Primary Dependencies**: prompt_toolkit >=3.0.0, textual, pyahocorasick (NEW - for multi-keyword matching)
**Storage**: TOML configuration file (existing config.py infrastructure)
**Testing**: pytest >=7.0.0, pytest-cov >=4.0.0, pytest-asyncio >=1.0.0
**Target Platform**: macOS, Linux, Windows (cross-platform CLI)
**Project Type**: Single Python package (pgtail_py/)
**Performance Goals**: 10,000 lines/second highlighting throughput (FR-162)
**Constraints**: <100ms per log line, configurable max_length (default 10KB), graceful degradation without colors
**Scale/Scope**: 29 built-in highlighters across 10 categories, 12 commands, 6 theme updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Simplicity First | PASS | Highlighting is automatic/zero-config by default; commands are optional |
| II. Cross-Platform Parity | PASS | All highlighters use regex/pyahocorasick; platform-specific code isolated |
| III. Graceful Degradation | PASS | NO_COLOR support, missing theme keys fallback, depth limiting |
| IV. User-Friendly Feedback | PASS | Color-coded output enhances scanability; clear error messages |
| V. Focused Scope | PASS | Extends existing display functionality; no new primary features |
| VI. Minimal Dependencies | PASS | One new dependency (pyahocorasick) justified for Aho-Corasick algorithm |
| VII. Developer Workflow Priority | PASS | Pattern recognition accelerates log scanning during development |
| File Size Limit (900 LOC) | ATTENTION | New modules must be designed within 900 LOC limit |

**New Dependency Justification (pyahocorasick)**:
- FR-160 requires Aho-Corasick algorithm for efficient multi-keyword matching (lock types, backend names, error names, SQL keywords)
- pyahocorasick is BSD-3-Clause licensed, cross-platform (macOS/Linux/Windows), actively maintained
- Provides O(n+m) complexity vs O(n*k) for k patterns - critical for 29 highlighters processing 10K lines/sec
- Pre-built wheels eliminate build friction for PyInstaller/Nuitka distribution

## Project Structure

### Documentation (this feature)

```text
specs/023-semantic-highlighting/
├── plan.md              # This file
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Development guide
├── contracts/           # Phase 1: Internal API contracts
│   └── highlighter.md   # Highlighter protocol definition
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
pgtail_py/
├── highlighter.py          # NEW: Highlighter protocol, HighlighterChain compositor
├── highlighter_registry.py # NEW: Built-in highlighter registration, enable/disable
├── highlighters/           # NEW: 29 highlighter implementations (one module per category)
│   ├── __init__.py
│   ├── structural.py       # Timestamp, PID, Context labels
│   ├── diagnostic.py       # SQLSTATE, Error names
│   ├── performance.py      # Duration, Memory/size, Statistics
│   ├── objects.py          # Identifiers, Relations, Schema-qualified names
│   ├── wal.py              # LSN, WAL segments, Transaction IDs
│   ├── connection.py       # Connection info, IP addresses, Backend types
│   ├── sql.py              # Query params, SQL keywords/strings/numbers (migrated)
│   ├── lock.py             # Lock types, Lock wait info
│   ├── checkpoint.py       # Checkpoint stats, Recovery progress
│   └── misc.py             # Booleans, NULL, OIDs, Paths
├── highlighting_config.py  # NEW: HighlightingConfig, threshold management
├── cli_highlight.py        # NEW: highlight command handlers
├── theme.py                # MODIFIED: Add get_style() method, highlight style keys
├── themes/                 # MODIFIED: Add highlight colors to all 6 themes
├── config.py               # MODIFIED: Add highlighting.* settings
├── tail_rich.py            # MODIFIED: Integrate HighlighterChain
├── display.py              # MODIFIED: Integrate HighlighterChain
├── export.py               # MODIFIED: Strip/preserve highlighting markup
├── commands.py             # MODIFIED: Add highlight commands to completer
└── sql_highlighter.py      # REMOVED: Migrated to highlighters/sql.py
    sql_tokenizer.py        # REMOVED: Migrated to highlighters/sql.py
    sql_detector.py         # REMOVED: Integrated into HighlighterChain

tests/
├── test_highlighter.py            # NEW: Protocol, chain, overlap prevention
├── test_highlighter_registry.py   # NEW: Registration, enable/disable
├── test_highlighters_structural.py
├── test_highlighters_diagnostic.py
├── test_highlighters_performance.py
├── test_highlighters_objects.py
├── test_highlighters_wal.py
├── test_highlighters_connection.py
├── test_highlighters_sql.py       # Migrated from test_sql_highlighter.py
├── test_highlighters_lock.py
├── test_highlighters_checkpoint.py
├── test_highlighters_misc.py
├── test_highlighting_config.py    # NEW: Config validation, persistence
├── test_cli_highlight.py          # NEW: Command handlers
└── test_highlighting_integration.py # NEW: End-to-end tests
```

**Structure Decision**: Single project structure following existing pgtail_py/ package layout. New highlighters/ subdirectory for category modules. Test files follow 1:1 correspondence with source modules.

## Complexity Tracking

> No violations requiring justification

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Post-Design Constitution Re-Check

*Gate re-evaluation after Phase 1 design completion.*

| Principle | Status | Post-Design Evidence |
|-----------|--------|----------------------|
| I. Simplicity First | ✅ PASS | Zero-config default; 12 optional commands; automatic pattern detection |
| II. Cross-Platform Parity | ✅ PASS | pyahocorasick has pre-built wheels for all platforms; no platform-specific highlighter code |
| III. Graceful Degradation | ✅ PASS | OccupancyTracker prevents crashes; depth limiting for long lines; fallback styles |
| IV. User-Friendly Feedback | ✅ PASS | Clear error messages for invalid patterns; `highlight list` shows status |
| V. Focused Scope | ✅ PASS | Display enhancement only; no new core functionality; extends existing theme system |
| VI. Minimal Dependencies | ✅ PASS | Single new dependency (pyahocorasick) with clear Aho-Corasick justification |
| VII. Developer Workflow Priority | ✅ PASS | Instant pattern recognition; no delay; 10K lines/sec throughput |
| File Size Limit (900 LOC) | ✅ PASS | Module split: 10 category files (~200 LOC each), 2 core files (~300 LOC each) |

**Design Verification**:
- **data-model.md**: 7 entities defined with clear relationships
- **contracts/highlighter.md**: Protocol contract with base implementations
- **research.md**: All technology decisions documented with alternatives
- **quickstart.md**: Development guide with code examples

**All gates PASS. Ready for Phase 2 task generation.**
