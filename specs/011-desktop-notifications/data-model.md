# Data Model: Desktop Notifications for Alerts

**Feature**: 011-desktop-notifications
**Date**: 2025-12-17

## Entities

### NotificationRuleType

Enumeration of notification trigger types.

```
NotificationRuleType
├── LEVEL      # Trigger on specific log levels
├── PATTERN    # Trigger on regex pattern match
├── ERROR_RATE # Trigger when errors/min exceeds threshold
└── SLOW_QUERY # Trigger when query duration exceeds threshold
```

### NotificationRule

A single notification condition. Multiple rules can be active simultaneously.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| rule_type | NotificationRuleType | Type of rule | Required |
| levels | set[LogLevel] | Levels to match | Only for LEVEL type |
| pattern | re.Pattern | Compiled regex | Only for PATTERN type |
| pattern_str | str | Original pattern string | For display/persistence |
| case_sensitive | bool | Pattern case sensitivity | Default: True |
| error_threshold | int | Errors per minute | Only for ERROR_RATE type |
| slow_threshold_ms | int | Query duration in ms | Only for SLOW_QUERY type |

**Validation Rules**:
- LEVEL rules must have non-empty `levels`
- PATTERN rules must have valid compiled `pattern`
- ERROR_RATE rules must have `error_threshold > 0`
- SLOW_QUERY rules must have `slow_threshold_ms > 0`

### NotificationConfig

Collection of active notification rules and settings.

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| enabled | bool | Master enable/disable | False |
| rules | list[NotificationRule] | Active rules | [] |
| quiet_start | time | Quiet hours start | None |
| quiet_end | time | Quiet hours end | None |

**Relationships**:
- Contains 0..* NotificationRule
- Persisted to config.toml under `[notifications]` section

### QuietHours

Time range during which notifications are suppressed.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| start | time | Start time (HH:MM) | 00:00 to 23:59 |
| end | time | End time (HH:MM) | 00:00 to 23:59 |

**State Transitions**:
- **Active**: current time is within start-end range (handles overnight spans)
- **Inactive**: current time is outside range

**Overnight Handling**: If start > end (e.g., 22:00-08:00), range crosses midnight.

### RateLimiter

Controls notification frequency to prevent spam.

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| window_seconds | float | Minimum time between notifications | 5.0 |
| last_notification | datetime | Last notification timestamp | None |

**State Transitions**:
- **Ready**: last_notification is None or elapsed >= window_seconds
- **Blocked**: elapsed < window_seconds

### NotificationManager

Session-scoped coordinator for notification logic.

| Field | Type | Description |
|-------|------|-------------|
| config | NotificationConfig | Current configuration |
| rate_limiter | RateLimiter | Spam prevention |
| notifier | Notifier | Platform-specific sender |
| error_stats_ref | ErrorStats | Reference for rate checking |
| last_error | str | Last notification error message |
| notification_available | bool | True if platform supports notifications |

**Relationships**:
- Contains 1 NotificationConfig
- Contains 1 RateLimiter
- Contains 1 Notifier
- References ErrorStats (for rate threshold checking)

### Notifier (Abstract)

Platform dispatcher for sending notifications.

| Method | Description |
|--------|-------------|
| send(title, body, subtitle) | Send notification, return success |
| is_available() | Check if notification system is available |
| get_platform_info() | Return platform/method description |

**Implementations**:
- `MacOSNotifier`: Uses osascript
- `LinuxNotifier`: Uses notify-send
- `WindowsNotifier`: Uses PowerShell toast
- `NoOpNotifier`: Fallback when no system available

### NotificationEvent

Represents a notification that was (or should be) sent.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When the triggering entry occurred |
| rule | NotificationRule | Which rule triggered |
| entry | LogEntry | The log entry that triggered |
| sent | bool | Whether notification was actually sent |
| suppressed_reason | str | Reason if not sent (rate limit, quiet hours) |

## Entity Relationships

```
AppState
├── NotificationManager
│   ├── NotificationConfig
│   │   ├── rules: list[NotificationRule]
│   │   └── quiet_hours: QuietHours?
│   ├── RateLimiter
│   └── Notifier (platform-specific)
│
├── ErrorStats (existing)
│   └── referenced by NotificationManager for rate checking
│
└── ConfigSchema (existing)
    └── NotificationsSection
        └── persisted notification settings
```

## Persistence

### Config File Schema

```toml
[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock detected/", "/out of memory/i"]
error_rate = 10  # errors per minute
slow_query_ms = 500
quiet_hours = "22:00-08:00"
```

### Runtime vs Persisted

| Setting | Runtime (AppState) | Persisted (config.toml) |
|---------|-------------------|------------------------|
| enabled | ✓ | ✓ |
| level rules | ✓ | ✓ via `levels` |
| pattern rules | ✓ | ✓ via `patterns` |
| error rate | ✓ | ✓ via `error_rate` |
| slow query | ✓ | ✓ via `slow_query_ms` |
| quiet hours | ✓ | ✓ via `quiet_hours` |
| rate limiter state | ✓ (session only) | — |
| last error | ✓ (session only) | — |

## Data Flow

```
LogEntry arrives
    │
    ▼
NotificationManager.check(entry)
    │
    ├── Is notifications enabled? No → return
    │
    ├── Is in quiet hours? Yes → return (suppressed)
    │
    ├── Does entry match any rule?
    │   ├── LEVEL: entry.level in rule.levels
    │   ├── PATTERN: rule.pattern.search(entry.message)
    │   ├── ERROR_RATE: ErrorStats.get_rate() > threshold
    │   └── SLOW_QUERY: entry.duration_ms > threshold
    │
    │   No match → return
    │
    ├── Is rate limited? Yes → return (suppressed)
    │
    └── Send notification via Notifier
        ├── Success → update rate limiter
        └── Failure → log error (once)
```
