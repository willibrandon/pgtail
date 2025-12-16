# Data Model: Configuration File Support

**Feature**: 005-config-file
**Date**: 2025-12-15

## Entities

### Configuration

The root entity representing all user preferences.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| default | DefaultSection | Default behavior settings |
| slow | SlowSection | Slow query threshold settings |
| display | DisplaySection | Output formatting settings |
| theme | ThemeSection | Color theme settings |
| notifications | NotificationsSection | Notification settings |

**Storage**: TOML file at platform-specific path

**Lifecycle**:
- Created: On first `set` command (lazy creation)
- Read: On application startup
- Updated: On `set` or `unset` command
- Deleted: On `config reset` (backed up first)

---

### DefaultSection

Settings that control default behavior on startup.

**Attributes**:

| Attribute | Type | Default | Validation |
|-----------|------|---------|------------|
| levels | list[str] | [] (all levels) | Each element must be valid LogLevel |
| follow | bool | true | Must be boolean |

**Valid LogLevel values**: `DEBUG`, `LOG`, `INFO`, `NOTICE`, `WARNING`, `ERROR`, `FATAL`, `PANIC`

---

### SlowSection

Thresholds for slow query detection highlighting.

**Attributes**:

| Attribute | Type | Default | Validation |
|-----------|------|---------|------------|
| warn | int | 100 | Must be positive integer (ms) |
| error | int | 500 | Must be positive integer, > warn |
| critical | int | 1000 | Must be positive integer, > error |

**Constraint**: warn < error < critical (validated on load)

---

### DisplaySection

Output formatting preferences.

**Attributes**:

| Attribute | Type | Default | Validation |
|-----------|------|---------|------------|
| timestamp_format | str | "%H:%M:%S.%f" | Must be valid strftime format |
| show_pid | bool | true | Must be boolean |
| show_level | bool | true | Must be boolean |

---

### ThemeSection

Color theme selection.

**Attributes**:

| Attribute | Type | Default | Validation |
|-----------|------|---------|------------|
| name | str | "dark" | Must be "dark" or "light" |

---

### NotificationsSection

Desktop notification settings (future feature, config schema defined now).

**Attributes**:

| Attribute | Type | Default | Validation |
|-----------|------|---------|------------|
| enabled | bool | false | Must be boolean |
| levels | list[str] | ["FATAL", "PANIC"] | Each element must be valid LogLevel |
| quiet_hours | str \| None | None | Format: "HH:MM-HH:MM" or null |

---

### Setting

Represents a single configuration value with dotted key path.

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| key | str | Dotted path (e.g., "slow.warn") |
| value | Any | Current value |
| default | Any | Default value if unset |
| validator | Callable | Validation function |

**Key Path Format**: `section.attribute` (e.g., `slow.warn`, `default.levels`)

---

## Relationships

```
Configuration
├── default: DefaultSection (1:1)
├── slow: SlowSection (1:1)
├── display: DisplaySection (1:1)
├── theme: ThemeSection (1:1)
└── notifications: NotificationsSection (1:1)
```

## State Transitions

### Configuration Lifecycle

```
[Not Exists] ---(first set)--> [Exists]
[Exists] ---(set/unset)--> [Exists] (updated)
[Exists] ---(config reset)--> [Not Exists] + [Backup Created]
```

### Load State Machine

```
[Start]
  |
  v
[Read File] ---(FileNotFoundError)--> [Use All Defaults]
  |
  v
[Parse TOML] ---(TOMLDecodeError)--> [Warn] --> [Use All Defaults]
  |
  v
[Validate Each Key]
  |
  +---(Invalid Value)--> [Warn] --> [Use Default for Key]
  |
  v
[Apply Valid Settings]
  |
  v
[Done]
```

## TOML Schema

```toml
# Complete schema with all sections and attributes

[default]
levels = ["ERROR", "WARNING"]  # list of LogLevel strings
follow = true                   # boolean

[slow]
warn = 100      # positive integer (ms)
error = 500     # positive integer (ms), > warn
critical = 1000 # positive integer (ms), > error

[display]
timestamp_format = "%H:%M:%S.%f"  # strftime format string
show_pid = true                    # boolean
show_level = true                  # boolean

[theme]
name = "dark"  # "dark" or "light"

[notifications]
enabled = false                # boolean
levels = ["FATAL", "PANIC"]    # list of LogLevel strings
quiet_hours = "22:00-08:00"    # "HH:MM-HH:MM" or omitted
```

## Validation Rules

| Key | Rule | Error Message |
|-----|------|---------------|
| default.levels | All elements in LogLevel enum | "Invalid log level: {value}. Valid: DEBUG, LOG, INFO, NOTICE, WARNING, ERROR, FATAL, PANIC" |
| slow.warn | > 0 | "slow.warn must be a positive integer (milliseconds)" |
| slow.error | > slow.warn | "slow.error ({value}) must be greater than slow.warn ({warn})" |
| slow.critical | > slow.error | "slow.critical ({value}) must be greater than slow.error ({error})" |
| display.timestamp_format | Valid strftime | "Invalid timestamp format: {value}" |
| theme.name | in ["dark", "light"] | "Invalid theme: {value}. Valid: dark, light" |
| notifications.quiet_hours | Matches HH:MM-HH:MM | "Invalid quiet_hours format: {value}. Expected: HH:MM-HH:MM" |
