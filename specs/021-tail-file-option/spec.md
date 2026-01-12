# Feature Specification: Tail Arbitrary Log Files

**Feature Branch**: `021-tail-file-option`
**Created**: 2026-01-05
**Status**: Draft
**Input**: Issue #11 - Add `--file` option to tail command for arbitrary log file paths

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tail pg_regress Test Logs (Priority: P0 - MANDATORY)

A PostgreSQL extension developer runs `make installcheck` and needs to debug a failing regression test. The test creates logs in `tmp_check/log/postmaster.log` which are not detected by pgtail's automatic instance detection.

**Why this is mandatory**: This is the primary use case driving the feature request. Extension developers frequently need to inspect test logs, and the current workflow requires manual file inspection with less capable tools.

**Independent Test**: Can be fully tested by creating a log file at an arbitrary path and running `tail --file <path>`. Delivers immediate value for debugging pg_regress failures.

**Acceptance Scenarios**:

1. **Given** a log file at `./tmp_check/log/postmaster.log`, **When** user runs `tail --file ./tmp_check/log/postmaster.log`, **Then** pgtail opens the file in tail mode with full format auto-detection and filter support.

2. **Given** a log file at an absolute path `/home/user/project/tmp_check/log/postmaster.log`, **When** user runs `tail --file /home/user/project/tmp_check/log/postmaster.log`, **Then** pgtail opens the file using the absolute path.

3. **Given** the user is already in tail mode for a file, **When** they apply filters like `level error` or `filter /FATAL/`, **Then** the filters work identically to auto-detected instance tailing.

---

### User Story 2 - Tail Archived or Downloaded Logs (Priority: P0 - MANDATORY)

A DBA has downloaded PostgreSQL log files from a production server for post-incident analysis. The logs are stored in a local directory and need to be analyzed with pgtail's filtering capabilities.

**Why this is mandatory**: Analyzing historical logs is a common debugging workflow. It extends pgtail's utility beyond running instances and is essential for incident post-mortems.

**Independent Test**: Can be fully tested by placing a PostgreSQL log file in any directory and tailing it with `--file`. Delivers value for incident post-mortems.

**Acceptance Scenarios**:

1. **Given** an archived CSV log file `/var/log/pg-archive/postgresql-2024-01.csv`, **When** user runs `tail --file /var/log/pg-archive/postgresql-2024-01.csv`, **Then** pgtail auto-detects CSV format and provides structured field access.

2. **Given** a JSON format log file, **When** tailed with `--file`, **Then** pgtail auto-detects JSON format and enables field filtering (app=, db=, user=).

3. **Given** an archived log file that is not actively written to, **When** user opens it with `--file`, **Then** pgtail displays existing content and waits for new entries (which may never arrive for static files).

---

### User Story 3 - CLI-Level File Tailing (Priority: P0 - MANDATORY)

A user wants to tail a log file directly from the shell without entering the REPL, combining with other flags.

**Why this is mandatory**: CLI ergonomics are critical for quick debugging and scripting. Users expect to chain flags like `--since` with `--file`.

**Independent Test**: Can be tested by running `pgtail tail --file <path> --since 5m` from the command line. Delivers value for one-liner debugging.

**Acceptance Scenarios**:

1. **Given** a log file path, **When** user runs `pgtail tail --file ./log.txt --since 5m`, **Then** pgtail opens the file with a 5-minute time filter applied.

2. **Given** a log file path, **When** user runs `pgtail tail --file ./log.txt --stream`, **Then** pgtail uses legacy streaming mode (same behavior as with auto-detected instances).

3. **Given** both `--file` and an instance ID, **When** user runs `pgtail tail --file ./log.txt 0`, **Then** pgtail shows an error indicating these options are mutually exclusive.

---

### User Story 4 - REPL-Level File Tailing (Priority: P0 - MANDATORY)

A user is in the pgtail REPL and wants to switch from tailing an auto-detected instance to tailing an arbitrary file, or start tailing a file directly.

**Why this is mandatory**: Consistency between CLI and REPL behavior is essential. Users must be able to use `--file` in both contexts.

**Independent Test**: Can be tested by entering the REPL and running `tail --file <path>`. Delivers value for interactive debugging sessions.

**Acceptance Scenarios**:

1. **Given** user is in the REPL, **When** they run `tail --file ./tmp_check/log/postmaster.log`, **Then** pgtail enters tail mode for that file.

2. **Given** user is tailing an auto-detected instance, **When** they stop and run `tail --file ./other.log`, **Then** pgtail switches to tailing the new file.

3. **Given** user runs `tail --file` without a path, **When** the command is executed, **Then** pgtail displays a usage error: "Usage: tail --file <path>".

---

### User Story 5 - Glob Pattern Tailing (Priority: P0 - MANDATORY)

