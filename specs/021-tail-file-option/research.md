# Research: Tail Arbitrary Log Files

**Feature Branch**: `021-tail-file-option`
**Created**: 2026-01-05
**Status**: Complete

## Research Questions

### R1: How to extend CLI argument parsing for --file option?

**Context**: Need to add `--file <path>` option to both Typer CLI (`cli_main.py`) and REPL (`cli_core.py`).

**Research Findings**:

1. **Typer CLI** (`pgtail_py/cli_main.py:149-221`):
   - Current `tail` command uses `typer.Argument(help="Instance ID to tail.")` for `instance_id`
   - Adding `--file` requires making `instance_id` optional: `typer.Argument(default=None)`
   - Use `typer.Option("--file", "-f")` for the file path
   - Mutual exclusivity: Check both provided → error

2. **REPL** (`pgtail_py/cli_core.py:169-252`):
   - Current parsing loops through args looking for `--since`, `--stream`
   - Add `--file` with next arg as path value
   - Path validation before instance lookup

**Decision**: Follow existing argument parsing patterns in both entry points.

**Alternatives Considered**:
- Separate command (`pgtail tail-file <path>`) - Rejected: Adds command proliferation, violates Simplicity First
- Subcommand (`pgtail tail file <path>`) - Rejected: Inconsistent with existing `tail <id>` pattern

---

### R2: Path validation and resolution approach?

**Context**: FR-011 requires resolving relative paths; FR-012 requires handling spaces and special characters.

**Research Findings**:

1. **pathlib.Path** is the standard cross-platform approach:
   ```python
   from pathlib import Path

   path = Path(user_input)
   resolved = path.resolve()  # Absolute, normalized, symlinks resolved
   ```

2. **Validation sequence**:
   ```python
   if not resolved.exists():
       # File not found
   if not resolved.is_file():
       # Is a directory or other non-file
   if not os.access(resolved, os.R_OK):
       # Permission denied
   ```

3. **Symlink handling**: `Path.resolve()` automatically follows symlinks (FR-013)

**Decision**: Use `pathlib.Path.resolve()` immediately on command entry, then validate.

**Alternatives Considered**:
- `os.path.abspath()` - Less modern, doesn't handle symlinks
- Manual normalization - Error-prone, reinvents wheel

---

### R3: How to support file-only mode in TailApp?

**Context**: Current `TailApp` requires an `Instance` object. Need to support tailing without a detected instance.

**Research Findings**:

1. **Current TailApp constructor** (`pgtail_py/tail_textual.py:126-155`):
   ```python
   def __init__(
       self,
       state: AppState,
       instance: Instance,  # Required
       log_path: Path,
       max_lines: int = 10000,
   ) -> None:
   ```

2. **Instance usage in TailApp**:
   - `_instance.version` and `_instance.port` for status bar (`on_mount`:223-227)
   - `_instance.data_dir` and `log_path.parent` for LogTailer (`on_mount`:253)

3. **Options**:
   - Make `instance` optional (`Instance | None`)
   - Add `file_path` as alternative to instance
   - Create lightweight "FileSource" dataclass

**Decision**: Make `instance` parameter `Instance | None`, add separate `file_path` handling path. When `instance` is None, status bar shows filename.

**Rationale**: Minimal changes, no new classes, clean separation.

---

### R4: How to detect PostgreSQL version/port from log content?

**Context**: FR-006 requires showing `PG17:5432` format if version/port detectable from log content.

**Research Findings**:

1. **PostgreSQL startup log messages**:
   ```
   LOG:  starting PostgreSQL 17.0 on x86_64-pc-linux-gnu, compiled by gcc...
   LOG:  listening on IPv4 address "0.0.0.0", port 5432
   LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
   ```

2. **Regex patterns**:
   ```python
   VERSION_PATTERN = r'starting PostgreSQL (\d+)(?:\.(\d+))?'
   PORT_PATTERN = r'listening on .*port (\d+)'
   ```

3. **Detection timing**:
   - Check first ~50 lines of file
   - Update status bar when detected
   - Don't block on detection

**Decision**: Add `_detect_instance_info()` method to TailApp that scans initial entries asynchronously.

**Alternatives Considered**:
- Synchronous scan before tailing - Rejected: Violates 1-second startup goal
- Never detect - Rejected: Violates FR-006

---

### R5: Status bar format for file-only mode?

**Context**: Status bar currently shows `PGver:port`. Need filename fallback.

**Research Findings**:

1. **Current implementation** (`pgtail_py/tail_status.py:199-206`):
   ```python
   if self.pg_version:
       parts.append((\"class:status.instance\", f\"PG{self.pg_version}:{self.pg_port}\"))
   else:
       parts.append((\"class:status.instance\", f\":{self.pg_port}\"))
   ```

2. **Proposed change**:
   ```python
   # Add filename field
   filename: str | None = None

   # In format_rich():
   if self.pg_version:
       text.append(f"PG{self.pg_version}:{self.pg_port}")
   elif self.filename:
       text.append(self.filename)
   else:
       text.append(f":{self.pg_port}")
   ```

**Decision**: Add `filename` attribute to TailStatus, use as fallback when `pg_version` not set.

---

### R6: How to handle file deletion during tailing?

**Context**: Clarification decided "wait indefinitely for recreation".

**Research Findings**:

1. **Current LogTailer behavior** (`pgtail_py/tailer.py:256-262`):
   - OSError caught, sets `_file_unavailable_since`
   - Calls `_check_for_new_log_file()` to look for replacement

2. **For arbitrary files without data_dir**:
   - `_check_for_new_log_file()` requires `_data_dir` or `_log_directory`
   - Neither available for arbitrary file paths
   - Current behavior: Just waits (no new file detection)

3. **Notification**: Add visual indication in status bar when file unavailable

**Decision**:
- LogTailer already handles this correctly for arbitrary files (waits for recreation)
- Add optional file unavailable indicator to status bar
- Match existing restart resilience behavior

---

### R7: Command completion for --file?

**Context**: Tab completion should suggest `--file` for `tail` command.

**Research Findings**:

1. **Current PgtailCompleter** (`pgtail_py/commands.py`):
   - Uses `prompt_toolkit.completion.NestedCompleter`
   - `tail` completions include instance IDs

2. **Adding --file**:
   ```python
   COMMANDS = {
       "tail": {
           "--file": PathCompleter(),  # prompt_toolkit has PathCompleter
           "--since": None,
           "--stream": None,
           # Dynamic instance IDs added at runtime
       },
       ...
   }
   ```

**Decision**: Add `--file` with `PathCompleter()` to tail command completions.

---

## Technology Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Path handling | `pathlib.Path.resolve()` | Cross-platform, handles symlinks |
| File-only mode | Optional `Instance` in TailApp | Minimal changes, clean separation |
| Instance detection | Async regex scan of first 50 lines | Non-blocking, meets 1-second goal |
| Status bar | `filename` fallback field | Simple addition to existing pattern |
| File deletion | Existing wait behavior | Already implemented in LogTailer |
| Completions | `PathCompleter` for --file | Built-in prompt_toolkit support |

## Dependencies

No new dependencies required. All functionality uses:
- `pathlib` (stdlib)
- `prompt_toolkit` (existing)
- `textual` (existing)
- `typer` (existing)

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Instance detection slows startup | Async detection, don't block on it |
| Path with spaces breaks shell | pathlib handles internally; user quotes in shell |
| Large files slow initial load | Existing 10,000 line buffer limit applies |
| Symlink loops | `Path.resolve()` handles with max depth |
