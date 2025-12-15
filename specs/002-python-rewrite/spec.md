# Feature Specification: pgtail Python Rewrite

**Feature Branch**: `002-python-rewrite`
**Created**: 2025-12-14
**Status**: Draft
**Input**: Rewrite pgtail from Go to Python using python-prompt-toolkit for better terminal color support across platforms.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch and List Instances (Priority: P1)

A developer launches pgtail and immediately sees all detected PostgreSQL instances on their system without any configuration.

**Why this priority**: This is the entry point for all users. Without instance detection, no other features work.

**Independent Test**: Can be fully tested by launching the application and verifying detected instances match running PostgreSQL processes and known installation paths.

**Acceptance Scenarios**:

1. **Given** a system with PostgreSQL running, **When** user launches pgtail, **Then** the REPL prompt appears within 2 seconds with detected instances listed.
2. **Given** a system with pgrx data directories in ~/.pgrx/, **When** user runs `list`, **Then** all pgrx instances are shown with their version numbers.
3. **Given** no PostgreSQL instances on the system, **When** user launches pgtail, **Then** a helpful message indicates no instances found and suggests checking paths.

---

### User Story 2 - Tail Logs with Color Output (Priority: P1)

A developer tails PostgreSQL logs and sees color-coded output by severity level, working consistently on macOS, Linux, and Windows terminals.

**Why this priority**: This is the core functionality and the primary motivation for the rewrite (fixing color issues on Linux).

**Independent Test**: Can be tested by tailing a log file with mixed severity levels and verifying colors render correctly on all three platforms.

**Acceptance Scenarios**:

1. **Given** a detected PostgreSQL instance with logging enabled, **When** user runs `tail 1`, **Then** new log entries appear in real-time with color-coded severity.
2. **Given** an active tail session, **When** PostgreSQL writes an ERROR log, **Then** the line appears in red immediately.
3. **Given** a terminal with TERM=linux (16-color mode), **When** user tails logs, **Then** colors degrade gracefully to available palette.
4. **Given** NO_COLOR environment variable is set, **When** user tails logs, **Then** output appears without any color codes.

---

### User Story 3 - Filter by Log Level (Priority: P2)

A developer filters log output to show only errors and warnings while debugging, reducing noise from routine messages.

**Why this priority**: Filtering enhances usability but requires tailing to work first.

**Independent Test**: Can be tested by setting filters and verifying only matching log levels appear.

**Acceptance Scenarios**:

1. **Given** an active tail session, **When** user runs `levels ERROR WARNING`, **Then** only ERROR and WARNING messages appear.
2. **Given** active filters, **When** user runs `levels` with no arguments, **Then** current filter settings are displayed.
3. **Given** active filters, **When** user runs `levels ALL`, **Then** all log levels are shown again.

---

### User Story 4 - Interactive REPL with Autocomplete (Priority: P2)

A developer uses the interactive REPL with command autocomplete and persistent history across sessions.

**Why this priority**: Enhances developer experience but core functionality works without it.

**Independent Test**: Can be tested by typing partial commands and verifying autocomplete suggestions appear.

**Acceptance Scenarios**:

1. **Given** the REPL is running, **When** user types `ta` and presses Tab, **Then** `tail` is autocompleted.
2. **Given** previous session had commands, **When** user starts new session and presses Up arrow, **Then** previous commands appear in history.
3. **Given** multiple detected instances, **When** user types `tail ` and presses Tab, **Then** instance IDs/paths are suggested.

---

### User Story 5 - Enable Logging for Instance (Priority: P3)

A developer discovers an instance without logging enabled and can turn it on directly from pgtail.

**Why this priority**: Convenience feature that requires core detection to work first.

**Independent Test**: Can be tested by targeting an instance with logging_collector=off and verifying it gets enabled.

**Acceptance Scenarios**:

1. **Given** an instance with logging_collector=off, **When** user runs `enable-logging 1`, **Then** postgresql.conf is modified and user is prompted to restart.
2. **Given** an instance the user cannot write to, **When** user runs `enable-logging 1`, **Then** a clear error explains the permission issue and suggests sudo.

---

### Edge Cases

- What happens when a log file is rotated while tailing? System should seamlessly switch to new file.
- What happens when PostgreSQL crashes during tail? System should report the instance stopped and return to prompt.
- What happens when user specifies invalid instance ID? System should list valid IDs and suggest closest match.
- What happens when log file has non-UTF8 characters? System should handle gracefully without crashing.
- What happens when terminal window is resized during output? Output should adapt to new width.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST auto-detect PostgreSQL instances from running processes, ~/.pgrx/ directories, PGDATA environment variable, and platform-specific default paths.
- **FR-002**: System MUST display detected instances in a formatted table with ID, version, status (running/stopped), data directory, and log path.
- **FR-003**: System MUST tail log files in real-time using file system watching with polling fallback.
- **FR-004**: System MUST parse PostgreSQL log lines to extract timestamp, severity level, and message.
- **FR-005**: System MUST color-code log output by severity: PANIC/FATAL (magenta), ERROR (red), WARNING (yellow), NOTICE (cyan), LOG/INFO (default), DEBUG (dim).
- **FR-006**: System MUST support filtering by log level with `levels` command accepting multiple levels.
- **FR-007**: System MUST provide command autocomplete for all commands and their arguments.
- **FR-008**: System MUST persist command history across sessions in a platform-appropriate location.
- **FR-009**: System MUST respect NO_COLOR environment variable to disable color output.
- **FR-010**: System MUST work identically on macOS, Linux, and Windows.
- **FR-011**: System MUST provide `enable-logging` command to modify postgresql.conf logging_collector setting.
- **FR-012**: System MUST handle `stop` command to halt current tail and return to prompt.
- **FR-013**: System MUST handle `clear` command to clear terminal screen.
- **FR-014**: System MUST handle `refresh` command to re-scan for instances.
- **FR-015**: System MUST handle `quit`/`exit` commands and Ctrl+D to exit gracefully.
- **FR-016**: System MUST be distributable as a single executable file per platform.

### Key Entities

- **Instance**: Represents a detected PostgreSQL installation with: ID (integer), version (string), data directory path, log file path, detection source (process/pgrx/pgdata/known-path), running status (boolean).
- **LogEntry**: Represents a parsed log line with: timestamp, severity level, message text, raw line.
- **LogLevel**: Enumeration of PostgreSQL log levels: PANIC, FATAL, ERROR, WARNING, NOTICE, LOG, INFO, DEBUG1-DEBUG5.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can detect and list PostgreSQL instances within 2 seconds of launching pgtail.
- **SC-002**: Log entries appear in the terminal within 500ms of being written to the log file.
- **SC-003**: Color-coded output renders correctly on all three platforms (macOS, Linux, Windows) including 16-color terminals.
- **SC-004**: Command autocomplete suggestions appear within 100ms of user input.
- **SC-005**: Application startup time is under 1 second on standard hardware.
- **SC-006**: 100% feature parity with the existing Go implementation.
- **SC-007**: Single executable file size is under 50MB per platform.

## Assumptions

- Users have PostgreSQL installed via standard methods (package manager, Homebrew, source, pgrx).
- Log files use PostgreSQL's default log format (timestamp, level, message).
- Terminal emulators support basic ANSI escape codes (true for all modern terminals).
- History file location follows XDG spec on Linux, ~/Library on macOS, %APPDATA% on Windows.
- Users running pgtail have read access to PostgreSQL data directories and log files.