A user wants to tail multiple log files matching a pattern, such as all `.log` files in a directory.

**Why this is mandatory**: Power users need to tail multiple related logs simultaneously. This is essential for analyzing distributed systems, replicas, and multi-process PostgreSQL setups.

**Independent Test**: Can be tested by running `tail --file "*.log"` in a directory with multiple log files. Delivers value for multi-file analysis.

**Acceptance Scenarios**:

1. **Given** multiple log files `a.log`, `b.log`, `c.log` in the current directory, **When** user runs `tail --file "*.log"`, **Then** pgtail tails all matching files, interleaving entries by timestamp.

2. **Given** a glob pattern that matches no files, **When** user runs `tail --file "*.xyz"`, **Then** pgtail displays an error: "No files match pattern: *.xyz".

3. **Given** a glob pattern, **When** new files matching the pattern are created, **Then** pgtail detects and includes them in the tail (with indication of file source).

---

### User Story 6 - Multiple Explicit Files (Priority: P0 - MANDATORY)

A user wants to tail multiple specific files simultaneously.

**Why this is mandatory**: Comparing logs from multiple sources is essential for debugging complex issues. Users must be able to correlate events across multiple log files.

**Independent Test**: Can be tested by running `tail --file a.log --file b.log`. Delivers value for multi-source debugging.

**Acceptance Scenarios**:

1. **Given** two log files, **When** user runs `tail --file a.log --file b.log`, **Then** pgtail tails both files, interleaving entries by timestamp.

2. **Given** multiple files with different formats, **When** tailed together, **Then** each file's format is auto-detected independently and parsed correctly.

3. **Given** multiple files, **When** displayed in the log view, **Then** entries show their source file (e.g., filename prefix or indicator).

---

### User Story 7 - Stdin Pipe Support (Priority: P0 - MANDATORY)

A user wants to pipe log data into pgtail from stdin, such as from a decompressed archive.

**Why this is mandatory**: Integration with external tools and compressed archives is essential for production workflows. Users must be able to decompress and pipe logs without intermediate files.

**Independent Test**: Can be tested by running `cat log.gz | gunzip | pgtail tail --stdin`. Delivers value for compressed log analysis.

**Acceptance Scenarios**:

1. **Given** log data piped to stdin, **When** user runs `cat log.txt | pgtail tail --stdin`, **Then** pgtail reads from stdin and displays entries with normal filtering.

2. **Given** compressed log data, **When** user runs `gunzip -c log.gz | pgtail tail --stdin`, **Then** pgtail processes the decompressed stream.

3. **Given** stdin mode, **When** stdin reaches EOF, **Then** pgtail exits tail mode gracefully (no infinite wait).

---

### Edge Cases

- What happens when the file path does not exist?
  - Display error: "File not found: <path>" and return to prompt

- What happens when the file exists but is not readable (permission denied)?
  - Display error: "Permission denied: <path>" and return to prompt

- What happens when the file path is a directory instead of a file?
  - Display error: "Not a file: <path> (is a directory)" and return to prompt

- What happens when the file is deleted while tailing?
  - Display notification: "File removed: <filename>", wait indefinitely for recreation (user can exit manually with `q`)

- What happens when the file is truncated (rotated) while tailing?
  - Detect truncation and restart from beginning (existing rotation handling)

- What happens when a relative path contains `..` segments?
  - Resolve to absolute path before processing

- What happens when the path contains spaces or special characters?
  - Handle correctly with proper quoting in shell, escape in display

- What happens when `--file` is used with instance ID argument?
  - Display error: "Cannot specify both --file and instance ID" and return to prompt

- What happens when the file is empty?
  - Enter tail mode normally, waiting for new entries

- What happens when the file contains no valid PostgreSQL log entries?
  - Attempt parsing with text format, display unparsed lines as-is with UNKNOWN level

- What happens with symlinks?
  - Follow symlinks and tail the target file

- What happens when a glob pattern matches too many files (e.g., hundreds)?
  - Display warning: "Pattern matches N files (may impact performance)", proceed with tailing
  - Consider a configurable limit with `--max-files N` flag

- What happens when a glob pattern matches files in different formats (CSV, JSON, text)?
  - Auto-detect format independently for each file, parse each correctly

- What happens when one of multiple files becomes unreadable during tailing?
  - Continue tailing other files, show notification for unreadable file

- What happens when stdin is a terminal (not a pipe)?
  - Display error: "--stdin requires piped input" and exit with error code

- What happens when stdin is empty (immediate EOF)?
  - Display message: "No input received", exit tail mode gracefully

- What happens when entries from multiple files have identical timestamps?
  - Maintain consistent ordering (e.g., alphabetical by filename as secondary sort)

