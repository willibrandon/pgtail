# Feature Specification: CSV and JSON Log Format Support

**Feature Branch**: `008-csv-json-log-format`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Add support for PostgreSQL CSV and JSON log formats with auto-detection, rich field display, and field-based filtering"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Auto-Detection of Log Format (Priority: P1)

A developer points pgtail at a PostgreSQL log file. Pgtail automatically detects whether it's a text (stderr), CSV, or JSON format log and begins parsing accordingly, without requiring manual format specification.

**Why this priority**: This is the foundation for all other features. Without format detection, users cannot benefit from structured log parsing. This enables zero-configuration usage which is critical for developer experience.

**Independent Test**: Can be fully tested by pointing pgtail at log files of each format and verifying correct detection and parsing without user intervention.

**Acceptance Scenarios**:

1. **Given** a PostgreSQL CSV log file, **When** the user runs `tail <id>`, **Then** pgtail detects "csvlog" format and parses all CSV fields correctly
2. **Given** a PostgreSQL JSON log file (PG15+), **When** the user runs `tail <id>`, **Then** pgtail detects "jsonlog" format and parses all JSON fields correctly
3. **Given** a standard text log file, **When** the user runs `tail <id>`, **Then** pgtail continues using existing text parsing (backward compatible)
4. **Given** an empty or new log file, **When** the user starts tailing, **Then** pgtail waits for content and detects format from the first entry

---

### User Story 2 - Rich Error Display (Priority: P2)

When viewing CSV or JSON logs, developers see enhanced error information including SQL state codes, application name, query text, and source code location - information not available in text logs.

**Why this priority**: This delivers the primary value proposition of structured logs - more diagnostic information. Once detection works, users immediately benefit from richer output.

**Independent Test**: Can be tested by generating errors in PostgreSQL with csvlog/jsonlog enabled and verifying all relevant fields appear in pgtail output.

**Acceptance Scenarios**:

1. **Given** a CSV log with an ERROR entry, **When** displayed in compact mode, **Then** the output shows timestamp, PID, level, SQL state code, and message on one line
2. **Given** a CSV log with an ERROR entry, **When** displayed in full mode, **Then** all available fields (application, query, location, detail, hint, context) appear on separate lines
3. **Given** a JSON log entry, **When** parsed and displayed, **Then** the same information is available as CSV format
4. **Given** a log entry with DETAIL or HINT fields populated, **When** displayed, **Then** these supplementary fields are shown to help with debugging

---

### User Story 3 - Display Mode Control (Priority: P2)

Developers can switch between different display modes: compact (one line per entry), full (all fields), or custom field selection to show exactly the information they need.

**Why this priority**: Different debugging scenarios require different levels of detail. This allows users to customize output density without losing access to full data.

**Independent Test**: Can be tested by switching display modes during an active tail session and verifying output format changes accordingly.

**Acceptance Scenarios**:

1. **Given** pgtail is tailing a structured log, **When** user runs `display compact`, **Then** each entry shows on one line with key fields only
2. **Given** pgtail is in full display mode, **When** user runs `display full`, **Then** all available fields from the log format are shown with labels
3. **Given** a user wants specific fields, **When** they run `display fields timestamp,level,application_name,message`, **Then** only those fields appear in output
4. **Given** an invalid field name in display fields, **When** the user runs the command, **Then** an error lists valid field names for the current log format

---

### User Story 4 - Field-Based Filtering (Priority: P3)

Developers can filter log entries by any available field value, such as application name, database name, or user name - capabilities only available with structured log formats.

**Why this priority**: Filtering by fields like application or database is powerful but requires the other features to be in place first. This extends the value of structured parsing.

**Independent Test**: Can be tested by generating logs from multiple applications/databases and verifying filters show only matching entries.

**Acceptance Scenarios**:

1. **Given** a CSV/JSON log with multiple applications, **When** user runs `filter app=myapp`, **Then** only entries from "myapp" are displayed
2. **Given** a structured log, **When** user runs `filter db=production`, **Then** only entries for database "production" are shown
3. **Given** a structured log, **When** user runs `filter user=admin`, **Then** only entries from user "admin" are displayed
4. **Given** a text format log, **When** user attempts field filtering, **Then** an informative message explains field filtering requires CSV or JSON format
5. **Given** multiple filters active, **When** user runs `filter app=myapp db=prod`, **Then** entries must match ALL filter conditions (AND logic)
6. **Given** active filters, **When** user runs `filter clear`, **Then** all field filters are removed

