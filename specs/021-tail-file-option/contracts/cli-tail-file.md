# CLI Contract: tail --file

**Feature Branch**: `021-tail-file-option`
**Created**: 2026-01-05

## Overview

This document defines the CLI contract for the `--file` option added to the `tail` command in both the Typer CLI and REPL modes.

## Command Signature

### Typer CLI Mode

```
pgtail tail [INSTANCE_ID] [OPTIONS]
```

**Arguments**:

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `INSTANCE_ID` | `int` | No | `None` | Instance ID to tail (from `pgtail list`) |

**Options**:

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--file` | `-f` | `PATH` | `None` | Path to log file to tail (repeatable for multiple files, supports glob patterns) |
| `--stdin` | | `bool` | `False` | Read log data from stdin pipe |
| `--since` | `-s` | `str` | `None` | Show entries from time (e.g., 5m, 1h, 14:30) |
| `--stream` | | `bool` | `False` | Use legacy streaming mode instead of Textual UI |
| `--help` | | | | Show help and exit |

**Mutual Exclusivity**:
- `INSTANCE_ID` and `--file` are mutually exclusive
- `INSTANCE_ID` and `--stdin` are mutually exclusive
- `--file` and `--stdin` are mutually exclusive
- If conflicting options provided → error

### REPL Mode

```
tail [<id>] [--file <path>] [--since <time>] [--stream]
```

Same semantics as Typer CLI mode.

## Usage Examples

### Basic File Tailing

```bash
# Tail a pg_regress test log
pgtail tail --file ./tmp_check/log/postmaster.log

# Short form
pgtail tail -f ./tmp_check/log/postmaster.log

# Absolute path
pgtail tail --file /var/log/postgresql/postgresql-17-main.log
```

### With Time Filter

```bash
# Tail file with time filter
pgtail tail --file ./log.txt --since 5m

# Combined with other options
pgtail tail -f ./log.txt -s 1h --stream
```

### Glob Patterns

```bash
# Tail all .log files in current directory
pgtail tail --file "*.log"

# Tail all PostgreSQL logs in a directory
pgtail tail --file "/var/log/postgresql/*.log"

# Recursive pattern
pgtail tail --file "logs/**/*.log"
```

### Multiple Explicit Files

```bash
# Tail two specific files
pgtail tail --file primary.log --file replica.log

# Multiple files from different directories
pgtail tail --file /var/log/pg1/current.log --file /var/log/pg2/current.log
```

### Stdin Pipe

```bash
# Decompress and tail
gunzip -c postgresql.log.gz | pgtail tail --stdin

# Tail from remote server
ssh production "cat /var/log/postgresql/current.log" | pgtail tail --stdin

# Process archived logs
zcat archive/2024-01.log.gz | pgtail tail --stdin
```

### From REPL

```
pgtail> tail --file ./tmp_check/log/postmaster.log
pgtail> tail --file ./log.txt --since 5m
pgtail> tail --file "*.log"
pgtail> tail --file a.log --file b.log
```

## Response Formats

### Success

When tailing starts successfully, the Textual UI launches with:
- Log display area showing entries
- Status bar showing filename (or `PGver:port` if detected)
- Command input for filters

### Error Responses

| Condition | Exit Code | Message |
|-----------|-----------|---------|
| File not found | 1 | `File not found: <path>` |
| Permission denied | 1 | `Permission denied: <path>` |
| Is directory | 1 | `Not a file: <path> (is a directory)` |
| Both --file and ID | 1 | `Cannot specify both --file and instance ID` |
| --file without value | 1 | `--file requires a path argument` |
| Glob matches no files | 1 | `No files match pattern: <pattern>` |
| --stdin not piped | 1 | `--stdin requires piped input` |
| --stdin with --file | 1 | `Cannot specify both --stdin and --file` |
| --stdin with ID | 1 | `Cannot specify both --stdin and instance ID` |
| Empty stdin | 0 | `No input received` (exits gracefully) |

## Behavior Specifications

### Path Handling (FR-002, FR-011, FR-012, FR-013)

1. **Relative paths**: Resolved relative to current working directory
   ```bash
   # From /home/user/project
   pgtail tail -f ./tmp_check/log/postmaster.log
   # Resolves to: /home/user/project/tmp_check/log/postmaster.log
   ```

2. **Path normalization**: `..` segments resolved
   ```bash
   pgtail tail -f ../logs/../logs/pg.log
   # Normalized before processing
   ```

3. **Symlinks**: Followed automatically
   ```bash
   pgtail tail -f /var/log/postgresql/current  # symlink to actual log
   # Follows symlink to target file
   ```

4. **Spaces in paths**: Handled with quotes
   ```bash
   pgtail tail -f "/path with spaces/log.txt"
   pgtail tail -f '/path with spaces/log.txt'
   ```

### Format Detection (FR-003)

Auto-detects from file content:
- **TEXT**: Default PostgreSQL log format
- **CSV**: When `log_destination = 'csvlog'` was used
- **JSON**: When `log_destination = 'jsonlog'` was used (PG15+)

### Filter Support (FR-004)

All filter commands work identically:
- `level <lvl>` - Log level filter
- `filter /pattern/` - Regex filter
- `since <time>` - Time filter
- `until <time>` - Time filter
- `between <start> <end>` - Time range
- `slow <ms>` - Slow query threshold

### Status Bar Display (FR-006)

| Condition | Display |
|-----------|---------|
| Version detected from log | `PG17:5432` |
| Port detected, no version | `:5432` |
| Neither detected | `postmaster.log` (filename) |
| File unavailable | `postmaster.log (unavailable)` |
| Multiple files (glob) | `3 files (*.log)` |
| Multiple files (explicit) | `3 files` |
| Stdin mode | `stdin` |

### File Rotation (FR-009)

Same behavior as instance tailing:
- Truncation detected → restart from beginning
- File recreation detected → continue tailing new file

### File Deletion

Per clarification (2026-01-05):
- File deleted → Display notification, wait indefinitely
- User can exit manually with `q`
- If file recreated → resume tailing

### Glob Pattern Behavior (FR-014, FR-019)

- Patterns are expanded at command start
- Shell quoting required to prevent shell expansion (e.g., `--file "*.log"`)
- New files matching pattern are detected within 5 seconds
- Dynamic file watching during tail session

### Multi-File Behavior (FR-015, FR-017, FR-018)

- Multiple `--file` arguments supported
- Entries interleaved by timestamp across all files
- Source file indicator shown for each entry (e.g., `[primary.log]`)
- Independent format detection per file
- If one file becomes unreadable, continue tailing others with notification

### Stdin Behavior (FR-016)

- `--stdin` flag reads from stdin pipe
- EOF on stdin exits tail mode gracefully
- Format auto-detection from first few lines
- Stdin must be piped (not a terminal)

## Validation Rules

### Pre-Tailing Validation

```
1. Parse arguments
2. Check mutual exclusivity (--file vs INSTANCE_ID)
3. If --file provided:
   a. Resolve path to absolute
   b. Check exists (File not found)
   c. Check is_file (Not a file: is a directory)
   d. Check readable (Permission denied)
