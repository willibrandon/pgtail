# Quickstart: Desktop Notifications for Alerts

**Feature**: 011-desktop-notifications
**Date**: 2025-12-17

## Overview

Desktop notifications alert you when important PostgreSQL log events occur, even when pgtail is running in the background.

## Basic Setup

### 1. Test Your System

First, verify your system can display notifications:

```
pgtail> notify test
Test notification sent
Platform: macOS (osascript)
```

If you see an error, check the troubleshooting section below.

### 2. Enable for Critical Errors

Enable notifications for the most critical errors:

```
pgtail> notify on FATAL PANIC
Notifications enabled for: FATAL, PANIC
```

### 3. Start Tailing

```
pgtail> tail 1
Tailing instance 1...
```

Now you'll receive desktop notifications whenever a FATAL or PANIC error occurs.

## Common Configurations

### Monitor All Errors

```
pgtail> notify on ERROR FATAL PANIC
Notifications enabled for: ERROR, FATAL, PANIC
```

### Monitor Specific Patterns

```
pgtail> notify on /deadlock detected/
Notifications enabled for pattern: deadlock detected

pgtail> notify on /connection refused/i
Notifications enabled for pattern: connection refused (case-insensitive)
```

### Alert on High Error Rate

```
pgtail> notify on errors > 10/min
Notifications enabled: more than 10 errors per minute
```

### Alert on Slow Queries

```
pgtail> notify on slow > 500ms
Notifications enabled: queries slower than 500ms
```

## Quiet Hours

Prevent notifications during off-hours:

```
pgtail> notify quiet 22:00-08:00
Notifications silenced 22:00-08:00
```

Disable quiet hours:

```
pgtail> notify quiet off
Quiet hours disabled
```

## Managing Notifications

### Check Current Settings

```
pgtail> notify
Notifications: enabled
  Levels: FATAL, PANIC
  Patterns: /deadlock detected/
  Quiet hours: 22:00-08:00
Platform: macOS (osascript)
```

### Disable Notifications

```
pgtail> notify off
Notifications disabled
```

### Clear All Rules

```
pgtail> notify clear
Notification rules cleared
```

## Persistent Configuration

All settings are saved to your config file and restored on next launch. You can also edit directly:

```
pgtail> config edit
```

Config location:
- macOS: `~/Library/Application Support/pgtail/config.toml`
- Linux: `~/.config/pgtail/config.toml`
- Windows: `%APPDATA%/pgtail/config.toml`

Example config section:

```toml
[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock detected/"]
quiet_hours = "22:00-08:00"
```

## Rate Limiting

To prevent notification spam during incidents, pgtail limits notifications to **1 per 5 seconds** maximum. This ensures you're alerted without being overwhelmed.

## Platform Support

| Platform | Method | Notes |
|----------|--------|-------|
| macOS | osascript | Built-in, no setup needed |
| Linux | notify-send | Requires libnotify-bin package |
| Windows | PowerShell | Windows 10+ recommended |

## Troubleshooting

### "notify-send not found" (Linux)

Install libnotify:

```bash
# Debian/Ubuntu
sudo apt install libnotify-bin

# Fedora
sudo dnf install libnotify

# Arch
sudo pacman -S libnotify
```

### "Notifications unavailable" (SSH)

Desktop notifications require a display server. When using SSH without X forwarding, notifications will be unavailable. This is expected behavior.

### Notifications not appearing (macOS)

Check System Settings > Notifications > Terminal (or your terminal app) and ensure notifications are allowed.

### Notifications not appearing (Linux)

Ensure your desktop environment's notification daemon is running. Most DEs start this automatically.

## Next Steps

- Combine with `errors --live` for real-time error monitoring
- Use `slow` command to identify slow queries
- Check `help` for all available commands
