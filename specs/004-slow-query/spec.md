# Feature Specification: Slow Query Detection and Highlighting

**Feature Branch**: `004-slow-query`
**Created**: 2025-12-15
**Status**: Draft
**Input**: User description: "Parse query duration from log entries and apply visual highlighting based on configurable thresholds. Slow queries get progressively more prominent colors (yellow → orange → red) based on severity."

## Clarifications

### Session 2025-12-15

- Q: When slow query highlighting and regex highlighting both match, how should they interact? → A: Replace - slow query color completely overrides regex highlight color

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual Slow Query Detection (Priority: P1)

A developer is tailing PostgreSQL logs to identify performance issues. While watching the log stream, they need to immediately spot queries that are taking longer than expected. Most log lines appear in the default color, but when a query exceeds their configured warning threshold, it appears in yellow. Critical slow queries (exceeding the critical threshold) appear in red with bold formatting, making them impossible to miss even when scrolling through high-volume output.

**Why this priority**: This is the core value proposition of the feature - visual identification of slow queries is the primary use case that all other functionality builds upon.

**Independent Test**: Can be fully tested by tailing a log file containing queries with varying durations and observing that queries exceeding thresholds are visually highlighted with appropriate colors.

**Acceptance Scenarios**:

1. **Given** pgtail is tailing a log with slow query highlighting enabled and default thresholds (100ms/500ms/1000ms), **When** a log entry contains "duration: 234.567 ms", **Then** the entire log line is displayed in yellow (warning level).

2. **Given** pgtail is tailing a log with slow query highlighting enabled and default thresholds, **When** a log entry contains "duration: 1234.567 ms", **Then** the entire log line is displayed in red with bold formatting (critical level).

3. **Given** pgtail is tailing a log with slow query highlighting enabled, **When** a log entry contains "duration: 50.123 ms" (below warning threshold), **Then** the log line is displayed in the default color with no special highlighting.

4. **Given** pgtail is tailing a log with slow query highlighting enabled, **When** a log entry contains "duration: 750.000 ms" (between slow and critical thresholds), **Then** the log line is displayed in orange (slow level).

---

### User Story 2 - Custom Threshold Configuration (Priority: P2)

A DBA working on a high-performance system needs more aggressive thresholds than the defaults. They configure custom thresholds to match their application's requirements - warning at 10ms, slow at 100ms, critical at 500ms. The system confirms their configuration and applies it immediately to the log stream.

**Why this priority**: Different environments have different performance expectations. Without customizable thresholds, the feature would have limited utility for many users.

**Independent Test**: Can be fully tested by configuring custom thresholds via the `slow` command and verifying that subsequent log entries are highlighted according to the new thresholds.

**Acceptance Scenarios**:

1. **Given** pgtail is running, **When** the user enters "slow 10 100 500", **Then** the system displays confirmation showing the three thresholds (warning: >10ms, slow: >100ms, critical: >500ms) and applies them immediately.

2. **Given** custom thresholds are configured (10/100/500), **When** a log entry contains "duration: 75.000 ms", **Then** the log line is displayed in yellow (exceeds 10ms warning but below 100ms slow threshold).

3. **Given** pgtail is running with slow query highlighting active, **When** the user enters "slow off", **Then** slow query highlighting is disabled and all subsequent duration entries appear in default colors.

4. **Given** pgtail is running with custom thresholds (10/100/500), **When** the user enters "slow" with no arguments, **Then** the system displays the current thresholds: "Current thresholds: 10ms / 100ms / 500ms".

---

### User Story 3 - Query Duration Statistics (Priority: P3)

A developer wants to understand the overall query performance distribution during their debugging session. They run a stats command and see a summary including total query count, average duration, and percentile breakdown (p50, p95, p99, max) for the queries observed during the session.

**Why this priority**: While valuable for analysis, statistics are secondary to the core real-time highlighting functionality. Users can work effectively with just highlighting; statistics provide additional insight.

**Independent Test**: Can be fully tested by tailing a log with various query durations, then running the `stats` command to verify accurate statistical calculations.

**Acceptance Scenarios**:

