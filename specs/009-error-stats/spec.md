# Feature Specification: Error Statistics Dashboard

**Feature Branch**: `009-error-stats`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Track error events and provide a dashboard showing error statistics, trends, and breakdowns by type. Support both point-in-time summaries and live updating views."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Error Summary View (Priority: P1)

A developer investigating reports of issues wants to quickly understand the current error landscape without scrolling through logs. They run a single command and see a summary showing error counts, breakdowns by error type (SQLSTATE), and breakdowns by severity level.

**Why this priority**: This is the core value proposition - giving users immediate visibility into error patterns. Without this, the feature has no foundation.

**Independent Test**: Can be fully tested by generating errors in a test database, running the `errors` command, and verifying the output shows accurate counts and breakdowns.

**Acceptance Scenarios**:

1. **Given** the user is tailing a PostgreSQL log with errors, **When** they run `errors`, **Then** they see a summary showing total errors and warnings in the last hour
2. **Given** errors with different SQLSTATE codes exist, **When** they run `errors`, **Then** they see a "By type" breakdown with error codes, descriptions, and occurrence counts sorted by frequency
3. **Given** errors at different severity levels exist (ERROR, FATAL, WARNING), **When** they run `errors`, **Then** they see a "By level" breakdown with counts per level
4. **Given** no errors have occurred in the session, **When** they run `errors`, **Then** they see a message indicating no errors recorded

---

### User Story 2 - Error Trend Visualization (Priority: P2)

A DBA wants to check if a recent deployment caused an increase in errors. They view an error rate trend over time to identify spikes and correlate them with deployment timing.

**Why this priority**: Trend analysis helps identify patterns and correlate errors with events, but requires the base tracking from P1 to be functional first.

**Independent Test**: Can be tested by generating errors at varying rates over time, running `errors --trend`, and verifying the visualization accurately reflects the error rate changes.

**Acceptance Scenarios**:

1. **Given** errors have occurred over the past hour, **When** they run `errors --trend`, **Then** they see a time-bucketed visualization showing error rate per minute
2. **Given** a spike in errors occurred at a specific time, **When** they run `errors --trend`, **Then** the spike is visually distinguishable and annotated with the approximate time
3. **Given** the terminal has limited width, **When** they run `errors --trend`, **Then** the visualization fits within terminal width and remains readable

---

### User Story 3 - Live Error Counter (Priority: P2)

An ops engineer monitoring during a deployment wants to see real-time error counts without log lines scrolling. They need an in-place updating display that shows current error state.

**Why this priority**: Live monitoring is critical for deployment scenarios but builds on the same tracking infrastructure as P1.

**Independent Test**: Can be tested by starting live mode, generating errors, and verifying the counter updates in place without scrolling.

**Acceptance Scenarios**:

1. **Given** the user runs `errors --live`, **When** new errors occur, **Then** the display updates in place showing current error count, warning count, and time since last error
2. **Given** the user is in live mode, **When** they press Ctrl+C or a designated key, **Then** live mode exits cleanly and returns to the command prompt
3. **Given** no new errors occur, **When** the user is in live mode, **Then** the "time since last error" continues to update

---

### User Story 4 - Filter by Error Code (Priority: P3)

A developer seeing many unique constraint violations wants to investigate a specific error type. They filter errors by SQLSTATE code to see details and recent examples of that specific error.

**Why this priority**: Detailed investigation is valuable but requires the base tracking and likely comes after understanding the overall picture.

**Independent Test**: Can be tested by generating multiple error types, running `errors --code 23505`, and verifying only matching errors are shown with recent examples.

**Acceptance Scenarios**:

1. **Given** multiple error types exist, **When** they run `errors --code 23505`, **Then** they see only the count and details for unique_violation errors
2. **Given** a specific error code filter is applied, **When** viewing results, **Then** recent examples are shown with timestamp, message excerpt, and relevant context
3. **Given** an invalid or non-existent error code is provided, **When** they run `errors --code XXXXX`, **Then** they see a message indicating no errors match that code

---

### User Story 5 - Time-Scoped Statistics (Priority: P3)

A developer wants to see error statistics for a specific time window, not just the default rolling window. They use the `--since` flag to narrow the time range.

**Why this priority**: Time scoping enhances the base functionality but isn't required for core value delivery.

**Independent Test**: Can be tested by generating errors across time periods, running `errors --since 30m`, and verifying only errors from the specified window are counted.

**Acceptance Scenarios**:

1. **Given** errors exist across the past 2 hours, **When** they run `errors --since 30m`, **Then** only errors from the last 30 minutes are included in statistics
2. **Given** time-based filtering is applied, **When** viewing the summary, **Then** the time window is clearly displayed in the output

---

### User Story 6 - Reset Counters (Priority: P3)

After investigating an issue, a user wants to start fresh with a clean slate for ongoing monitoring. They reset the error counters to begin tracking from that point forward.

**Why this priority**: Counter management is a convenience feature that enhances usability but isn't core functionality.

**Independent Test**: Can be tested by accumulating errors, running `errors clear`, then verifying subsequent `errors` shows zero counts.

**Acceptance Scenarios**:

1. **Given** errors have been accumulated, **When** they run `errors clear`, **Then** all counters are reset to zero
2. **Given** counters were cleared, **When** new errors occur, **Then** they are tracked starting from the reset point

---

### Edge Cases

- What happens when the log format doesn't include SQLSTATE codes? Display "Unknown" category and note that error code breakdown requires structured log formats
- How does the system handle extremely high error rates (thousands per minute)? Memory is bounded using a sliding window; oldest entries are dropped when limit reached
- What happens when the user hasn't started tailing yet? Display message indicating error tracking requires an active tail session
- How are multi-line error messages handled? The message field shows the primary error line; full details available via `--code` filter
- What if errors occur faster than display can update in live mode? Batch updates at reasonable interval (e.g., 100ms) to prevent flicker

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST track all log entries with levels ERROR, FATAL, PANIC, and WARNING during an active tail session
- **FR-002**: System MUST parse SQLSTATE codes from log entries when available (present in CSV/JSON log formats, parsed from message in text format)
- **FR-003**: System MUST provide an `errors` command that displays error summary for the current session
- **FR-004**: System MUST display error breakdown by SQLSTATE code with human-readable descriptions for common codes
- **FR-005**: System MUST display error breakdown by severity level (ERROR, FATAL, PANIC, WARNING)
- **FR-006**: System MUST support `errors --trend` to show error rate visualization over time
- **FR-007**: System MUST support `errors --live` for real-time updating error counter display
- **FR-008**: System MUST support `errors --code <SQLSTATE>` to filter statistics by specific error code
- **FR-009**: System MUST support `errors --since <time>` to scope statistics to a time window
- **FR-010**: System MUST support `errors clear` to reset all counters
- **FR-011**: System MUST bound memory usage with a sliding window approach, retaining recent errors up to a configurable limit
- **FR-012**: System MUST group SQLSTATE codes by category (Class 23, 42, 53, 57, 58) for high-level overview
- **FR-013**: System MUST persist error statistics across commands within the same session (session-scoped, not persisted to disk)

### Key Entities

- **ErrorEvent**: Represents a tracked error occurrence with timestamp, level, SQLSTATE code, message excerpt, and source log entry metadata
- **ErrorStatistics**: Aggregated statistics including counts by level, counts by SQLSTATE, time-series data for trend visualization
- **SQLStateCategory**: Grouping of SQLSTATE codes by class (e.g., "23" = Integrity Constraint Violation) with human-readable names

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view error summary within 1 second of running the `errors` command
- **SC-002**: Error tracking adds less than 5% overhead to log tailing performance
- **SC-003**: Memory usage for error tracking remains bounded regardless of session duration (configurable limit, default reasonable for typical sessions)
- **SC-004**: Live mode updates display within 500ms of new errors occurring
- **SC-005**: Trend visualization accurately reflects error rate patterns, with spikes clearly identifiable
- **SC-006**: Users can identify the most frequent error type within 10 seconds of viewing the summary
- **SC-007**: All common SQLSTATE codes (Class 23, 42, 53, 57, 58) display human-readable descriptions

## Assumptions

- Error tracking begins when a tail session starts; historical log analysis is out of scope
- SQLSTATE code descriptions will cover the most common PostgreSQL error codes; rare codes may show the raw code only
- The sliding window for memory bounding will retain the most recent N errors (default: 10,000) which covers typical debugging sessions
- Live mode display will use terminal control sequences for in-place updates; terminals without support will fall back to scrolling output
- Integration with existing time filter parsing (`--since`) from the time_filter module

## Out of Scope

- Persistent storage of statistics across sessions
- Alerting or notifications based on error thresholds
- Comparison between different time periods
- Error correlation or root cause analysis
- Exporting error statistics to external formats
