# Feature Specification: Desktop Notifications for Alerts

**Feature Branch**: `011-desktop-notifications`
**Created**: 2025-12-17
**Status**: Draft
**Input**: User description: Desktop notification system for pgtail to alert users of critical log events, patterns, and threshold breaches

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Level-Based Notifications (Priority: P1)

A developer has pgtail running while writing code in another window. They want immediate awareness when critical errors (FATAL, PANIC) occur in PostgreSQL without constantly watching the log output.

**Why this priority**: This is the core use case - immediate awareness of critical database errors that require immediate attention. FATAL and PANIC errors can indicate database crashes or severe issues.

**Independent Test**: Can be fully tested by enabling notifications for FATAL/PANIC, triggering a FATAL error (e.g., connection limit exceeded), and verifying the desktop notification appears.

**Acceptance Scenarios**:

1. **Given** notifications are disabled, **When** user runs `notify on FATAL PANIC`, **Then** system confirms "Notifications enabled for: FATAL, PANIC"
2. **Given** notifications are enabled for FATAL, **When** a FATAL log entry appears, **Then** a desktop notification is displayed within 1 second showing level, message excerpt, and instance name
3. **Given** notifications are enabled for FATAL, **When** an ERROR log entry appears, **Then** no notification is sent
4. **Given** notifications are enabled, **When** user runs `notify off`, **Then** system confirms notifications are disabled and no further notifications are sent

---

### User Story 2 - Notification Rate Limiting (Priority: P1)

An ops engineer monitoring a system during an incident wants notifications but doesn't want to be overwhelmed when hundreds of errors occur in succession.

**Why this priority**: Without rate limiting, the notification system becomes unusable during incidents - exactly when it's needed most. This is essential for the feature to be practical.

**Independent Test**: Can be tested by triggering rapid errors and verifying notifications are throttled to 1 per 5 seconds maximum.

**Acceptance Scenarios**:

1. **Given** notifications are enabled for ERROR, **When** 50 ERROR entries occur within 5 seconds, **Then** at most 1 notification is shown (not 50)
2. **Given** rate limiting has suppressed notifications, **When** 5 seconds pass with no notifications, **Then** the next matching entry triggers a notification immediately
3. **Given** multiple notification rules are active, **When** entries match different rules rapidly, **Then** rate limiting applies globally (not per-rule)

---

### User Story 3 - Pattern-Based Notifications (Priority: P2)

A DBA wants to be alerted when specific patterns appear in logs, such as "deadlock detected" or "out of memory", regardless of log level.

**Why this priority**: Allows targeted monitoring for specific known issues. Builds on P1 foundation with more flexible matching.

**Independent Test**: Can be tested by enabling a pattern filter, generating log entries that match and don't match, and verifying correct notification behavior.

**Acceptance Scenarios**:

1. **Given** no pattern notifications, **When** user runs `notify on /deadlock detected/`, **Then** system confirms "Notifications enabled for pattern: deadlock detected"
2. **Given** pattern notification for "deadlock", **When** log entry contains "deadlock detected in process 1234", **Then** notification is displayed
3. **Given** pattern notification for "deadlock", **When** log entry contains "no deadlocks found", **Then** notification is displayed (substring match)
4. **Given** notifications disabled, **When** user runs `notify on /connection refused/i`, **Then** case-insensitive pattern matching is enabled

---

### User Story 4 - Rate-Based Threshold Notifications (Priority: P2)

An ops team wants to know when the error rate exceeds a threshold, indicating a systemic issue rather than isolated errors.

**Why this priority**: Detects patterns that individual error notifications miss. Requires the error tracking system already present in pgtail.

**Independent Test**: Can be tested by enabling rate threshold, generating errors at different rates, and verifying notifications only appear when threshold is exceeded.

**Acceptance Scenarios**:

1. **Given** no rate notifications, **When** user runs `notify on errors > 10/min`, **Then** system confirms "Notifications enabled: more than 10 errors per minute"
2. **Given** rate threshold of 10/min, **When** 11th error occurs within 1 minute, **Then** notification shows "Error rate exceeded: 11 errors/min"
3. **Given** rate threshold active and exceeded, **When** error rate drops below threshold, **Then** no "recovered" notification is sent (only alerts, no recovery notices)

---

### User Story 5 - Slow Query Notifications (Priority: P2)

A developer wants to be alerted when queries exceed a duration threshold, helping identify performance regressions as they occur.

**Why this priority**: Leverages existing slow query detection. Important for performance monitoring but not as critical as error alerts.

**Independent Test**: Can be tested by enabling slow query threshold, running queries of varying durations, and verifying notifications appear only for queries exceeding threshold.

**Acceptance Scenarios**:

1. **Given** no slow query notifications, **When** user runs `notify on slow > 500ms`, **Then** system confirms "Notifications enabled: queries slower than 500ms"
2. **Given** slow threshold of 500ms, **When** query completes in 600ms, **Then** notification shows query duration and excerpt
3. **Given** slow threshold of 500ms, **When** query completes in 400ms, **Then** no notification is sent