4. If all pass → enter tail mode
```

### Runtime Validation

- File truncated → Handled by LogTailer (restart from beginning)
- File deleted → Wait for recreation (no timeout)
- Permission changed → Display error, wait for restoration

## Examples with Expected Output

### Example 1: Successful File Tail

```bash
$ pgtail tail --file ./tmp_check/log/postmaster.log
# Enters Textual UI
# Status bar shows: "FOLLOW | E:0 W:0 | 0 lines | levels:ALL | postmaster.log"
```

### Example 2: File with Detected Instance

```bash
$ pgtail tail --file ./postgresql-17-main.log
# If log contains PostgreSQL startup messages:
# Status bar shows: "FOLLOW | E:0 W:0 | 0 lines | levels:ALL | PG17:5432"
```

### Example 3: Error - File Not Found

```bash
$ pgtail tail --file ./nonexistent.log
File not found: /current/path/nonexistent.log
$ echo $?
1
```

### Example 4: Error - Mutual Exclusivity

```bash
$ pgtail tail --file ./log.txt 0
Cannot specify both --file and instance ID
$ echo $?
1
```

### Example 5: REPL Usage

```
$ pgtail
pgtail - PostgreSQL log tailer

Found 2 PostgreSQL instances. Type 'list' to see details.
Type 'help' for available commands, 'quit' to exit.

pgtail> tail --file ./tmp_check/log/postmaster.log
# Enters tail mode for file
```

## Compatibility Notes

### Backward Compatibility

- Existing `pgtail tail <id>` usage unchanged
- `pgtail tail` with no args still works (uses first instance)
- All existing flags (`--since`, `--stream`) work with `--file`

### Cross-Platform Behavior

- Path separators: Use OS-native (handled by pathlib)
- Home directory: `~` expansion supported
- Environment variables: Not expanded (use shell expansion)

## Implementation Checklist

### Single File Support
- [ ] Add `--file` option to Typer CLI (`cli_main.py`)
- [ ] Add `--file` parsing to REPL (`cli_core.py`)
- [ ] Implement path validation function
- [ ] Add mutual exclusivity check
- [ ] Update help text
- [ ] Add `--file` to tab completion
- [ ] Update status bar for filename display
- [ ] Add instance detection from log content
- [ ] Handle file deletion scenario

### Glob Pattern Support (FR-014, FR-019)
- [ ] Implement glob pattern expansion
- [ ] Add "No files match pattern" error handling
- [ ] Implement dynamic file watching for new matches
- [ ] Add glob-specific status bar display

### Multiple Files Support (FR-015, FR-017, FR-018)
- [ ] Support multiple `--file` arguments
- [ ] Implement timestamp-based interleaving
- [ ] Add source file indicator to log entries
- [ ] Implement independent format detection per file
- [ ] Handle partial file unavailability

### Stdin Support (FR-016)
- [ ] Add `--stdin` flag
- [ ] Implement stdin reader
- [ ] Add terminal detection (require piped input)
- [ ] Handle EOF gracefully
- [ ] Add stdin-specific status bar display

### Tests
- [ ] Add unit tests for single file
- [ ] Add unit tests for glob patterns
- [ ] Add unit tests for multi-file
- [ ] Add unit tests for stdin
- [ ] Add integration tests for all scenarios
