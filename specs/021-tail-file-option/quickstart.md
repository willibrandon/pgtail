# Quickstart: Tail Arbitrary Log Files

**Feature Branch**: `021-tail-file-option`
**Created**: 2026-01-05

## Overview

This feature adds the `--file` (or `-f`) option to pgtail's `tail` command, allowing you to tail PostgreSQL log files at any path rather than only auto-detected instances.

## Quick Examples

### Basic Usage

```bash
# Tail a pg_regress test log
pgtail tail --file ./tmp_check/log/postmaster.log

# Short form
pgtail tail -f ./tmp_check/log/postmaster.log
```

### With Time Filter

```bash
# Show logs from the last 5 minutes
pgtail tail -f ./log.txt --since 5m
```

### From the REPL

```
pgtail> tail --file ./tmp_check/log/postmaster.log
```

## Common Use Cases

### 1. pg_regress Test Logs

When running `make installcheck` for PostgreSQL extension development:

```bash
cd my-extension
make installcheck

# Test failed? Check the logs
pgtail tail -f ./tmp_check/log/postmaster.log
```

### 2. Archived/Downloaded Logs

Analyzing logs from a production incident:

```bash
pgtail tail --file /var/log/pg-archive/postgresql-2024-01.csv
```

### 3. Non-Standard Installations

Logs in custom locations:

```bash
pgtail tail --file /opt/custom/postgres/logs/postgresql.log
```

## What Works

All pgtail features work identically with `--file`:

- **Filters**: `level error`, `filter /deadlock/`, `since 5m`
- **Export**: `export ./output.txt`, `pipe jq`
- **Stats**: `errors`, `connections`, `stats`
- **Themes**: `theme monokai`, `theme list`
- **Navigation**: vim keys (j/k/g/G), visual mode (v/V), yank (y)

## Status Bar

When tailing arbitrary files, the status bar shows:

```
FOLLOW | E:0 W:0 | 42 lines | levels:ALL | postmaster.log
                                            ^^^^^^^^^^^^^
                                            Filename shown here
```

If PostgreSQL version/port is detected from log content:

```
FOLLOW | E:0 W:0 | 42 lines | levels:ALL | PG17:5432
                                           ^^^^^^^^^
                                           Detected from log content
```

## Error Messages

| Situation | Error Message |
|-----------|---------------|
| File doesn't exist | `File not found: /path/to/file.log` |
| Permission denied | `Permission denied: /path/to/file.log` |
| Path is a directory | `Not a file: /path (is a directory)` |
| Used with instance ID | `Cannot specify both --file and instance ID` |

## Tips

1. **Relative paths work**: `./logs/pg.log` resolved relative to current directory
2. **Symlinks followed**: Automatically follows symlinks to target file
3. **Spaces in paths**: Quote the path: `--file "/path with spaces/log.txt"`
4. **File rotation handled**: Truncation/recreation detected automatically
5. **File deletion**: pgtail waits for file recreation (press `q` to exit)

## Implementation Details

For developers working on this feature:

- **CLI entry point**: `pgtail_py/cli_main.py` - Typer command definition
- **REPL entry point**: `pgtail_py/cli_core.py` - `tail_command()` function
- **Status bar**: `pgtail_py/tail_status.py` - `filename` field
- **TailApp**: `pgtail_py/tail_textual.py` - supports `instance=None` for file-only mode

### Key Files to Modify

1. `cli_main.py` - Add `--file` option to `tail` command
2. `cli_core.py` - Add `--file` parsing to REPL handler
3. `tail_status.py` - Add filename display support
4. `tail_textual.py` - Support file-only mode
5. `commands.py` - Add completion for `--file`

### Testing

```bash
# Create test log file
echo "2024-01-15 10:00:00 UTC LOG: test message" > /tmp/test.log

# Test file tailing
pgtail tail -f /tmp/test.log

# Test with time filter
pgtail tail -f /tmp/test.log --since 5m
```
