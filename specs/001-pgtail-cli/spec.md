# Feature Specification: pgtail CLI Tool

**Feature Branch**: `001-pgtail-cli`
**Created**: 2025-12-14
**Status**: Draft
**Input**: Cross-platform interactive CLI tool for discovering PostgreSQL instances and tailing their log files

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover PostgreSQL Instances (Priority: P1)

As a PostgreSQL developer, I want to quickly see all PostgreSQL instances on my machine so I can identify which logs to monitor without manually searching through file systems.

**Why this priority**: This is the foundational capability—without instance discovery, no other features work. Developers waste significant time hunting for PostgreSQL data directories across varied installation methods.

**Independent Test**: Can be fully tested by launching pgtail and running `list` command. Delivers immediate value by showing all detected instances with their versions, ports, and status.

**Acceptance Scenarios**:

1. **Given** a machine with one or more PostgreSQL instances installed, **When** the user launches pgtail and runs `list`, **Then** all instances are displayed in a table showing index, version, port, running status, source, and data directory.

2. **Given** a machine with pgrx-managed PostgreSQL instances, **When** the user runs `list`, **Then** all `~/.pgrx/data-{version}/` directories are detected and shown with source "pgrx".

3. **Given** a machine with Homebrew-installed PostgreSQL, **When** the user runs `list`, **Then** both `/opt/homebrew/var/postgresql@{version}/` (Apple Silicon) and `/usr/local/var/postgresql@{version}/` (Intel) paths are checked and detected instances displayed.

4. **Given** a machine with no PostgreSQL instances, **When** the user runs `list`, **Then** a helpful message is shown suggesting how to install PostgreSQL or check common locations.

---

### User Story 2 - Tail Instance Logs (Priority: P2)

As a PostgreSQL developer, I want to tail log files for a specific instance so I can monitor database activity and debug issues in real-time.

**Why this priority**: Tailing logs is the primary use case after discovery. Once a developer knows which instances exist, they need to actually view the logs.

**Independent Test**: Can be fully tested by selecting an instance from `list` output and running `tail <id>`. Delivers value by streaming log output to the terminal with color-coded log levels.

**Acceptance Scenarios**:

1. **Given** a list of detected instances, **When** the user runs `tail 0`, **Then** the log file for instance 0 is tailed with new lines appearing in real-time.

2. **Given** a running tail operation, **When** new log entries are written by PostgreSQL, **Then** they appear in the terminal within 1 second.

3. **Given** a tail command with a partial path like `tail pgrx`, **When** multiple instances match, **Then** the most relevant match is selected (fuzzy matching).

4. **Given** a tail command for an instance with no log files, **When** the user runs `tail`, **Then** a clear error message explains why and suggests checking `log_destination` configuration.

5. **Given** an active tail operation, **When** the user presses Ctrl+C, **Then** tailing stops and the user returns to the prompt.

---

### User Story 3 - Filter Logs by Level (Priority: P3)

As a PostgreSQL developer, I want to filter log output by severity level so I can focus on errors and warnings without wading through verbose output.

**Why this priority**: Filtering enhances the tailing experience but is not essential for basic functionality. Developers can still use pgtail effectively without filters.

**Independent Test**: Can be fully tested by setting a filter with `levels ERROR WARNING` and then tailing an instance. Delivers value by reducing noise and surfacing only important log entries.

**Acceptance Scenarios**:

1. **Given** no active filter, **When** the user runs `levels ERROR WARNING`, **Then** only ERROR and WARNING level messages are shown during subsequent tail operations.

2. **Given** an active filter, **When** the user runs `levels` with no arguments, **Then** the filter is cleared and all log levels are shown.

3. **Given** a filter set to ERROR, **When** the user tails an instance, **Then** DEBUG, INFO, LOG, NOTICE, and WARNING messages are hidden.

4. **Given** a filter is set, **When** the user runs a new `tail` command, **Then** the filter persists across tail sessions until explicitly cleared.

---

### User Story 4 - Interactive REPL Experience (Priority: P4)

As a PostgreSQL developer, I want an interactive prompt with autocomplete and command history so I can work efficiently without memorizing exact syntax.

**Why this priority**: The REPL enhances usability but is not strictly required—commands could theoretically work without autocomplete. This builds on top of the core detection and tailing functionality.

**Independent Test**: Can be fully tested by launching pgtail and using Tab for autocomplete, Up/Down for history. Delivers value by reducing friction and typos.

**Acceptance Scenarios**:

1. **Given** the pgtail prompt, **When** the user types `ta` and presses Tab, **Then** the input autocompletes to `tail`.

2. **Given** the user has run previous commands, **When** they press Up arrow, **Then** the previous command is recalled.

3. **Given** a tail command context, **When** the user types `tail ` and presses Tab, **Then** available instance indices and paths are suggested.

4. **Given** the `levels` command context, **When** the user presses Tab, **Then** valid log levels (DEBUG5...PANIC) are suggested.

---

### User Story 5 - Color-Coded Log Output (Priority: P5)

As a PostgreSQL developer, I want log output color-coded by severity so I can quickly spot errors and warnings visually.

**Why this priority**: Color coding improves usability but logs are still functional without it. This is a polish feature that enhances the experience.

**Independent Test**: Can be fully tested by tailing an instance that produces various log levels. Delivers value by making ERROR (red), WARNING (yellow), and other levels visually distinct.

**Acceptance Scenarios**:

1. **Given** a log entry with level ERROR, **When** it is displayed, **Then** the line appears in red.

2. **Given** a log entry with level WARNING, **When** it is displayed, **Then** the line appears in yellow.

3. **Given** a log entry with level FATAL or PANIC, **When** it is displayed, **Then** the line appears in bold red.

4. **Given** a terminal without color support, **When** logs are displayed, **Then** output falls back to plain text without ANSI codes.

---

### Edge Cases

- What happens when a detected log file is unreadable due to permissions?
  - The system reports the permission error clearly and suggests running with elevated privileges if appropriate.

- What happens when PostgreSQL rotates log files during an active tail?
  - The system detects the rotation and seamlessly switches to the new log file (future consideration, v1 may restart tail).

- What happens when the `log_destination` is set to syslog or eventlog instead of file?
  - The system reports the log destination type and provides guidance on alternative viewing methods.

- What happens when multiple PostgreSQL processes share the same data directory?
  - The system deduplicates by data directory path, showing each unique instance once.

- What happens when a data directory exists but is corrupted or incomplete?
  - The system skips corrupted instances with a warning rather than crashing.

## Requirements *(mandatory)*

### Functional Requirements

#### Instance Detection

- **FR-001**: System MUST detect running PostgreSQL instances by scanning process arguments for `-D` data directory flags.
- **FR-002**: System MUST detect pgrx-managed instances in `~/.pgrx/data-{version}/` directories.
- **FR-003**: System MUST scan common installation paths for each supported platform (Linux Debian/RHEL, macOS Homebrew/Postgres.app, Windows Program Files).
- **FR-004**: System MUST check the `PGDATA` environment variable for additional instances.
- **FR-005**: System MUST deduplicate detected instances by data directory path.
- **FR-006**: System MUST determine PostgreSQL version from `PG_VERSION` file in data directory.
- **FR-007**: System MUST determine listening port from `postgresql.conf` or `postmaster.pid`.
- **FR-008**: System MUST determine running status by checking for active postmaster process.

#### Log Location

- **FR-009**: System MUST parse `postgresql.conf` to find `log_directory` and `log_filename` settings.
- **FR-010**: System MUST scan default log locations (`{data_dir}/log/`, `{data_dir}/pg_log/`) when config is unavailable.
- **FR-011**: System MUST identify the most recent log file when multiple files match the pattern.

#### Commands

- **FR-012**: System MUST provide a `list` command showing all detected instances in tabular format.
- **FR-013**: System MUST provide a `tail` command accepting numeric index or path to select an instance.
- **FR-014**: System MUST provide a `refresh` command to re-scan for instances.
- **FR-015**: System MUST provide a `levels` command to set/clear log level filters.
- **FR-016**: System MUST provide `help`, `clear`, `quit`/`exit` commands.
- **FR-017**: System MUST support `follow` as an alias for `tail`.

#### User Interface

- **FR-018**: System MUST provide autocomplete for commands, instance identifiers, and log levels.
- **FR-019**: System MUST maintain command history navigable with Up/Down arrows.
- **FR-020**: System MUST display a dynamic prompt showing current state (selected instance, active filters).
- **FR-021**: System MUST color-code log output by severity level.
- **FR-022**: System MUST support Ctrl+C to stop tail operations and Ctrl+D to exit.

#### Cross-Platform

- **FR-023**: System MUST work identically on macOS, Linux, and Windows.
- **FR-024**: System MUST use platform-appropriate path handling (no hardcoded separators).
- **FR-025**: System MUST handle platform-specific process detection methods.

#### Error Handling

- **FR-026**: System MUST continue operation when individual detection methods fail.
- **FR-027**: System MUST provide actionable error messages with suggestions.
- **FR-028**: System MUST never crash due to permission errors or missing files.

### Key Entities

- **Instance**: Represents a PostgreSQL installation with data directory, version, port, running status, log location, and detection source.
- **DetectionSource**: Categorizes how an instance was discovered (process, pgrx, known path, environment variable, service).
- **LogLevel**: PostgreSQL log severity levels (DEBUG5-DEBUG1, INFO, NOTICE, WARNING, ERROR, LOG, FATAL, PANIC).
- **Filter**: User-configured set of log levels to display during tail operations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can find and begin tailing any PostgreSQL log in under 10 seconds from launching pgtail.
- **SC-002**: Zero manual configuration is required for pgrx development workflows—instances are auto-detected.
- **SC-003**: The tool works identically on macOS, Linux, and Windows with no platform-specific setup steps.
- **SC-004**: New users can be productive after reading only the `help` output—no external documentation required.
- **SC-005**: 100% of pgrx-managed instances are detected automatically on first `list` command.
- **SC-006**: 95% of common PostgreSQL installations (Homebrew, apt, yum, Windows installer) are detected without configuration.
- **SC-007**: Log entries appear in the terminal within 1 second of being written to the log file.
- **SC-008**: The command set is small enough to memorize (fewer than 10 commands).

## Assumptions

- Users have at least one PostgreSQL instance installed locally (tool provides helpful guidance if none found).
- Log files are stored on local filesystem (syslog/eventlog destinations show guidance, not direct viewing in v1).
- Users have read permissions for PostgreSQL data directories (tool reports permission issues clearly).
- Terminal supports standard input/output (tool works in any standard terminal emulator).
- Color output follows standard ANSI escape codes (fallback to plain text when unsupported).
