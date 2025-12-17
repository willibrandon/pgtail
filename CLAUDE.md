# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
make run      # Run from source
make test     # Run all tests
make lint     # Lint code
make format   # Format code
make build    # Build single executable
make clean    # Remove build artifacts
```

## Architecture

pgtail is an interactive CLI tool for tailing PostgreSQL log files. It auto-detects PostgreSQL instances and provides real-time log streaming with level filtering.

### Package Structure (pgtail_py/)

- `pgtail_py/__main__.py` - Entry point for `python -m pgtail_py`
- `pgtail_py/cli.py` - REPL loop, command handlers, AppState
- `pgtail_py/detector.py` - Platform dispatcher for instance detection
- `pgtail_py/detector_unix.py` - Unix/macOS detection (processes, pgrx, PGDATA, known paths)
- `pgtail_py/detector_windows.py` - Windows-specific detection
- `pgtail_py/instance.py` - Instance dataclass and DetectionSource enum
- `pgtail_py/parser.py` - PostgreSQL log line parsing, LogEntry dataclass
- `pgtail_py/filter.py` - LogLevel enum, level filtering logic
- `pgtail_py/regex_filter.py` - Regex pattern filtering and highlighting
- `pgtail_py/time_filter.py` - Time-based filtering (since, until, between)
- `pgtail_py/slow_query.py` - Slow query detection, thresholds, duration stats
- `pgtail_py/tailer.py` - Log file tailing with polling (handles rotation)
- `pgtail_py/colors.py` - Color output using prompt_toolkit styles
- `pgtail_py/commands.py` - Command definitions, PgtailCompleter for autocomplete
- `pgtail_py/config.py` - Configuration file support, platform-specific paths, config schema
- `pgtail_py/enable_logging.py` - Enable logging_collector in postgresql.conf
- `pgtail_py/export.py` - Export formatting, file writing, pipe to external commands

**Detection priority:** Running processes → ~/.pgrx/data-* → PGDATA env → platform-specific paths

**Key dependencies:**
- `prompt_toolkit` - REPL with autocomplete and history
- `psutil` - Cross-platform process detection

## Tech Stack

- Python 3.10+
- prompt_toolkit >=3.0.0 (REPL, autocomplete, styled output)
- psutil >=5.9.0 (process detection)
- re (stdlib, regex filtering)

## Configuration

Settings persist in a TOML config file at platform-specific locations:
- **macOS**: `~/Library/Application Support/pgtail/config.toml`
- **Linux**: `~/.config/pgtail/config.toml` (XDG_CONFIG_HOME)
- **Windows**: `%APPDATA%/pgtail/config.toml`

**Config commands:**
- `set <key> [value]` - Set a config value (e.g., `set slow.warn 50`)
- `unset <key>` - Remove a setting, revert to default
- `config` - Show current configuration as TOML
- `config path` - Show config file location
- `config edit` - Open in $EDITOR
- `config reset` - Reset to defaults (creates backup)

**Available settings:**
- `default.levels` - Default log level filter (e.g., `["ERROR", "WARNING"]`)
- `default.follow` - Auto-follow new entries (bool)
- `slow.warn`, `slow.error`, `slow.critical` - Threshold values in ms
- `display.timestamp_format` - strftime format string
- `display.show_pid`, `display.show_level` - Toggle output fields
- `theme.name` - Color theme (`dark` or `light`)
- `notifications.enabled`, `notifications.levels`, `notifications.quiet_hours`

## Time Filtering

Time-based filtering commands support multiple formats:
- **Relative**: `5m`, `30s`, `2h`, `1d` (duration from now)
- **Time only**: `14:30`, `14:30:45` (today at specified time)
- **ISO 8601**: `2024-01-15T14:30`, `2024-01-15T14:30:00Z`

Commands:
- `since <time>` - Show entries from time onward
- `until <time>` - Show entries up to time
- `between <start> <end>` - Show entries in time range
- `tail <id> --since <time>` - Start tailing with time filter

Filter order (cheapest first): time → level → regex

## Recent Changes
- 007-time-filter: Added `since`, `until`, `between` commands and `tail --since` flag for time-based log filtering
- 006-export-pipe: Added `export` and `pipe` commands for saving logs to files and streaming to external tools
- 005-config-file: Added persistent configuration file support with `set`, `unset`, and `config` commands

## Active Technologies
- Python 3.10+ + prompt_toolkit >=3.0.0, psutil >=5.9.0, re (stdlib), datetime (stdlib)