- What happens with binary data in stdin?
  - Attempt UTF-8 decode with replacement, parse lines as-is

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept a `--file <path>` option in the `tail` command to specify an arbitrary log file path
- **FR-002**: System MUST support both absolute paths (e.g., `/var/log/pg.log`) and relative paths (e.g., `./tmp_check/log/postmaster.log`)
- **FR-003**: System MUST auto-detect the log format (text, CSV, JSON) from file content, identical to auto-detected instance behavior
- **FR-004**: System MUST apply all existing filters (level, regex, time, slow query, field) to file-based tailing
- **FR-005**: System MUST display clear error messages for file not found, permission denied, and other file access errors
- **FR-006**: System MUST update the status bar to show filename (e.g., `postmaster.log`) when tailing a file; if PostgreSQL version/port can be detected from log content, display standard instance format (e.g., `PG17:5432`) instead
- **FR-007**: System MUST support combining `--file` with other flags like `--since` and `--stream`
- **FR-008**: System MUST work identically in both CLI mode (`pgtail tail --file <path>`) and REPL mode (`tail --file <path>`)
- **FR-009**: System MUST handle file rotation (truncation) identically to auto-detected instance tailing
- **FR-010**: System MUST reject commands that specify both `--file` and an instance ID with a clear error message
- **FR-011**: System MUST resolve relative paths to absolute paths for consistent internal handling
- **FR-012**: System MUST handle paths with spaces and special characters correctly
- **FR-013**: System MUST follow symlinks when a symlinked path is provided

### Multi-File and Pipe Requirements

- **FR-014**: System MUST support glob patterns (e.g., `--file "*.log"`) to tail multiple files matching a pattern
- **FR-015**: System MUST support multiple `--file` arguments (e.g., `--file a.log --file b.log`) to tail multiple specific files
- **FR-016**: System MUST support `--stdin` flag to read log data from stdin pipe
- **FR-017**: When tailing multiple files, system MUST interleave entries by timestamp
- **FR-018**: When tailing multiple files, system MUST indicate the source file for each entry
- **FR-019**: For glob patterns, system MUST detect newly created matching files and include them

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can open a log file at any path within 1 second of entering the command
- **SC-002**: All existing filter commands (level, filter, since, until, between, slow) work identically for file-based tailing
- **SC-003**: Format auto-detection correctly identifies text, CSV, and JSON formats in file-based tailing
- **SC-004**: Error messages for file access failures are clear and actionable
- **SC-005**: Users can combine `--file` with `--since` filter in a single command
- **SC-006**: File rotation is detected and handled without user intervention
- **SC-007**: Status bar displays filename when tailing arbitrary files, or detected instance info (version:port) when available from log content
- **SC-008**: Command works identically in CLI and REPL modes
- **SC-009**: Glob patterns expand correctly and tail all matching files simultaneously
- **SC-010**: Multiple `--file` arguments correctly interleave entries by timestamp
- **SC-011**: Source file indicators are visible for each entry when tailing multiple files
- **SC-012**: Newly created files matching a glob pattern are detected and included within 5 seconds
- **SC-013**: Stdin input is processed with the same filtering capabilities as file-based tailing
- **SC-014**: EOF on stdin exits tail mode gracefully without error

## Clarifications

### Session 2026-01-05

- Q: What timeout should apply when the file is deleted during tailing? → A: No timeout - wait indefinitely for recreation (user exits manually)
- Q: What format should the status bar use when tailing an arbitrary file? → A: Filename only (e.g., `postmaster.log`), but use standard instance format (e.g., `PG17:5432`) if instance info can be detected from log content

## Assumptions

1. **Path resolution**: Relative paths are resolved relative to the current working directory at command execution time
2. **File locking**: pgtail does not acquire exclusive locks on tailed files; other processes can continue writing
3. **Encoding**: Log files are assumed to be UTF-8 encoded (with fallback to replace errors, matching existing behavior)
4. **Buffer size**: The same 10,000 entry buffer limit applies to file-based tailing; for multi-file tailing, this is a combined limit across all files
5. **No instance detection bypass**: When using `--file`, no PostgreSQL instance detection is performed for that file
6. **Connection/Error stats**: When tailing arbitrary files, connection and error statistics are still tracked; instance-specific info (version, port) is detected from log content when available (e.g., from startup messages), otherwise shows filename
7. **Notifications**: Desktop notifications work with file-based tailing, using the same rules as instance tailing
8. **Glob expansion**: Glob patterns are expanded at command start; shell quoting required to prevent shell expansion (e.g., `--file "*.log"`)
9. **Multi-file memory**: Each file maintains its own read position and format detector; memory scales linearly with file count
10. **Stdin buffering**: Stdin is read line-by-line in non-blocking mode; large lines may be split across reads
11. **Stdin format detection**: Format auto-detection occurs on the first few lines of stdin input, same as file-based detection
