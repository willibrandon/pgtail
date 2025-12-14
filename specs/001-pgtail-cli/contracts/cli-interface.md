# CLI Interface Contract: pgtail

**Date**: 2025-12-14
**Branch**: `001-pgtail-cli`

## Overview

This document defines the command-line interface contract for pgtail. Since pgtail is an interactive CLI tool (not an API), this contract specifies command syntax, output formats, and expected behaviors.

## Invocation

```bash
pgtail [flags]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--help`, `-h` | bool | false | Show help and exit |
| `--version`, `-v` | bool | false | Show version and exit |

**No flags required for normal operation**—pgtail launches directly into the interactive REPL.

## REPL Commands

### list

**Syntax**: `list`

**Description**: Display all detected PostgreSQL instances.

**Output Format**:
```
  #  VERSION  PORT   STATUS   SOURCE  DATA DIRECTORY
  0  16.1     5432   running  pgrx    ~/.pgrx/data-16
  1  15.4     5433   running  pgrx    ~/.pgrx/data-15
  2  14.9     5434   stopped  brew    /opt/homebrew/var/postgresql@14
```

**Columns**:
| Column | Width | Alignment | Description |
|--------|-------|-----------|-------------|
| # | 3 | Right | Zero-based index |
| VERSION | 8 | Left | PostgreSQL version |
| PORT | 6 | Right | Listening port or "-" |
| STATUS | 8 | Left | "running" or "stopped" |
| SOURCE | 8 | Left | Detection source |
| DATA DIRECTORY | Variable | Left | Path (~ expanded on display) |

**Edge Cases**:
- No instances found: Display helpful message with suggestions
- Detection errors: Show partial results with warnings

---

### tail

**Syntax**: `tail <identifier>`

**Aliases**: `follow`

**Arguments**:
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| identifier | string/int | Yes | Instance index (0-N) or path substring |

**Description**: Begin tailing logs for the specified instance.

**Output**:
```
[Following: ~/.pgrx/data-16/log/postgresql-2024-01-15.log]
[Press Ctrl+C to stop]

2024-01-15 10:23:45.123 PST [12345] LOG:  statement: SELECT 1
2024-01-15 10:23:45.456 PST [12345] ERROR:  relation "foo" does not exist
```

**Behavior**:
- Streams new log entries in real-time
- Applies current filter (if any)
- Color-codes by log level
- Ctrl+C stops tailing and returns to prompt

**Error Cases**:
| Condition | Message |
|-----------|---------|
| Invalid index | `Error: No instance with index N. Run 'list' to see available instances.` |
| No match for path | `Error: No PostgreSQL instance found matching 'X'. Did you mean: Y?` |
| No log file | `Error: No log files found for instance. Check log_destination in postgresql.conf.` |
| Permission denied | `Error: Cannot read log file: permission denied. Try running with elevated privileges.` |

---

### levels

**Syntax**: `levels [LEVEL...]`

**Arguments**:
| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| LEVEL | string | No | One or more log levels to filter |

**Valid Levels**: `DEBUG5`, `DEBUG4`, `DEBUG3`, `DEBUG2`, `DEBUG1`, `INFO`, `NOTICE`, `WARNING`, `ERROR`, `LOG`, `FATAL`, `PANIC`

**Behavior**:
- With arguments: Set filter to show only specified levels
- Without arguments: Clear filter (show all levels)

**Output**:
```
# With arguments
[Filter set: ERROR, WARNING]

# Without arguments
[Filter cleared - showing all levels]
```

**Error Cases**:
| Condition | Message |
|-----------|---------|
| Invalid level | `Error: Unknown level 'X'. Valid levels: DEBUG5..DEBUG1, INFO, NOTICE, WARNING, ERROR, LOG, FATAL, PANIC` |

---

### refresh

**Syntax**: `refresh`

**Description**: Re-scan for PostgreSQL instances.

**Output**:
```
[Scanning for PostgreSQL instances...]
[Found 3 instances]
```

**Behavior**:
- Runs full detection again
- Clears current instance selection
- Preserves filter settings

---

### stop

**Syntax**: `stop`

**Description**: Stop the current tail operation.

**Output**: (returns to prompt silently)

**Behavior**:
- Only effective during active tail
- No-op if not tailing

---

### clear

**Syntax**: `clear`

**Description**: Clear the terminal screen.

**Keyboard Shortcut**: Ctrl+L

---

### help

**Syntax**: `help`

**Description**: Show available commands.

**Output**:
```
pgtail - PostgreSQL log tailer

Commands:
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (alias: follow)
  levels [LEVEL...] Set log level filter (no args = clear)
  refresh           Re-scan for instances
  stop              Stop current tail
  clear             Clear screen
  help              Show this help
  quit              Exit pgtail (alias: exit)

Keyboard Shortcuts:
  Tab       Autocomplete
  Up/Down   Command history
  Ctrl+C    Stop tail / Clear input
  Ctrl+D    Exit (when input empty)
  Ctrl+L    Clear screen

Log Levels (for 'levels' command):
  PANIC FATAL ERROR WARNING NOTICE LOG INFO DEBUG1-5
```

---

### quit / exit

**Syntax**: `quit` or `exit`

**Description**: Exit pgtail.

**Keyboard Shortcut**: Ctrl+D (when input empty)

## Prompt Format

**Base Prompt**: `pgtail> `

**With Selected Instance**: `pgtail[N]> ` where N is the instance index

**With Filter**: `pgtail[N:FLT]> ` where FLT is abbreviated filter (e.g., `ERR,WARN`)

**Examples**:
```
pgtail> list
pgtail[0]> tail 0
pgtail[0:ERR,WARN]> levels ERROR WARNING
pgtail> quit
```

## Autocomplete Behavior

| Context | Suggestions |
|---------|-------------|
| Empty input | All commands |
| Partial command | Matching commands |
| After `tail ` | Instance indices, path fragments |
| After `levels ` | Valid log levels not yet specified |

## Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Normal exit (quit, exit, Ctrl+D) |
| 1 | Startup error (e.g., terminal not interactive) |

## Color Codes

Log level colors (ANSI escape sequences):

| Level | Foreground | Style |
|-------|------------|-------|
| PANIC | Red (31) | Bold |
| FATAL | Red (31) | Bold |
| ERROR | Red (31) | Normal |
| WARNING | Yellow (33) | Normal |
| NOTICE | Cyan (36) | Normal |
| LOG | Default | Normal |
| INFO | Green (32) | Normal |
| DEBUG* | Bright Black (90) | Normal |

**Color Disabled**: When `NO_COLOR` env var is set or terminal doesn't support colors.

## Version Output

```
pgtail version 0.1.0
```

Format: `pgtail version X.Y.Z`
