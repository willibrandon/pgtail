# Feature: Desktop Notifications for Alerts

## Problem

When tailing logs in the background or on a secondary monitor, critical errors can go unnoticed. Developers need immediate awareness of:
- FATAL/PANIC errors
- Specific error patterns
- Threshold breaches (too many errors, slow queries)

## Proposed Solution

Send desktop notifications when specified conditions are met. Support native notifications on macOS, Linux (notify-send), and Windows.

## User Scenarios

### Scenario 1: Fatal Error Alert
Developer has pgtail running while coding:
```
pgtail> notify on FATAL PANIC
Notifications enabled for: FATAL, PANIC
```
When a FATAL error occurs, desktop notification appears:
```
┌─────────────────────────────┐
│ pgtail: FATAL Error         │
│ connection limit exceeded   │
│ Instance: pg16 (localhost)  │
└─────────────────────────────┘
```

### Scenario 2: Pattern-Based Alert
DBA monitoring for specific issues:
```
pgtail> notify on /deadlock detected/
Notifications enabled for pattern: deadlock detected
```

### Scenario 3: Rate-Based Alert
Ops team monitoring error rate:
```
pgtail> notify on errors > 10/min
Notifications enabled: more than 10 errors per minute
```

### Scenario 4: Quiet Hours
Developer wants notifications only during work:
```
pgtail> notify quiet 22:00-08:00
Notifications silenced 22:00-08:00
```

## Commands

```
notify on <levels>           Enable for log levels
notify on /<pattern>/        Enable for regex match
notify on errors > N/min     Enable for error rate
notify on slow > Nms         Enable for slow queries
notify off                   Disable all notifications
notify quiet <time-range>    Set quiet hours
notify test                  Send test notification
notify                       Show current settings
```

## Platform Support

| Platform | Method |
|----------|--------|
| macOS | osascript / terminal-notifier |
| Linux | notify-send (libnotify) |
| Windows | win10toast / plyer |

## Notification Content

- Title: "pgtail: {LEVEL}" or "pgtail: Alert"
- Body: First line of log message (truncated)
- Subtitle: Instance name/ID
- Sound: Optional, configurable

## Success Criteria

1. Works on macOS, Linux with common desktop environments
2. Windows support (best effort)
3. Notifications are timely (< 1 second delay)
4. Rate limiting prevents notification spam (max 1 per 5 seconds)
5. Quiet hours prevent off-hours notifications
6. Graceful fallback if notification system unavailable
7. Test command verifies setup works

## Out of Scope

- Mobile push notifications
- Email/SMS alerts
- Webhook integrations (separate feature)
- Notification history
