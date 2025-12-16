# Feature Specification: Export Logs and Pipe to External Commands

**Feature Branch**: `006-export-pipe`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Add commands to export log output to files or pipe to external commands. Support multiple output formats and the ability to apply current filters to exports."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export Filtered Logs to File (Priority: P1)

A developer has identified relevant error logs using pgtail's filtering capabilities and wants to save them to a file for later analysis, sharing with teammates, or attaching to bug reports.

**Why this priority**: This is the core value proposition of the feature - saving filtered log output is the most fundamental export capability and enables all downstream workflows (sharing, archiving, analysis).

**Independent Test**: Can be fully tested by applying filters, running export command, and verifying the output file contains exactly the filtered entries in the correct format.

**Acceptance Scenarios**:

1. **Given** the user has applied level filters (e.g., `levels ERROR FATAL`), **When** the user runs `export errors.log`, **Then** only log entries matching those levels are written to the file
2. **Given** the user has applied regex filters, **When** the user runs `export filtered.log`, **Then** only log entries matching the regex pattern are written to the file
3. **Given** the user runs `export output.log` on a path that already exists, **When** the file exists, **Then** the system warns the user and prompts for confirmation before overwriting
4. **Given** the user specifies `--append`, **When** the file exists, **Then** new entries are appended rather than overwriting

---

### User Story 2 - Export in JSON Format for Programmatic Analysis (Priority: P2)

A data engineer or developer wants to analyze PostgreSQL logs programmatically using tools like jq, Python, or other data processing pipelines. They need structured output format.

**Why this priority**: Structured formats (JSON, CSV) unlock programmatic analysis workflows that are essential for power users and integration with other tools.

**Independent Test**: Can be fully tested by exporting with `--format json`, then parsing the output file with a JSON parser to verify valid JSONL format with expected fields.

**Acceptance Scenarios**:

1. **Given** the user has log entries in the buffer, **When** the user runs `export --format json logs.json`, **Then** each log entry is written as a valid JSON object on its own line (JSONL format)
2. **Given** JSON export is used, **When** the file is written, **Then** each JSON object contains timestamp, level, pid, and message fields
3. **Given** the user runs `export --format csv logs.csv`, **When** the file is written, **Then** the output is valid CSV with headers: timestamp, level, pid, message

---

### User Story 3 - Pipe Logs to External Commands (Priority: P2)

A developer wants to use familiar Unix tools (grep, jq, wc, head) to process log output without leaving pgtail. This combines pgtail's filtering with the flexibility of the Unix toolchain.

**Why this priority**: Piping to external tools is equally important as JSON export for power users who prefer Unix pipelines over file-based workflows.

**Independent Test**: Can be fully tested by piping to a simple command like `wc -l` and verifying the count matches the number of filtered entries.

**Acceptance Scenarios**:

1. **Given** the user has filtered entries, **When** the user runs `pipe grep "connection"`, **Then** the filtered entries are sent to grep and results are displayed
2. **Given** the user wants JSON piped to jq, **When** the user runs `pipe --format json jq '.message'`, **Then** entries are converted to JSON before being piped to jq
3. **Given** the external command exits with an error, **When** the error occurs, **Then** the error message is displayed to the user

---

### User Story 4 - Continuous Export During Testing (Priority: P3)

An ops engineer or developer wants to capture all logs during a test run or debugging session, similar to `tail -f | tee logfile`. They need real-time export that continues until stopped.

**Why this priority**: Continuous export is valuable for specific use cases (test runs, debugging sessions) but is less commonly needed than one-time exports.

**Independent Test**: Can be fully tested by starting continuous export, generating new log entries, stopping with Ctrl+C, and verifying all entries were captured.

**Acceptance Scenarios**:

1. **Given** the user runs `export --follow test.log`, **When** new log entries arrive, **Then** they are immediately written to the file
2. **Given** continuous export is running, **When** the user presses Ctrl+C, **Then** export stops and displays the total count of entries written
3. **Given** continuous export is running, **When** the PostgreSQL log file rotates, **Then** export continues capturing from the new log file without interruption
4. **Given** continuous export is running, **When** entries are being written, **Then** entries are also displayed on screen (like `tee`)

