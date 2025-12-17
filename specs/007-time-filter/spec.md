# Feature Specification: Time-Based Filtering

**Feature Branch**: `007-time-filter`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Add time-based filtering to show only log entries within a specified time range. Support relative times ('last 5m'), absolute times ('since 14:30'), and ranges ('between 14:30 and 15:00')."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recent History Investigation (Priority: P1)

A developer has just observed an error in their application and wants to see logs from the last few minutes to understand the context and root cause.

**Why this priority**: This is the most common use case - investigating issues that just happened. Most debugging sessions start with "what happened in the last N minutes?"

**Independent Test**: Can be fully tested by running `since 5m` command and verifying that only log entries from the last 5 minutes are displayed, delivering immediate value for recent issue investigation.

**Acceptance Scenarios**:

1. **Given** a log file with entries spanning several hours, **When** user types `since 5m`, **Then** only entries from the last 5 minutes are displayed with clear feedback showing the time range.
2. **Given** a log file with entries, **When** user types `since 30s`, **Then** only entries from the last 30 seconds are displayed.
3. **Given** a log file with entries, **When** user types `since 2h`, **Then** only entries from the last 2 hours are displayed.
4. **Given** a log file with entries, **When** user types `since 1d`, **Then** only entries from the last 24 hours are displayed.
5. **Given** no entries exist within the specified time range, **When** user types `since 5m`, **Then** system displays a message indicating no entries found in that time period.

---

### User Story 2 - Specific Time Window Investigation (Priority: P1)

An on-call engineer receives an alert that fired at a specific time (e.g., 3:47am) and needs to examine logs around that exact time to diagnose the issue.

**Why this priority**: Critical for incident response. Engineers often know exactly when an issue occurred from alerts/monitoring and need to jump directly to that time.

**Independent Test**: Can be fully tested by running `since 03:45` command and verifying that logs from the specified time onward are displayed.

**Acceptance Scenarios**:

1. **Given** a log file with entries throughout the day, **When** user types `since 14:30`, **Then** entries from 14:30:00 today onward are displayed.
2. **Given** a log file with entries, **When** user types `since 14:30:45`, **Then** entries from that exact time (with seconds precision) onward are displayed.
3. **Given** a log file with entries from multiple days, **When** user types `since 2024-01-15T14:30`, **Then** entries from that specific date and time onward are displayed.
4. **Given** the current time is 10:00, **When** user types `since 11:00` (future time today), **Then** system displays a warning that the time is in the future and no entries will match.

---

### User Story 3 - Time Range Investigation (Priority: P2)

A developer needs to examine logs between two specific times - for example, between a deployment start and a rollback - to understand what happened during that window.

**Why this priority**: Important for bounded investigations but less common than "since X" queries. Requires both start and end time to be known.

**Independent Test**: Can be fully tested by running `between 14:30 15:00` command and verifying only entries within that 30-minute window are displayed.

**Acceptance Scenarios**:

1. **Given** a log file with entries spanning several hours, **When** user types `between 14:30 15:00`, **Then** only entries between 14:30:00 and 15:00:00 are displayed.
2. **Given** a log file with entries, **When** user types `between 2024-01-15T09:00 2024-01-15T10:00`, **Then** only entries within that specific hour on that date are displayed.
3. **Given** start time is after end time, **When** user types `between 15:00 14:00`, **Then** system displays an error indicating the invalid time range.

---

### User Story 4 - Upper Bound Filtering (Priority: P2)

A developer wants to see all logs up until a specific time, useful for examining what happened before an event.

**Why this priority**: Useful complement to `since` but less commonly needed. Most investigations focus on "what happened after X" rather than "what happened before X".

**Independent Test**: Can be fully tested by running `until 15:00` command and verifying only entries before that time are shown.

**Acceptance Scenarios**:

1. **Given** a log file with entries throughout the day, **When** user types `until 15:00`, **Then** only entries before 15:00:00 are displayed and tailing stops (no follow mode).
2. **Given** a log file with entries, **When** user types `until 30m`, **Then** entries up to 30 minutes ago are displayed (relative time interpreted as "until N ago").

---

### User Story 5 - Time Filter with Live Tail (Priority: P2)

A developer wants to start tailing from a specific point in time, showing historical entries first and then continuing to follow new entries.

**Why this priority**: Combines time filtering with live tailing for continuous monitoring from a point in history.

**Independent Test**: Can be fully tested by running tail with `--since 10m` flag and verifying historical entries are shown first, then new entries continue to appear.

**Acceptance Scenarios**:

1. **Given** an active PostgreSQL instance generating logs, **When** user starts tail with `--since 10m`, **Then** logs from the last 10 minutes are displayed first, followed by continuous tailing of new entries.
2. **Given** time filter is active, **When** new log entries arrive, **Then** new entries are displayed if they fall within the time filter (for `since`) or are newer than the start time.

---

### User Story 6 - Clear Time Filter (Priority: P3)

