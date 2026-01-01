# Desktop Notifications

pgtail can send desktop notifications for important log events.

## Platform Support

| Platform | Method |
|----------|--------|
| macOS | `osascript` (built-in) |
| Linux | `notify-send` (libnotify) |
| Windows | PowerShell toast |

## Enabling Notifications

### By Log Level

```
notify on ERROR FATAL PANIC    # Specific levels
notify on error+               # ERROR and above
```

### By Pattern

```
notify on /deadlock/           # Case-sensitive
notify on /connection refused/i # Case-insensitive
```

### By Error Rate

```
notify on errors > 10/min      # Alert when rate exceeds threshold
```

### By Query Duration

```
notify on slow > 500ms         # Alert on slow queries
```

## Viewing Status

```
pgtail> notify
```

Shows current notification settings:

```
Notifications: enabled
Platform: macOS (osascript)

Rules:
  - Levels: FATAL, PANIC
  - Pattern: /deadlock/i
  - Error rate: > 10/min

Rate limiting: 1 per 5 seconds
Quiet hours: 22:00-08:00
```

## Rate Limiting

Notifications are rate-limited to prevent spam:

- Maximum 1 notification per 5 seconds
- Quiet hours suppress all notifications

## Quiet Hours

Suppress notifications during specific hours:

```
notify quiet 22:00-08:00       # No notifications 10 PM - 8 AM
notify quiet off               # Disable quiet hours
```

Handles overnight spans correctly.

## Testing Notifications

```
notify test                    # Send test notification
```

## Disabling Notifications

```
notify off                     # Disable all
notify clear                   # Remove all rules
```

## Configuration

Persist notification settings:

```toml
[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock/i"]
error_rate = 10
slow_query_ms = 500
quiet_hours = "22:00-08:00"
```
