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

### 4. Multiple Log Files (Glob Pattern)

Tail all logs matching a pattern:

```bash
# Tail all .log files in current directory
pgtail tail --file "*.log"

# Tail all PostgreSQL logs in a directory
pgtail tail --file "/var/log/postgresql/*.log"
```

### 5. Multiple Explicit Files

Compare logs from multiple sources:

```bash
# Tail two specific files
pgtail tail --file primary.log --file replica.log

# Tail logs from multiple PostgreSQL instances
pgtail tail --file /var/lib/pgsql/15/data/log/postgresql.log --file /var/lib/pgsql/16/data/log/postgresql.log
```

### 6. Stdin Pipe Support

Process compressed or remote logs:

```bash
# Decompress and tail
gunzip -c postgresql.log.gz | pgtail tail --stdin

# Tail from remote server
ssh production "cat /var/log/postgresql/current.log" | pgtail tail --stdin

# Process archived logs
zcat archive/2024-01.log.gz | pgtail tail --stdin
```

## What Works

All pgtail features work identically with `--file`:

- **Filters**: `level error`, `filter /deadlock/`, `since 5m`
- **Export**: `export ./output.txt`, `pipe jq`
- **Stats**: `errors`, `connections`, `stats`
- **Themes**: `theme monokai`, `theme list`
- **Navigation**: vim keys (j/k/g/G), visual mode (v/V), yank (y)
- **Multi-file**: Glob patterns (`*.log`), multiple `--file` arguments
- **Stdin**: Piped input from external commands

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

When tailing multiple files:

```
FOLLOW | E:0 W:0 | 42 lines | levels:ALL | 3 files (*.log)
                                           ^^^^^^^^^^^^^^^
                                           File count and pattern
```

## Error Messages

| Situation | Error Message |
|-----------|---------------|
| File doesn't exist | `File not found: /path/to/file.log` |
| Permission denied | `Permission denied: /path/to/file.log` |
| Path is a directory | `Not a file: /path (is a directory)` |
| Used with instance ID | `Cannot specify both --file and instance ID` |
| Glob matches no files | `No files match pattern: *.xyz` |
| Stdin is a terminal | `--stdin requires piped input` |
| Stdin is empty | `No input received` |

## Tips

1. **Relative paths work**: `./logs/pg.log` resolved relative to current directory
2. **Symlinks followed**: Automatically follows symlinks to target file
3. **Spaces in paths**: Quote the path: `--file "/path with spaces/log.txt"`
4. **File rotation handled**: Truncation/recreation detected automatically
5. **File deletion**: pgtail waits for file recreation (press `q` to exit)
6. **Glob quoting**: Quote glob patterns to prevent shell expansion: `--file "*.log"`
7. **Multi-file ordering**: Entries interleaved by timestamp across files
8. **Source indicators**: Multi-file mode shows which file each entry came from
9. **Dynamic globs**: New files matching the pattern are automatically included
10. **Stdin EOF**: Tail mode exits gracefully when stdin ends

## Implementation Details

For developers working on this feature:

- **CLI entry point**: `pgtail_py/cli_main.py` - Typer command definition
- **REPL entry point**: `pgtail_py/cli_core.py` - `tail_command()` function
- **Status bar**: `pgtail_py/tail_status.py` - `filename` field
- **TailApp**: `pgtail_py/tail_textual.py` - supports `instance=None` for file-only mode

### Key Files to Modify

1. `cli_main.py` - Add `--file` option, glob expansion, `--stdin` to `tail` command
2. `cli_core.py` - Add `--file`, glob, `--stdin` parsing to REPL handler
3. `tail_status.py` - Add filename/multi-file display support
4. `tail_textual.py` - Support file-only mode and multi-file mode
5. `commands.py` - Add completion for `--file` and `--stdin`
6. `tailer.py` - Add multi-file interleaving and stdin reader
7. `tail_rich.py` - Add source file indicator for multi-file mode

### Testing

```bash
# Create test log files
echo "2024-01-15 10:00:00 UTC LOG: test message" > /tmp/test.log
echo "2024-01-15 10:00:01 UTC LOG: another message" > /tmp/test2.log

# Test single file tailing
pgtail tail -f /tmp/test.log

# Test with time filter
pgtail tail -f /tmp/test.log --since 5m

# Test glob pattern
pgtail tail --file "/tmp/test*.log"

# Test multiple files
pgtail tail --file /tmp/test.log --file /tmp/test2.log

# Test stdin
echo "2024-01-15 10:00:00 UTC LOG: stdin message" | pgtail tail --stdin
```
