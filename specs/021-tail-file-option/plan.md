# Implementation Plan: Tail Arbitrary Log Files

**Branch**: `021-tail-file-option` | **Date**: 2026-01-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/021-tail-file-option/spec.md`

## Summary

Add a `--file <path>` option to the `tail` command enabling users to tail arbitrary PostgreSQL log files at any path (e.g., pg_regress test logs at `tmp_check/log/postmaster.log`, archived logs, non-standard installations). The feature integrates with existing LogTailer infrastructure, reusing format auto-detection, filtering, and status bar display. When tailing arbitrary files, the status bar shows the filename unless PostgreSQL version/port can be detected from log content.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit, textual, typer, psutil
**Storage**: N/A (file system read-only)
**Testing**: pytest
**Target Platform**: macOS, Linux, Windows (cross-platform parity per constitution)
**Project Type**: single (CLI tool)
**Performance Goals**: File open within 1 second (per SC-001), same 10,000 entry buffer limit
**Constraints**: <200ms p95 for filter operations, graceful degradation on file errors
**Scale/Scope**: Single files (P1), multi-file/glob patterns (P3 stretch goals)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Gate (Phase 0)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Single `--file` flag extends existing command; no new concepts to learn |
| II. Cross-Platform Parity | ✅ PASS | Uses pathlib for paths, no platform-specific file handling |
| III. Graceful Degradation | ✅ PASS | Clear error messages for file not found, permission denied, etc. |
| IV. User-Friendly Feedback | ✅ PASS | Actionable errors, status bar shows file/instance info |
| V. Focused Scope | ✅ PASS | Local files only, tailing only, no new administration features |
| VI. Minimal Dependencies | ✅ PASS | No new dependencies; reuses existing LogTailer, parser, format detector |
| VII. Developer Workflow Priority | ✅ PASS | Primary use case is pg_regress logs for pgrx development |

### Post-Design Re-evaluation (Phase 1)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | ✅ PASS | Design adds ~200 LOC to existing files, no new abstractions |
| II. Cross-Platform Parity | ✅ PASS | pathlib.Path.resolve() tested on all platforms |
| III. Graceful Degradation | ✅ PASS | All error paths return to prompt cleanly; file deletion waits gracefully |
| IV. User-Friendly Feedback | ✅ PASS | Status bar shows filename or detected PG version; error messages include paths |
| V. Focused Scope | ✅ PASS | P3 stretch goals (glob, multi-file, stdin) deferred to separate tasks |
| VI. Minimal Dependencies | ✅ PASS | Zero new dependencies; all functionality from stdlib + existing deps |
| VII. Developer Workflow Priority | ✅ PASS | pg_regress use case explicitly validated in spec and quickstart |

**Quality Standards Check**:
- ✅ File Size Limit: No file exceeds 900 LOC (largest addition ~60 LOC to cli_core.py at ~443 current)
- ✅ Test Coverage: Unit and integration tests planned for all new code paths
- ✅ Type Hints: All new functions will have type annotations
- ✅ Docstrings: All new public functions will have docstrings

## Project Structure

### Documentation (this feature)

```text
specs/021-tail-file-option/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contracts)
│   └── cli-tail-file.md
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
pgtail_py/
├── cli_main.py          # MODIFY: Add --file option to tail command (Typer CLI)
├── cli_core.py          # MODIFY: Add file path handling to tail_command() (REPL)
├── cli.py               # MODIFY: Update AppState for file-based tailing
├── instance.py          # EXTEND: Support file-only tailing without Instance
├── tailer.py            # No changes needed (already supports arbitrary paths)
├── tail_textual.py      # MODIFY: Support file-only mode (no Instance required)
├── tail_status.py       # MODIFY: Support filename display when no instance
├── commands.py          # MODIFY: Add --file completion to tail command
└── detector.py          # No changes needed

tests/
├── unit/
│   └── test_tail_file.py    # NEW: Unit tests for file path handling
└── integration/
    └── test_tail_file_e2e.py  # NEW: End-to-end tests with real files