A developer has been investigating with a time filter and wants to return to viewing all logs or resume normal tailing.

**Why this priority**: Utility feature to reset state. Important for workflow but not core functionality.

**Independent Test**: Can be fully tested by setting a time filter, then running `since clear` and verifying all logs are shown again.

**Acceptance Scenarios**:

1. **Given** a time filter is active showing only recent entries, **When** user types `since clear`, **Then** the time filter is removed and all log entries are displayed.
2. **Given** a time filter is active, **When** user types `since clear`, **Then** feedback confirms the filter was removed.

---

### User Story 7 - Combined Filtering (Priority: P3)

A developer wants to use time filtering together with existing level and regex filters to narrow down to specific error patterns within a time window.

**Why this priority**: Advanced use case combining multiple filter types. Powerful but relies on other features working correctly first.

**Independent Test**: Can be fully tested by setting level filter to ERROR, regex filter for a pattern, and time filter, then verifying only matching entries within the time window are shown.

**Acceptance Scenarios**:

1. **Given** level filter is set to ERROR, **When** user types `since 1h`, **Then** only ERROR level entries from the last hour are displayed.
2. **Given** regex filter is active for "connection", **When** user types `between 14:00 15:00`, **Then** only entries matching "connection" within that hour are displayed.
3. **Given** multiple filters active, **When** user views status, **Then** all active filters including time filter are shown.

---

### Edge Cases

- What happens when log file has entries with unparseable timestamps? System should skip entries without valid timestamps and continue processing, optionally warning about skipped entries.
- How does system handle timezone differences between log file timestamps and user input? System assumes local timezone for both unless Z suffix is provided for UTC.
- What happens when log file is rotated during time-filtered viewing? System should handle rotation gracefully, continuing from the new file if entries fall within the time range.
- What happens when no log entries exist in the specified time range? Display informative message with the time range searched.
- How are midnight boundary crossings handled? Times like "23:30" should refer to today's 23:30, not tomorrow's.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse relative time formats with suffixes: s (seconds), m (minutes), h (hours), d (days).
- **FR-002**: System MUST parse absolute time formats: HH:MM, HH:MM:SS for today's date.
- **FR-003**: System MUST parse date-time formats: YYYY-MM-DDTHH:MM and ISO 8601 (YYYY-MM-DDTHH:MM:SSZ).
- **FR-004**: System MUST provide `since <time>` command to show entries from the specified time onward.
- **FR-005**: System MUST provide `until <time>` command to show entries up to the specified time.
- **FR-006**: System MUST provide `between <start> <end>` command to show entries within a time range.
- **FR-007**: System MUST provide `since clear` command to remove active time filters.
- **FR-008**: System MUST display clear feedback showing the active time range when a time filter is set.
- **FR-009**: System MUST combine time filters with existing level filters (ERROR, WARNING, etc.).
- **FR-010**: System MUST combine time filters with existing regex pattern filters.
- **FR-011**: System MUST gracefully handle log entries that lack parseable timestamps.
- **FR-012**: System MUST provide meaningful error messages for invalid time formats or ranges.
- **FR-013**: System MUST warn users when specified time is in the future.
- **FR-014**: System MUST interpret times without timezone as local timezone.
- **FR-015**: System MUST interpret times with Z suffix as UTC.
- **FR-016**: System MUST support `--since` flag on the tail command for starting tail from a specific time.

### Key Entities

- **TimeFilter**: Represents an active time-based filter with optional start time, optional end time, and the original user input string for display purposes.
- **ParsedTime**: Represents a parsed time value that could be relative (duration from now) or absolute (specific datetime), with methods to resolve to an actual datetime.
- **LogEntry timestamp**: The existing timestamp field in LogEntry dataclass used for time comparisons.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can filter logs to a specific time window with a single command.
- **SC-002**: Relative time parsing correctly interprets all supported suffixes (s, m, h, d) with numeric values.
- **SC-003**: Absolute time parsing correctly handles HH:MM, HH:MM:SS, YYYY-MM-DDTHH:MM, and full ISO 8601 formats.
- **SC-004**: Time filters work correctly in combination with level filters and regex filters simultaneously.
- **SC-005**: Users receive clear feedback indicating the active time range.
- **SC-006**: Invalid time inputs produce helpful error messages guiding correct usage.
- **SC-007**: Performance remains responsive when filtering large log files (seeking should avoid full file scan where possible).
- **SC-008**: All existing pgtail functionality continues to work correctly when no time filter is active.

## Assumptions

- Log files contain timestamps in a parseable format that the existing parser can extract.
- The PostgreSQL log_line_prefix configuration includes timestamp information.
- Users are familiar with common time notation conventions (24-hour format, ISO 8601).
- Binary search optimization for large files is a nice-to-have but not required for initial implementation if log structure doesn't support it.

## Out of Scope

- Timezone conversion commands (users must know their timezone)
- Calendar or date picker UI
- Log file archival or retrieval from rotated/archived files
- Persistent time filter settings in configuration
