# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python (pgtail_py)

```bash
uv run python -m pgtail_py                    # Run from source
uv run python -m pytest tests/ -v             # Run all tests
uv run ruff check pgtail_py/                  # Lint code
uv run ruff check --fix pgtail_py/            # Auto-fix lint issues
uv run pyinstaller --onefile --name pgtail pgtail_py/__main__.py  # Build executable
```

### Go (legacy)

```bash
make build          # Build for current platform
make test           # Run all tests
make lint           # Run golangci-lint
make run            # Build and run
```

## Architecture

pgtail is an interactive CLI tool for tailing PostgreSQL log files. It auto-detects PostgreSQL instances and provides real-time log streaming with level filtering.

### Python Package Structure (pgtail_py/)

- `pgtail_py/__main__.py` - Entry point for `python -m pgtail_py`
- `pgtail_py/cli.py` - REPL loop, command handlers, AppState
- `pgtail_py/detector.py` - Platform dispatcher for instance detection
- `pgtail_py/detector_unix.py` - Unix/macOS detection (processes, pgrx, PGDATA, known paths)
- `pgtail_py/detector_windows.py` - Windows-specific detection
- `pgtail_py/instance.py` - Instance dataclass and DetectionSource enum
- `pgtail_py/parser.py` - PostgreSQL log line parsing, LogEntry dataclass
- `pgtail_py/filter.py` - LogLevel enum, filtering logic
- `pgtail_py/tailer.py` - Log file tailing with polling (handles rotation)
- `pgtail_py/colors.py` - Color output using prompt_toolkit styles
- `pgtail_py/commands.py` - Command definitions, PgtailCompleter for autocomplete
- `pgtail_py/config.py` - Platform-specific paths (history file)
- `pgtail_py/enable_logging.py` - Enable logging_collector in postgresql.conf

### Go Package Structure (legacy)

- `cmd/pgtail/` - Entry point, REPL loop using go-prompt, command handlers
- `internal/detector/` - PostgreSQL instance detection
- `internal/instance/` - Instance type and DetectionSource enum
- `internal/tailer/` - Log file tailing, parsing, filtering, colorization
- `internal/repl/` - AppState for REPL session

**Detection priority:** Running processes → ~/.pgrx/data-* → PGDATA env → platform-specific paths

**Key Python dependencies:**
- `prompt_toolkit` - REPL with autocomplete and history
- `psutil` - Cross-platform process detection
- `watchdog` - (available but using polling for reliability)

**Key Go dependencies:**
- `go-prompt` - REPL with autocomplete and history
- `lipgloss` - Terminal colors (respects NO_COLOR)
- `fsnotify` - File watching with polling fallback
- `gopsutil` - Cross-platform process detection