```

**Structure Decision**: Single project layout with existing `pgtail_py/` source directory and `tests/` test directory. No new directories required; modifications to existing files plus 2 new test files.

## Complexity Tracking

> No constitution violations requiring justification.

## Files to Create/Modify

### Modified Files

| File | Changes | LOC Est. |
|------|---------|----------|
| `pgtail_py/cli_main.py` | Add `--file` option to `tail` command, path validation, mutual exclusivity with instance ID | +50 |
| `pgtail_py/cli_core.py` | Add `--file` parsing in REPL `tail_command()`, path resolution, error handling | +60 |
| `pgtail_py/instance.py` | Add optional `file_only` factory method or adjust Instance for file-only use | +20 |
| `pgtail_py/tail_textual.py` | Support `None` instance for file-only mode, adjust callbacks | +30 |
| `pgtail_py/tail_status.py` | Add `set_file_source()` method, filename display in status bar | +25 |
| `pgtail_py/commands.py` | Add `--file` to tail command completions | +10 |
| `pgtail_py/cli.py` | Add `file_path` to prompt state tracking (optional) | +5 |

### New Files

| File | Purpose | LOC Est. |
|------|---------|----------|
| `tests/unit/test_tail_file.py` | Unit tests for path validation, resolution, error handling | ~150 |
| `tests/integration/test_tail_file_e2e.py` | End-to-end tests with temp log files | ~100 |

**Total Estimated LOC**: ~450 (well under 900 LOC limit per file)

## Key Design Decisions

### 1. File-Only Mode vs Pseudo-Instance

**Decision**: Create a lightweight "file-only" mode rather than synthesizing a fake Instance.

**Rationale**:
- Instance has fields like `data_dir`, `pid`, `running` that don't apply to arbitrary files
- Cleaner separation of concerns
- Status bar already has `format_plain()` / `format_rich()` methods that can conditionally show filename vs instance info

### 2. Path Resolution

**Decision**: Resolve relative paths to absolute immediately on command entry.

**Rationale**:
- Consistent internal handling (FR-011)
- Avoids issues if working directory changes during session
- Simplifies log rotation detection

### 3. Instance Info Detection from Log Content

**Decision**: Parse first few log lines to detect PostgreSQL version and port from startup messages.

**Rationale**:
- FR-006 requires: "if PostgreSQL version/port can be detected from log content, display standard instance format"
- PostgreSQL logs startup messages like: `LOG:  listening on IPv4 address "0.0.0.0", port 5432`
- Version info in: `LOG:  database system is ready to accept connections` or banner

### 4. Mutual Exclusivity

**Decision**: `--file` and instance ID are mutually exclusive; show error if both provided.

**Rationale**:
- FR-010 explicitly requires this
- Clear user intent - either tail a known instance or an arbitrary file

### 5. Status Bar Format

**Decision**: When tailing arbitrary files:
- Default: Show filename only (e.g., `postmaster.log`)
- If version/port detected from log content: Show standard format (e.g., `PG17:5432`)

**Rationale**: Matches clarification session outcome and FR-006.

## Build Sequence

> **Note**: The detailed implementation sequence in `tasks.md` supersedes this high-level build sequence. Tasks are organized by user story for independent implementation and testing, with phases: Setup → Foundational → US3 (CLI) → US4 (REPL) → US1 (Filters) → US2 (Archived) → Polish.

1. **Phase 1**: CLI argument parsing (`cli_main.py`, `cli_core.py`)
   - Add `--file` option with path validation
   - Error for mutual exclusivity with instance ID
   - Path resolution (relative → absolute)

2. **Phase 2**: Status bar updates (`tail_status.py`)
   - Add `filename` attribute
   - Modify `format_rich()` to show filename when no instance

3. **Phase 3**: Instance info detection (`tail_textual.py`)
   - Parse log content for version/port during first few lines
   - Update status bar if detected

4. **Phase 4**: Textual integration (`tail_textual.py`)
   - Support file-only mode (instance=None or file_path != None)
   - All filters work identically

5. **Phase 5**: Completions (`commands.py`)
   - Add `--file` to tail command completions

6. **Phase 6**: Tests
   - Unit tests for path handling
   - Integration tests with temp log files

## Edge Case Handling

| Edge Case | Implementation |
|-----------|----------------|
| File not found | Error: "File not found: <path>" - return to prompt |
| Permission denied | Error: "Permission denied: <path>" - return to prompt |
| Path is directory | Error: "Not a file: <path> (is a directory)" - return to prompt |
| File deleted while tailing | Notification, wait indefinitely for recreation |
| File truncated | Existing rotation handling applies |
| Path with `..` segments | `Path.resolve()` handles normalization |
| Paths with spaces | Quote handling in shell; pathlib handles internally |
| `--file` + instance ID | Error: "Cannot specify both --file and instance ID" |
| Empty file | Enter tail mode normally, wait for content |
| No valid log entries | Text format fallback, display as UNKNOWN level |
| Symlinks | `Path.resolve()` follows symlinks |

## Stretch Goals (P3) - NOT in initial implementation

- FR-014: Glob patterns (`--file "*.log"`)
- FR-015: Multiple `--file` arguments
- FR-016: `--stdin` for pipe input
- FR-017/18/19: Multi-file interleaving with source indicators

These are documented in spec but will be separate tasks in Phase 2.
