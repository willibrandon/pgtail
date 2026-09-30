---
title: Notifications
description: Desktop notifications for log levels, patterns, error rates, and slow queries, with quiet hours.
---

pgtail can send desktop notifications for important log events while it tails.

## Platform support

| Platform | Method |
|----------|--------|
| macOS | `osascript` (built in) |
| Linux | `notify-send` (libnotify; install the `libnotify-bin` package if it is missing) |
| Windows | Windows toast notifications |

On Windows, pgtail creates a `pgtail` shortcut in the Start menu, since Windows shows toasts only for applications
registered there.

## Turning notifications on

`notify on` adds a rule and turns notifications on. Rules add up: each `notify on` keeps the earlier ones.

### By log level

```pgtail
notify on FATAL PANIC          # Specific levels
notify on error+               # ERROR and above
```

Levels accept the same forms as [`level`](/guide/filtering/#level-filtering).

### By pattern

```pgtail
notify on /deadlock/            # Case-sensitive
notify on /connection refused/i # Ignoring case
```

### By error rate

```pgtail
notify on errors > 10/min      # When more than 10 errors arrive in a minute
```

### By query duration

```pgtail
notify on slow > 500ms         # When a query takes longer than 500 ms
notify on slow > 2s            # Seconds work too
```

## Viewing the settings

```pgtail
pgtail> notify
```

```
Notifications: enabled
  Levels: FATAL, PANIC
  Patterns: /deadlock/i
  Error rate: > 10/min
  Quiet hours: 22:00-08:00
Platform: macOS (osascript)
```

## What notifies, and how often

- Only entries logged after tailing starts. Entries a time filter reads back, as `tail 0 --since 1d` does, count in
  the statistics but never notify.
- At most one notification every 5 seconds. Alerts that match in between are not dropped: when the 5 seconds are up,
  one notification counts them (`pgtail: 4 more alerts`, `3 ERROR · 1 FATAL`) and shows the most severe.
- An alert whose message was already shown in the last minute, apart from its numbers (`queue depth is 814` and
  `queue depth is 233`), counts as a repeat instead of showing again; the next time it shows, it says how many times it
  repeated.
- Error rate alerts at most once a minute
- Nothing during quiet hours

## Quiet hours

Silence notifications during set hours:

```pgtail
notify quiet 22:00-08:00       # Nothing from 10 PM to 8 AM
notify quiet off               # No quiet hours
```

A range that crosses midnight works as expected. `notify` shows `(active)` while quiet hours are in effect.

## Testing

```pgtail
notify test                    # An info notification
notify test error              # Also: warning, critical
```

On Windows the severity sets how long the toast stays in the notification center: 2 minutes for info, 10 for warning,
30 for error, and until dismissed for critical.

## Turning notifications off

```pgtail
notify off                     # Stop notifying, keeping the rules
notify clear                   # Remove every rule
```

## Configuration

`notify` commands save their settings to the configuration file:

```toml
[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock/i"]
error_rate = 10
slow_query_ms = 500
quiet_hours = "22:00-08:00"
```

The same commands work in tail mode.
