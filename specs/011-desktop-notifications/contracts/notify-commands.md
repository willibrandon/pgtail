# CLI Contract: notify Commands

**Feature**: 011-desktop-notifications
**Date**: 2025-12-17

## Command Overview

| Command | Description |
|---------|-------------|
| `notify` | Show current notification settings |
| `notify on <levels>` | Enable level-based notifications |
| `notify on /<pattern>/[i]` | Enable pattern-based notifications |
| `notify on errors > N/min` | Enable error rate notifications |
| `notify on slow > Nms` | Enable slow query notifications |
| `notify off` | Disable all notifications |
| `notify quiet <range>` | Set quiet hours |
| `notify quiet off` | Disable quiet hours |
| `notify test` | Send test notification |
| `notify clear` | Remove all notification rules |

---

## notify (status)

Show current notification configuration.

**Syntax**: `notify`

**Output Format**:
```
Notifications: enabled
  Levels: FATAL, PANIC
  Patterns: /deadlock detected/, /out of memory/i
  Error rate: > 10/min
  Slow queries: > 500ms
  Quiet hours: 22:00-08:00 (active)
Platform: macOS (osascript)
```

**When disabled**:
```
Notifications: disabled
Platform: macOS (osascript)
Hint: Use 'notify on FATAL PANIC' to enable
```

**When unavailable**:
```
Notifications: unavailable
Platform: Linux (notify-send not found)
Hint: Install libnotify-bin package
```

---

## notify on \<levels\>

Enable notifications for specific log levels.

**Syntax**: `notify on <level> [level...]`

**Valid Levels**: DEBUG, INFO, NOTICE, WARNING, ERROR, FATAL, PANIC

**Examples**:
```
pgtail> notify on FATAL PANIC
Notifications enabled for: FATAL, PANIC

pgtail> notify on ERROR WARNING FATAL PANIC
Notifications enabled for: ERROR, WARNING, FATAL, PANIC
```

**Error Cases**:
```
pgtail> notify on INVALID
Unknown log level: INVALID
Valid levels: DEBUG, INFO, NOTICE, WARNING, ERROR, FATAL, PANIC

pgtail> notify on
Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms
```

**Behavior**:
- Adds to existing level rules (does not replace)
- Persists to config file
- Enables notifications if not already enabled

---

## notify on /\<pattern\>/[i]

Enable notifications for regex pattern matches.

**Syntax**: `notify on /<pattern>/[flags]`

**Flags**:
- `i` - Case-insensitive matching

**Examples**:
```
pgtail> notify on /deadlock detected/
Notifications enabled for pattern: deadlock detected

pgtail> notify on /connection refused/i
Notifications enabled for pattern: connection refused (case-insensitive)

pgtail> notify on /ERROR.*timeout/
Notifications enabled for pattern: ERROR.*timeout
```

**Error Cases**:
```
pgtail> notify on /[invalid/
Invalid regex pattern: unterminated character set

pgtail> notify on //
Pattern cannot be empty
```

**Behavior**:
- Adds to existing pattern rules
- Persists to config file
- Pattern is searched in log message (substring match)

---

## notify on errors \> N/min

Enable notifications when error rate exceeds threshold.

**Syntax**: `notify on errors > N/min`

**Examples**:
```
pgtail> notify on errors > 10/min
Notifications enabled: more than 10 errors per minute

pgtail> notify on errors > 5/min
Notifications enabled: more than 5 errors per minute
```

**Error Cases**:
```
pgtail> notify on errors > 0/min
Threshold must be at least 1

pgtail> notify on errors > abc/min
Invalid threshold: abc
```

**Behavior**:
- Uses existing ErrorStats for rate calculation
- Replaces previous error rate rule (only one active)
- Checks rate on each error entry
- Notification includes current rate

---

## notify on slow \> Nms

Enable notifications for slow queries.

**Syntax**: `notify on slow > <duration>`

**Duration Formats**:
- `Nms` - Milliseconds (e.g., `500ms`)
- `Ns` - Seconds (e.g., `5s`)

**Examples**:
```
pgtail> notify on slow > 500ms
Notifications enabled: queries slower than 500ms

pgtail> notify on slow > 2s
Notifications enabled: queries slower than 2000ms
```

**Error Cases**:
```
pgtail> notify on slow > 0ms
Threshold must be at least 1ms

pgtail> notify on slow > abc
Invalid duration: abc
```

**Behavior**:
- Replaces previous slow query rule (only one active)
- Checks duration in log entry (same as `slow` command)
- Notification includes query duration and excerpt

---

## notify off

Disable all notifications.

**Syntax**: `notify off`

**Output**:
```
Notifications disabled
```

**Behavior**:
- Sets enabled = false in config
- Does not clear rules (they persist for next enable)
- Persists to config file

---

## notify quiet \<range\>

Set quiet hours during which notifications are suppressed.

**Syntax**: `notify quiet <start>-<end>`

**Time Format**: HH:MM (24-hour)

**Examples**:
```
pgtail> notify quiet 22:00-08:00
Notifications silenced 22:00-08:00

pgtail> notify quiet 00:00-06:00
Notifications silenced 00:00-06:00
```

**Error Cases**:
```
pgtail> notify quiet 25:00-08:00
Invalid time: 25:00

pgtail> notify quiet abc
Invalid format. Use: notify quiet HH:MM-HH:MM
```

**Behavior**:
- Handles overnight ranges (22:00-08:00 = 10pm to 8am)
- Uses local system time
- Persists to config file
- Status command shows "(active)" if currently in quiet period

---

## notify quiet off

Disable quiet hours.

**Syntax**: `notify quiet off`

**Output**:
```
Quiet hours disabled
```

**Behavior**:
- Removes quiet_hours from config
- Notifications resume immediately
- Persists to config file

---

## notify test

Send a test notification to verify system setup.

**Syntax**: `notify test`

**Success Output**:
```
Test notification sent
Platform: macOS (osascript)
```

**Failure Output**:
```
Test notification failed
Platform: Linux
Error: notify-send not found
Hint: Install libnotify-bin package
```

**Notification Content**:
- Title: "pgtail: Test"
- Body: "Notification system is working correctly"
- Subtitle: Instance name if tailing, otherwise "pgtail"

**Behavior**:
- Bypasses rate limiting (always sends)
- Bypasses quiet hours (always sends)
- Does not require notifications to be enabled

---

## notify clear

Remove all notification rules.

**Syntax**: `notify clear`

**Output**:
```
Notification rules cleared
```

**Behavior**:
- Removes all rules (levels, patterns, rate, slow)
- Does not change enabled/disabled state
- Does not change quiet hours
- Persists to config file

---

## Command Completion

The completer should provide:

| Partial Input | Completions |
|--------------|-------------|
| `not` | `notify` |
| `notify ` | `on`, `off`, `quiet`, `test`, `clear` |
| `notify on ` | `FATAL`, `PANIC`, `ERROR`, `WARNING`, `errors`, `slow` |
| `notify on F` | `FATAL` |
| `notify on errors ` | `>` |
| `notify on slow ` | `>` |
| `notify quiet ` | `off`, (no time completion) |

---

## Config Persistence

All `notify` commands that change settings automatically persist to config.toml:

```toml
[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock detected/", "/out of memory/i"]
error_rate = 10
slow_query_ms = 500
quiet_hours = "22:00-08:00"
```

Settings are loaded on startup and applied to NotificationManager.
