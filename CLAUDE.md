# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make build          # Build for current platform
make test           # Run all tests
make lint           # Run golangci-lint
make run            # Build and run
go test -v ./internal/tailer/...  # Run tests for a specific package
go test -run TestFilter ./internal/tailer/...  # Run a specific test
```

## Architecture

pgtail is an interactive CLI tool for tailing PostgreSQL log files. It auto-detects PostgreSQL instances and provides real-time log streaming with level filtering.

**Package structure:**
- `cmd/pgtail/` - Entry point, REPL loop using go-prompt, command handlers
- `internal/detector/` - PostgreSQL instance detection (processes, pgrx paths, PGDATA, known paths)
- `internal/instance/` - Instance type and DetectionSource enum
- `internal/tailer/` - Log file tailing (fsnotify + polling fallback), parsing, filtering, colorization
- `internal/repl/` - AppState for REPL session

**Detection priority:** Running processes → ~/.pgrx/data-* → PGDATA env → platform-specific paths

**Platform-specific code:** `process_unix.go` and `process_windows.go` use build tags for platform isolation.

**Key dependencies:**
- `go-prompt` - REPL with autocomplete and history
- `lipgloss` - Terminal colors (respects NO_COLOR)
- `fsnotify` - File watching with polling fallback
- `gopsutil` - Cross-platform process detection