---

### User Story 5 - JSON Output Mode (Priority: P3)

Developers can output log entries as JSON for piping to other tools (jq, log aggregators, etc.) enabling integration with existing log processing pipelines.

**Why this priority**: This enables integration with external tooling but is not core to the primary use case of interactive log viewing. Important for power users and automation.

**Independent Test**: Can be tested by piping pgtail output to jq and verifying valid JSON structure with all expected fields.

**Acceptance Scenarios**:

1. **Given** pgtail is tailing any log format, **When** user runs `output json`, **Then** each entry outputs as a complete JSON object on one line
2. **Given** JSON output mode active, **When** entries are displayed, **Then** timestamps are ISO 8601 format and all available fields are included
3. **Given** JSON output mode, **When** piped to `jq`, **Then** the output is valid JSON that jq can process
4. **Given** JSON output mode active, **When** user runs `output text`, **Then** output returns to human-readable format

---

### Edge Cases

- What happens when a CSV log line is malformed (wrong number of fields)? Display raw line with a warning indicator.
- How does the system handle mixed format files (shouldn't happen but could)? Use detected format and show parse warnings for mismatched lines.
- What happens when JSON log has unexpected/custom fields? Parse known fields and preserve extras in an "other" category.
- How does pgtail handle log rotation from text to CSV format mid-session? Re-detect format when file changes and notify user.
- What happens with very long field values (e.g., huge queries)? Truncate in compact mode with indicator, show full in full mode.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST auto-detect log format (text, CSV, JSON) by examining file content
- **FR-002**: System MUST parse all 26 standard PostgreSQL csvlog fields (log_time through query_id)
- **FR-003**: System MUST parse all standard PostgreSQL jsonlog fields (PostgreSQL 15+)
- **FR-004**: System MUST fall back gracefully when encountering malformed entries, displaying raw content with warning
- **FR-005**: System MUST maintain backward compatibility with existing text log parsing
- **FR-006**: System MUST support `display compact` mode showing key fields on one line
- **FR-007**: System MUST support `display full` mode showing all available fields
- **FR-008**: System MUST support `display fields <list>` for custom field selection
- **FR-009**: System MUST support field-based filtering with syntax `filter <field>=<value>`
- **FR-010**: System MUST support multiple simultaneous field filters (AND logic)
- **FR-011**: System MUST provide `filter clear` command to remove all field filters
- **FR-012**: System MUST support `output json` mode for machine-readable output
- **FR-013**: System MUST support `output text` to return to human-readable display
- **FR-014**: System MUST show informative errors when field filtering is attempted on text logs
- **FR-015**: Existing level filtering, regex filtering, and time filtering MUST continue to work with all formats
- **FR-016**: System MUST handle log file rotation and re-detect format when file changes

### Key Entities

- **LogEntry**: Represents a single parsed log entry with all available fields. For text logs, contains timestamp, level, pid, and message. For CSV/JSON logs, contains all 26+ standard PostgreSQL fields.
- **LogFormat**: Enumeration of supported formats: TEXT, CSV, JSON. Determines parsing strategy and available fields.
- **DisplayMode**: Controls output formatting: COMPACT (single line), FULL (all fields), CUSTOM (user-selected fields).
- **FieldFilter**: A filter condition with field name, operator (equals), and value. Multiple filters combine with AND logic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Format detection completes within 100ms of first log entry arrival
- **SC-002**: All 26 standard PostgreSQL csvlog fields are parsed and accessible
- **SC-003**: All standard PostgreSQL jsonlog fields (PG15+) are parsed and accessible
- **SC-004**: Malformed entries display gracefully without crashing or losing subsequent entries
- **SC-005**: Field filtering reduces displayed entries to only those matching criteria
- **SC-006**: JSON output mode produces valid JSON parseable by standard tools
- **SC-007**: Display mode changes take effect immediately on next entry
- **SC-008**: Performance remains comparable to text parsing (less than 2x overhead for structured parsing)
- **SC-009**: Existing text log functionality works identically after this feature is added
- **SC-010**: Users can identify application source of errors in under 5 seconds with structured logs

## Assumptions

- PostgreSQL CSV log format follows the documented 26-field structure (may vary slightly by version)
- PostgreSQL JSON log format follows the documented structure for PostgreSQL 15+
- Log files use UTF-8 encoding
- Field filters use exact string matching (case-sensitive) as default behavior
- Display mode preference is session-only (not persisted to config) unless user explicitly saves
