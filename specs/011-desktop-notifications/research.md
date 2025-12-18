# Research: Desktop Notifications for Alerts

**Feature**: 011-desktop-notifications
**Date**: 2025-12-17

## 1. macOS Notification Mechanisms

### Decision: osascript with display notification

### Rationale
- **Zero dependencies**: osascript is built into macOS; no external tools needed
- **Reliable**: Works on all macOS versions since 10.9 (2013)
- **Sufficient features**: Supports title, body, subtitle, and sound

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| osascript | Built-in, reliable, no deps | Limited styling, no actions |
| terminal-notifier | More features, supports icons | External dependency, Homebrew only |
| PyObjC | Full native API access | Heavy dependency, complex |
| pyobjus | Native bindings | macOS only, complex setup |

### Implementation

```python
import subprocess

def notify_macos(title: str, body: str, subtitle: str | None = None) -> bool:
    """Send notification via osascript."""
    script = f'display notification "{body}"'
    if subtitle:
        script += f' subtitle "{subtitle}"'
    script += f' with title "{title}"'

    try:
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Notes
- Escape double quotes in body/title with backslash
- No icon support in osascript (uses Terminal.app icon)
- Sound can be added: `sound name "default"`

---

## 2. Linux Notification Standards

### Decision: notify-send with fallback detection

### Rationale
- **De facto standard**: notify-send (libnotify) is standard on GNOME, KDE, XFCE, etc.
- **Zero runtime dependencies**: Just calls external binary
- **Graceful detection**: Can check availability before first notification

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| notify-send | Standard, widely available | Not always installed |
| dbus-send | More control | Complex, DE-specific |
| zenity | More features | Dialogs, not notifications |
| plyer | Cross-platform | Heavy dependency |

### Implementation

```python
import shutil
import subprocess

def check_notify_send() -> bool:
    """Check if notify-send is available."""
    return shutil.which("notify-send") is not None

def notify_linux(title: str, body: str, urgency: str = "normal") -> bool:
    """Send notification via notify-send."""
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, title, body],
            capture_output=True,
            timeout=5,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Notes
- Urgency levels: low, normal, critical
- Critical notifications may not auto-dismiss (DE-dependent)
- Category can be set with `-c` for better handling

---

## 3. Windows Notification Options

### Decision: PowerShell toast notifications (best-effort)

### Rationale
- **No dependencies**: Uses built-in PowerShell and .NET
- **Works on Windows 10+**: Modern toast notification API
- **Best effort**: Constitution allows Windows as best-effort

### Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| PowerShell | Built-in, no deps | Complex, Windows 10+ only |
| win10toast | Simple API | External dependency |
| plyer | Cross-platform | Heavy dependency |
| winotify | Lightweight | External dependency |

### Implementation

```python
import subprocess

def notify_windows(title: str, body: str) -> bool:
    """Send notification via PowerShell."""
    # Escape single quotes for PowerShell
    title_escaped = title.replace("'", "''")
    body_escaped = body.replace("'", "''")

    script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
    $xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
    $text = $xml.GetElementsByTagName("text")
    $text[0].AppendChild($xml.CreateTextNode('{title_escaped}')) | Out-Null
    $text[1].AppendChild($xml.CreateTextNode('{body_escaped}')) | Out-Null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('pgtail').Show($toast)
    '''

    try:
        subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            timeout=10,
        )
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

### Notes
- Requires Windows 10 or later
- First-time use may require app registration
- Falls back gracefully on older Windows

---

## 4. Rate Limiting Patterns

### Decision: Simple time-window with last-notification timestamp

### Rationale
- **Simplest implementation**: Single timestamp comparison
- **Predictable behavior**: Easy to understand "1 per 5 seconds"
- **Low overhead**: O(1) check, no data structures

### Alternatives Considered

| Pattern | Pros | Cons |
|---------|------|------|
| Simple timestamp | Fast, simple | Bursty at window edges |
| Sliding window | Smoother rate | Complex, memory overhead |
| Token bucket | Flexible rates | Overkill for this use case |
| Leaky bucket | Steady output | Delays notifications |

### Implementation

```python
from datetime import datetime, timedelta

class RateLimiter:
    """Simple time-window rate limiter."""

    def __init__(self, window_seconds: float = 5.0):
        self._window = timedelta(seconds=window_seconds)
        self._last_allowed: datetime | None = None

    def should_allow(self) -> bool:
        """Check if action should be allowed and update state."""
        now = datetime.now()
        if self._last_allowed is None or (now - self._last_allowed) >= self._window:
            self._last_allowed = now
            return True
        return False

    def time_until_next(self) -> float:
        """Seconds until next notification allowed."""
        if self._last_allowed is None:
            return 0.0
        elapsed = (datetime.now() - self._last_allowed).total_seconds()
        remaining = self._window.total_seconds() - elapsed
        return max(0.0, remaining)
```

### Notes
- Global rate limit (not per-rule) as specified
- 5-second default aligns with spec requirement

---

## 5. Existing pgtail Integration Points

### Decision: Hook into LogTailer.on_entry callback

### Rationale
- **Already exists**: `on_entry` callback in LogTailer receives ALL entries before filtering
- **Used by error_stats**: Same pattern as existing ErrorStats integration
- **Clean separation**: Notification logic separate from display logic

### Integration Architecture

```
LogTailer
    ├── on_entry callback (before filtering)
    │   ├── ErrorStats.add(entry)
    │   ├── ConnectionStats.add(entry)
    │   └── NotificationManager.check(entry) <-- NEW
    │
    └── queue (after filtering) → display
```

### Key Integration Points

1. **AppState**: Add `NotificationManager` alongside `ErrorStats`, `ConnectionStats`
2. **cli.py main()**: Wire up notification manager to tailer's on_entry
3. **config.py**: Already has NotificationsSection (just expand it)
4. **commands.py**: Add `notify` to command completions

### Config Schema Extension

Existing config already has:
```python
@dataclass
class NotificationsSection:
    enabled: bool = False
    levels: list[str] = field(default_factory=lambda: ["FATAL", "PANIC"])
    quiet_hours: str | None = None
```

Need to add:
- `patterns: list[str]` - Regex patterns for notifications
- `error_rate_threshold: int | None` - Errors per minute threshold
- `slow_query_ms: int | None` - Slow query threshold

---

## Summary

| Topic | Decision | Key Benefit |
|-------|----------|-------------|
| macOS | osascript | Zero dependencies, built-in |
| Linux | notify-send | Standard, widely available |
| Windows | PowerShell | No dependencies, best-effort OK |
| Rate limiting | Simple timestamp | Simple, predictable |
| Integration | on_entry callback | Existing pattern, clean separation |

All research questions resolved. Ready for Phase 1 design.