1. **Given** pgtail has observed 100 queries with durations during the current session, **When** the user enters "stats", **Then** the system displays: total count, average duration, p50 (median), p95, p99, and maximum duration.

2. **Given** pgtail has just started and no queries have been observed, **When** the user enters "stats", **Then** the system displays a message indicating no query duration data is available yet.

3. **Given** pgtail has observed queries over a period of time, **When** the user enters "stats", **Then** the statistics reflect only the queries observed since pgtail started (session-scoped, not historical).

---

### Edge Cases

- What happens when a log entry contains multiple "duration:" patterns? (Only the first valid duration pattern should be matched)
- What happens when duration value is malformed (e.g., "duration: abc ms")? (Line should be displayed without slow query highlighting)
- What happens when thresholds are set to invalid values (negative numbers, non-numeric, out of order)? (System should display an error and retain previous thresholds)
- What happens when log format uses different duration units (seconds vs milliseconds)? (System should handle both "duration: 1.234 s" and "duration: 1234.567 ms" formats)
- How does highlighting interact with existing regex filter highlighting? (Slow query highlighting completely replaces regex highlighting when both match the same line)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse duration values from PostgreSQL log entries that contain the pattern "duration: X.XXX ms" or "duration: X.XXX s"
- **FR-002**: System MUST support three configurable threshold levels: warning, slow, and critical
- **FR-003**: System MUST apply distinct visual styles for each threshold level (yellow for warning, orange for slow, red/bold for critical)
- **FR-004**: System MUST provide a `slow` command to configure thresholds with three numeric arguments (warning, slow, critical in milliseconds)
- **FR-005**: System MUST provide a `slow off` command to disable slow query highlighting
- **FR-006**: System MUST provide a `slow` command with no arguments to display current threshold configuration
- **FR-007**: System MUST persist threshold configuration for the duration of the session
- **FR-008**: System MUST validate that threshold values are positive numbers and in ascending order (warning < slow < critical)
- **FR-009**: System MUST collect duration data for statistical analysis during the session
- **FR-010**: System MUST provide a `stats` command to display query duration statistics (count, average, p50, p95, p99, max)
- **FR-011**: System MUST handle both `log_duration` and `log_min_duration_statement` output formats from PostgreSQL
- **FR-012**: System MUST NOT apply slow query highlighting to non-duration numeric values in log entries (avoiding false positives)
- **FR-013**: When a log line matches both slow query thresholds and an active regex filter, slow query highlighting MUST completely replace regex highlighting (no combined styling)

### Key Entities

- **SlowQueryConfig**: Configuration state for slow query detection including three threshold values (warning_ms, slow_ms, critical_ms) and enabled/disabled status
- **DurationStats**: Session-scoped collection of observed query durations for statistical analysis, including methods to calculate percentiles
- **DurationMatch**: Result of parsing a log line for duration information, containing the extracted duration value in milliseconds (or null if no duration found)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can identify slow queries within 1 second of visual scanning, compared to reading each line individually
- **SC-002**: 100% of valid PostgreSQL duration log entries are correctly parsed and highlighted according to configured thresholds
- **SC-003**: Zero false positives - no log lines are incorrectly highlighted as slow queries when they don't contain duration information
- **SC-004**: Threshold configuration is confirmed within 1 second of user input
- **SC-005**: Statistics command displays results within 500ms even after observing 10,000+ queries
- **SC-006**: Users can configure thresholds appropriate for their environment in under 10 seconds
- **SC-007**: Statistics provide actionable insights with percentile breakdown (p50, p95, p99) to identify distribution patterns

## Assumptions

- Default thresholds of 100ms (warning), 500ms (slow), and 1000ms (critical) are reasonable starting points for most PostgreSQL applications
- Session-scoped statistics (reset when pgtail restarts) are sufficient; historical persistence is out of scope
- Duration parsing only needs to handle standard PostgreSQL log formats (log_duration and log_min_duration_statement settings)
- When slow query highlighting and regex highlighting both match the same line, slow query highlighting completely replaces regex highlighting (no combined styling)
- Seconds format ("duration: X.XXX s") should be converted to milliseconds for threshold comparison
