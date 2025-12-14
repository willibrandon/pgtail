# Implementation Plan: pgtail CLI Tool

**Branch**: `001-pgtail-cli` | **Date**: 2025-12-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-pgtail-cli/spec.md`

## Summary

Build a cross-platform interactive CLI tool that auto-detects PostgreSQL instances and provides real-time log tailing with level filtering. The tool prioritizes zero-configuration for pgrx development workflows, with an interactive REPL featuring autocomplete, history, and color-coded output. Targets macOS, Linux, and Windows with identical behavior across platforms.

## Technical Context

**Language/Version**: Go 1.21+ (latest stable)
**Primary Dependencies**:
- `github.com/c-bata/go-prompt` v0.2.6 (REPL with autocomplete)
- `github.com/charmbracelet/lipgloss` v1.0.0 (terminal styling and colors)
- `github.com/fsnotify/fsnotify` v1.7.0 (file watching for Unix)
- `github.com/shirou/gopsutil/v3` v3.24.1 (cross-platform process info)

**Storage**: N/A (no persistence; reads PostgreSQL configs and logs only)
**Testing**: `go test` with table-driven tests; testify for assertions
**Target Platform**: macOS (ARM64/AMD64), Linux (AMD64), Windows (AMD64)
**Project Type**: Single CLI binary
**Performance Goals**: Log entries appear within 1 second; instance detection completes in <2 seconds
**Constraints**: Single static binary <20MB; 80-column terminal minimum; no runtime dependencies
**Scale/Scope**: Local machine only; typically 1-10 PostgreSQL instances

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Simplicity First | PASS | 9 commands total (list, tail, follow, refresh, levels, stop, clear, help, quit/exit); zero config for common cases |
| II. Cross-Platform Parity | PASS | All deps support macOS/Linux/Windows; platform code isolated in `process_unix.go`/`process_windows.go` |
| III. Graceful Degradation | PASS | FR-026 through FR-028 mandate continue-on-failure, skip-unreadable, never-crash behavior |
| IV. User-Friendly Feedback | PASS | FR-027 actionable errors; FR-020 state in prompt; FR-021 color coding |
| V. Focused Scope | PASS | Local only (no remote); tailing only (no aggregation); basic filtering only |
| VI. Minimal Dependencies | PASS | 4 approved dependencies only; all justified in constitution |
| VII. Developer Workflow Priority | PASS | SC-001 10-second goal; SC-005 100% pgrx detection; FR-002 pgrx paths |

**Gate Result**: PASS - All 7 principles satisfied. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-pgtail-cli/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contract, not API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
cmd/
└── pgtail/
    └── main.go              # Entry point, REPL initialization

internal/
├── detector/
│   ├── detector.go          # Main detection orchestration
│   ├── process.go           # Running process detection (shared)
│   ├── process_unix.go      # Unix-specific process scanning
│   ├── process_windows.go   # Windows-specific process scanning
│   ├── paths.go             # Known path scanning
│   └── config.go            # postgresql.conf parsing
├── instance/
│   └── instance.go          # PostgreSQL instance type and methods
├── tailer/
│   ├── tailer.go            # Log file tailing orchestration
│   ├── parser.go            # Log line parsing (extract level, timestamp)
│   └── filter.go            # Level filtering logic
└── repl/
    ├── repl.go              # REPL setup with go-prompt
    ├── executor.go          # Command dispatch and state management
    └── completer.go         # Autocomplete suggestions

tests/
├── unit/
│   ├── detector_test.go
│   ├── parser_test.go
│   └── filter_test.go
└── integration/
    └── cli_test.go          # End-to-end command tests

go.mod
go.sum
```

**Structure Decision**: Single project structure following Go conventions. The `cmd/` directory contains the entry point, `internal/` contains non-exported packages organized by domain (detector, instance, tailer, repl). Platform-specific code uses Go build tags in separate files.

## Complexity Tracking

> No violations requiring justification. All design decisions align with constitution principles.

| Aspect | Decision | Justification |
|--------|----------|---------------|
| Dependencies | 4 external packages | Each is constitution-approved; all provide cross-platform value |
| Platform code | Build tags | Standard Go pattern for platform isolation |
| REPL library | go-prompt | Constitution-approved; provides autocomplete/history without custom implementation |