---

### User Story 6 - Quiet Hours (Priority: P3)

A developer wants notifications during work hours but not overnight when they're sleeping or on weekends.

**Why this priority**: Quality of life feature that prevents disturbance during off hours. Not essential for core functionality.

**Independent Test**: Can be tested by setting quiet hours, generating alerts during quiet period, and verifying no notifications appear.

**Acceptance Scenarios**:

1. **Given** no quiet hours, **When** user runs `notify quiet 22:00-08:00`, **Then** system confirms "Notifications silenced 22:00-08:00"
2. **Given** quiet hours 22:00-08:00, **When** FATAL error occurs at 23:00, **Then** no notification is displayed
3. **Given** quiet hours 22:00-08:00, **When** FATAL error occurs at 14:00, **Then** notification is displayed normally
4. **Given** quiet hours active, **When** user runs `notify quiet off`, **Then** quiet hours are disabled

---

### User Story 7 - Test and Status Commands (Priority: P3)

A user setting up notifications wants to verify their system can display notifications and check current configuration.

**Why this priority**: Debugging/verification feature. Important for setup but not core functionality.

**Independent Test**: Can be tested by running test command and verify notification appears, running status command and verify configuration is displayed.

**Acceptance Scenarios**:

1. **Given** any notification state, **When** user runs `notify test`, **Then** a test notification appears with "pgtail: Test" title
2. **Given** notifications configured, **When** user runs `notify`, **Then** current settings are displayed (enabled levels, patterns, thresholds, quiet hours)
3. **Given** notification system unavailable, **When** user runs `notify test`, **Then** error message explains what's missing (e.g., "notify-send not found")

---

### Edge Cases

- What happens when notification daemon/service is not running? Graceful degradation with warning message on first failure, silent skip on subsequent failures in same session.
- What happens when multiple notification rules match same entry? Single notification is sent (not one per rule) with most specific match.
- How does system handle very long log messages? Body is truncated to 200 characters with "..." suffix.
- What happens during time zone changes (DST)? Quiet hours use local system time, evaluated at notification time.
- What happens when user runs pgtail over SSH without display? Notification attempts fail gracefully with warning on first attempt.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support enabling notifications for specific log levels (DEBUG, INFO, NOTICE, WARNING, ERROR, FATAL, PANIC)
- **FR-002**: System MUST support enabling notifications for regex patterns in log messages
- **FR-003**: System MUST support enabling notifications when error rate exceeds N errors per minute
- **FR-004**: System MUST support enabling notifications when query duration exceeds N milliseconds
- **FR-005**: System MUST rate-limit notifications to maximum 1 per 5 seconds to prevent spam
- **FR-006**: System MUST support quiet hours with start and end times in HH:MM format
- **FR-007**: System MUST provide a test command to verify notification delivery
- **FR-008**: System MUST display current notification settings when `notify` is run without arguments
- **FR-009**: System MUST gracefully handle unavailable notification systems without crashing
- **FR-010**: System MUST display notifications within 1 second of matching log entry
- **FR-011**: System MUST persist notification settings to configuration file
- **FR-012**: System MUST support disabling all notifications with `notify off`
- **FR-013**: Notification body MUST be truncated to 200 characters maximum
- **FR-014**: System MUST work on macOS using native notification mechanisms
- **FR-015**: System MUST work on Linux using notify-send (libnotify) when available
- **FR-016**: System SHOULD work on Windows using available notification mechanisms (best effort)

### Key Entities

- **NotificationRule**: Represents a single notification condition (level match, pattern match, rate threshold, or slow query threshold)
- **NotificationConfig**: Collection of active rules plus quiet hours settings and enabled/disabled state
- **NotificationEvent**: A log entry that matched a rule and should trigger a notification (subject to rate limiting)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive desktop notifications within 1 second of matching log entries appearing
- **SC-002**: Notification spam is prevented - maximum 1 notification per 5-second window regardless of matching entry volume
- **SC-003**: System works correctly on macOS and Linux with standard desktop environments
- **SC-004**: Users can configure and verify notifications without technical knowledge of underlying notification systems
- **SC-005**: Quiet hours prevent 100% of notifications during configured periods
- **SC-006**: Test command provides clear pass/fail feedback about notification system availability
- **SC-007**: Notification settings persist across pgtail sessions

## Assumptions

- Users have a desktop environment with notification support (not headless servers)
- On Linux, libnotify/notify-send is the standard notification mechanism
- On macOS, osascript or terminal-notifier can be used for notifications
- Users understand HH:MM time format for quiet hours
- Rate limiting uses a simple time-based window (not sliding window)
- Pattern matching uses Python regex syntax

## Out of Scope

- Mobile push notifications
- Email/SMS alerts
- Webhook integrations (separate feature)
- Notification history/log
- Sound customization per rule
- Notification grouping/stacking
- Action buttons in notifications