---

### Edge Cases

- What happens when the target directory doesn't exist? The system automatically creates parent directories if the user has write permission; otherwise displays a permission error.
- What happens when disk space runs out during export? The system should handle gracefully and report how many entries were written.
- What happens when the pipe command doesn't exist? The system should report the error clearly.
- What happens when the pipe command takes a long time? The system should stream entries and not buffer everything in memory.
- What happens when the user exports with no entries in buffer/filter? The system should report "0 entries exported" rather than silently creating an empty file.
- What happens when special characters appear in log messages (quotes, newlines)? JSON and CSV formats should properly escape these characters.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an `export <filename>` command that writes filtered log entries to a file
- **FR-002**: System MUST apply current filters (level, regex, time) to all exports
- **FR-003**: System MUST support `--format` option with values: text (default), json, csv
- **FR-004**: System MUST support `--follow` option for continuous export
- **FR-005**: System MUST support `--append` option to append to existing files
- **FR-006**: System MUST warn and prompt before overwriting existing files (unless `--append` used)
- **FR-007**: System MUST provide a `pipe <command>` command that streams filtered entries to external processes
- **FR-008**: System MUST support `--format` option on pipe command for format conversion before piping
- **FR-009**: JSON format MUST produce valid JSONL (one JSON object per line) with fields: timestamp (ISO 8601), level, pid, message
- **FR-010**: CSV format MUST produce valid CSV with header row and columns: timestamp (ISO 8601), level, pid, message
- **FR-011**: System MUST properly escape special characters (quotes, newlines, commas) in JSON and CSV output
- **FR-012**: System MUST display count of exported entries upon completion
- **FR-013**: System MUST stream entries for large exports without loading all into memory
- **FR-014**: System MUST handle log rotation during continuous export
- **FR-015**: System MUST display errors clearly for permission denied, disk full, and command not found scenarios
- **FR-016**: System MUST support `--since <time>` option to export only entries after a specified time
- **FR-017**: System MUST auto-create parent directories for export path if user has write permission

### Key Entities

- **LogEntry**: Represents a parsed log line with timestamp, level, pid, message, and raw_line. Already exists in the codebase.
- **ExportFormat**: Enumeration of supported output formats (text, json, csv)
- **ExportOptions**: Configuration for an export operation including filename, format, follow mode, append mode, and time filter

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can export 10,000+ log entries without noticeable delay or memory issues
- **SC-002**: All three export formats (text, json, csv) produce valid, parseable output that passes format validation
- **SC-003**: Exported files contain only entries matching the current filter state (level, regex, time)
- **SC-004**: Pipe operations work with common tools: grep, jq, wc, head, awk
- **SC-005**: Continuous export captures 100% of log entries during a test period with log rotation
- **SC-006**: Users receive clear feedback on export progress and completion (entry count, file path)
- **SC-007**: Error scenarios (permission denied, disk full, invalid command) produce actionable error messages

## Clarifications

### Session 2025-12-15

- Q: Should export auto-create parent directories or require they exist? → A: Auto-create parent directories if user has permission
- Q: What timestamp format should be used in JSON/CSV exports? → A: ISO 8601 format (e.g., 2024-01-15T10:23:45.123Z)

## Assumptions

- Users have write permissions to the directories where they export files
- The shell environment supports standard Unix process piping mechanisms
- Log entries in the buffer are stored in chronological order
- The existing LogEntry data structure contains all fields needed for export (timestamp, level, pid, message)
- Users understand basic shell command syntax for the pipe feature

## Out of Scope

- Cloud storage upload (S3, GCS, Azure Blob)
- Compression of exported files
- Scheduled or automatic exports
- Email export functionality
- Export templates or custom field selection
- Binary/custom output formats beyond text, json, csv
