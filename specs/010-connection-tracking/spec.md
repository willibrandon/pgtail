# Feature Specification: Connection Tracking Dashboard

**Feature Branch**: `010-connection-tracking`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: "Track connection events (connect/disconnect) and provide a dashboard view showing active connections aggregated by user, database, application, and source IP."

## Clarifications

### Session 2025-12-17

- Q: What is the maximum number of connection events to retain in memory? → A: 10,000 events (matches existing error_stats pattern)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Connection Summary (Priority: P1)

A DBA wants to see the current state of connections to their PostgreSQL instance without querying the database directly. They run `connections` in pgtail to see total active connections and breakdowns by database, user, and application.

**Why this priority**: This is the core value proposition - providing visibility into connection distribution from log data alone. All other features build on this foundation.

**Independent Test**: Can be fully tested by tailing a log file with connection events and verifying the summary shows accurate counts by each dimension.

**Acceptance Scenarios**:

1. **Given** pgtail is tailing a log with connection/disconnection events, **When** user runs `connections`, **Then** displays total active connections and counts grouped by database, user, and application
2. **Given** no connection events have been tracked yet, **When** user runs `connections`, **Then** displays a message indicating no connection data is available
3. **Given** multiple connections from same application, **When** user views summary, **Then** application is counted once with total connection count

---

### User Story 2 - Connection History and Trend Analysis (Priority: P2)

A developer investigating a potential connection leak wants to see how connection counts have changed over time. They run `connections --history` to see connect/disconnect totals and a timeline showing when connections increased.

**Why this priority**: History enables root cause analysis for connection issues, which is a common operational need. Depends on P1's tracking foundation.

**Independent Test**: Can be tested by generating a sequence of connection events over time and verifying the history shows accurate trends and net changes.

**Acceptance Scenarios**:

1. **Given** connection events spanning the last hour, **When** user runs `connections --history`, **Then** displays total connects, disconnects, net change, and timeline of active connection counts
2. **Given** connections increasing without corresponding disconnections, **When** viewing history, **Then** trend clearly shows the accumulation pattern indicating potential leak
3. **Given** history data exists, **When** user views timeline, **Then** timestamps are shown at configurable intervals (default 15-minute buckets)

---

### User Story 3 - Watch Live Connection Events (Priority: P2)

A developer wants to monitor their specific application's connection behavior in real-time. They run `connections --watch app=myapp` to see a live stream of connection and disconnection events for their application.

**Why this priority**: Real-time monitoring is valuable for active debugging sessions. Equal priority to history since both serve different investigation workflows.

**Independent Test**: Can be tested by watching connections while generating new connection events and verifying they appear in real-time with correct details.

**Acceptance Scenarios**:

1. **Given** user starts `connections --watch`, **When** new connection events occur, **Then** each event appears immediately with direction indicator ([+] connect, [-] disconnect)
2. **Given** user specifies `--watch app=myapp`, **When** connection events occur, **Then** only events for application "myapp" are displayed
3. **Given** watch mode is active, **When** user presses Ctrl+C, **Then** watch mode exits cleanly and returns to prompt

---

### User Story 4 - Filter Connections by Criteria (Priority: P3)

A DBA troubleshooting issues with a specific database or user wants to filter the connection summary to show only relevant connections. They use flags like `--db=production` or `--user=app_user` to narrow the view.

**Why this priority**: Filtering enables focused analysis but the base summary (P1) provides value without it.

**Independent Test**: Can be tested by having connections from multiple databases/users and verifying filters correctly narrow the displayed results.

**Acceptance Scenarios**:

1. **Given** connections from multiple databases, **When** user runs `connections --db=production`, **Then** only connections to "production" database are counted
2. **Given** user specifies multiple filters `--user=admin --db=test`, **When** viewing connections, **Then** results match all specified criteria (AND logic)
3. **Given** filter matches no connections, **When** viewing filtered results, **Then** displays message indicating no matching connections found

---

### Edge Cases

- What happens when connection events occur faster than they can be processed? (Events stored in deque with maxlen=10,000; oldest events discarded when limit reached)
- How does the system handle log rotation during tracking? (New log file should be picked up automatically; connection state persists)
- What happens when a "disconnection" is logged without a matching "connection received"? (Track it as a standalone event; don't fail)
- How does the system handle truncated or malformed connection log messages? (Skip malformed entries with warning; continue processing)
- What happens when application_name is not set? (Display as "unknown" in aggregations)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse "connection received" log messages to extract host and port
- **FR-002**: System MUST parse "connection authorized" log messages to extract user, database, and application_name
- **FR-003**: System MUST parse "disconnection" log messages to extract session duration
- **FR-004**: System MUST track active connection count (connections minus disconnections)
- **FR-005**: System MUST aggregate connections by database name, user name, and application name
- **FR-006**: System MUST maintain a history of connection events for trend analysis (session-scoped, in-memory)
- **FR-007**: System MUST support filtering displayed connections by database, user, and application
- **FR-008**: System MUST provide a live watch mode showing connection events in real-time
- **FR-009**: System MUST handle "too many connections" and "connection limit exceeded" FATAL messages
- **FR-010**: System MUST work with default PostgreSQL log settings (no special configuration required)
- **FR-011**: System MUST support source IP tracking from "connection received" messages
- **FR-012**: System MUST clear/reset connection statistics on user request

### Key Entities

- **ConnectionEvent**: Represents a single connection or disconnection event. Contains timestamp, event type (connect/disconnect), user, database, application_name, host, port, and session duration (for disconnections).
- **ConnectionStats**: Aggregator for connection metrics. Tracks active count, connection history (max 10,000 events), and provides breakdowns by dimension.
- **ConnectionFilter**: Criteria for filtering connections (database, user, application, time range).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Connection summary displays within 1 second even with 10,000+ tracked events
- **SC-002**: Users can identify connection distribution by database, user, and application in a single command
- **SC-003**: History view shows connection trends with at least 15-minute granularity over the past hour
- **SC-004**: Watch mode displays new connection events within 500ms of log entry appearance
- **SC-005**: Connection tracking works without requiring any PostgreSQL configuration changes
- **SC-006**: System correctly correlates 95%+ of disconnection events with their corresponding connections when session info is available

## Assumptions

- PostgreSQL logs connection events at LOG level by default (log_connections and log_disconnections may need to be enabled)
- Connection events contain PID which can be used to correlate connects and disconnects
- Application name is optional and may be empty or unset for some connections
- Log format detection (TEXT/CSV/JSON) is already handled by existing pgtail infrastructure
- Session-scoped tracking is sufficient; persistence across pgtail restarts is not required

## Out of Scope

- Querying pg_stat_activity directly (log-based tracking only)
- Connection pooler (pgbouncer, pgpool) awareness
- Killing or managing connections
- Connection limits or alerting thresholds
- Historical persistence beyond current session
