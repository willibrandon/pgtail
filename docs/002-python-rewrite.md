# pgtail Python Rewrite

Rewrite pgtail from Go to Python using python-prompt-toolkit for the interactive REPL.

## Motivation

The Go implementation using go-prompt has terminal color issues on Linux. python-prompt-toolkit has better terminal detection and color support across platforms.

## Requirements

- Identical functionality to the Go version
- Use python-prompt-toolkit for REPL with autocomplete and history
- Cross-platform: macOS, Linux, Windows
- Auto-detect PostgreSQL instances (running processes, pgrx paths, PGDATA, known paths)
- Real-time log tailing with file watching
- Log level filtering (PANIC, FATAL, ERROR, WARNING, NOTICE, LOG, INFO, DEBUG1-5)
- Color-coded output by severity
- Persistent command history

## Commands

Same as Go version:
- `list` - Show detected PostgreSQL instances
- `tail <id|path>` - Tail logs for an instance
- `levels [LEVEL...]` - Set log level filter
- `enable-logging <id>` - Enable logging_collector for an instance
- `refresh` - Re-scan for instances
- `stop` - Stop current tail
- `clear` - Clear screen
- `help` - Show help
- `quit` / `exit` - Exit

## Dependencies

- python-prompt-toolkit - REPL with autocomplete/history
- psutil - Cross-platform process detection
- watchdog - File system monitoring

## Structure

```
pgtail/
├── __main__.py      # Entry point
├── cli.py           # REPL and command handlers
├── detector.py      # PostgreSQL instance detection
├── instance.py      # Instance data class
├── tailer.py        # Log file tailing
├── parser.py        # Log line parsing
├── filter.py        # Log level filtering
└── colors.py        # Color output
```

## Distribution

Single executable via PyInstaller or similar.
