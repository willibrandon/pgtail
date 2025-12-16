# CLI Command Contracts: Configuration File Support

**Feature**: 005-config-file
**Date**: 2025-12-15

## Commands Overview

| Command | Description | FR |
|---------|-------------|-----|
| `config` | Display current configuration | FR-006 |
| `config edit` | Open config in $EDITOR | FR-007 |
| `config reset` | Reset to defaults with backup | FR-008 |
| `config path` | Show config file location | FR-009 |
| `set <key> <value>` | Set a configuration value | FR-010 |
| `set <key>` | Show current value of key | FR-011 |
| `unset <key>` | Remove a setting | FR-012 |

---

## config

Display current configuration with file location.

**Syntax**: `config`

**Arguments**: None

**Output Format**:
```
Configuration file: ~/.config/pgtail/config.toml

[default]
levels = ["ERROR", "WARNING"]

[slow]
warn = 50
error = 200
critical = 1000

[display]
timestamp_format = "%H:%M:%S.%f"
show_pid = true
show_level = true

[theme]
name = "dark"

[notifications]
enabled = false
levels = ["FATAL", "PANIC"]
```

**Behavior**:
- If config file exists: Display file path + contents in TOML format
- If config file doesn't exist: Display expected path + default values
- Show only non-default values if file exists, or all defaults if no file

**Errors**: None (always succeeds)

---

## config edit

Open configuration file in user's preferred editor.

**Syntax**: `config edit`

**Arguments**: None

**Behavior**:
1. Check for `$EDITOR` environment variable
2. If config file doesn't exist, create with commented template
3. Open file in editor
4. Wait for editor to close
5. Reload config after editor exits

**Output**:
```
Opening ~/.config/pgtail/config.toml in vim...
```

**Errors**:

| Condition | Message |
|-----------|---------|
| $EDITOR not set | "Error: $EDITOR not set. Set it with: export EDITOR=vim" |
| Editor exits with error | "Editor exited with code {code}" |
| Permission denied creating file | "Error: Cannot create config file: permission denied" |

---

## config reset

Reset configuration to defaults, creating backup of current file.

**Syntax**: `config reset`

**Arguments**: None

**Behavior**:
1. Check if config file exists
2. If exists: Create backup with timestamp
3. Delete original config file
4. Confirm reset with backup location

**Output**:
```
Configuration reset to defaults.
Backup saved to: ~/.config/pgtail/config.toml.bak.20251215-143022
```

**If no config exists**:
```
No configuration file to reset.
```

**Errors**:

| Condition | Message |
|-----------|---------|
| Permission denied | "Error: Cannot reset config: permission denied" |

---

## config path

Show the platform-specific configuration file path.

**Syntax**: `config path`

**Arguments**: None

**Output**:
```
~/.config/pgtail/config.toml
```

**Note**: Shows path even if file doesn't exist (for user to know where to create it).

---

## set

Set a configuration value or display current value.

**Syntax**:
- `set <key> <value>` - Set value
- `set <key>` - Show current value

**Arguments**:

| Argument | Required | Description |
|----------|----------|-------------|
| key | Yes | Dotted key path (e.g., `slow.warn`) |
| value | No | New value to set |

**Valid Keys**:
- `default.levels` - Array: `set default.levels ERROR WARNING`
- `default.follow` - Boolean: `set default.follow true`
- `slow.warn` - Integer: `set slow.warn 50`
- `slow.error` - Integer: `set slow.error 200`
- `slow.critical` - Integer: `set slow.critical 1000`
- `display.timestamp_format` - String: `set display.timestamp_format "%H:%M:%S"`
- `display.show_pid` - Boolean: `set display.show_pid false`
- `display.show_level` - Boolean: `set display.show_level false`
- `theme.name` - String: `set theme.name light`
- `notifications.enabled` - Boolean: `set notifications.enabled true`
- `notifications.levels` - Array: `set notifications.levels FATAL PANIC`
- `notifications.quiet_hours` - String: `set notifications.quiet_hours 22:00-08:00`

**Output (set value)**:
```
slow.warn = 50
```

**Output (show value)**:
```
slow.warn = 100 (default)
```
or
```
slow.warn = 50
```

**Behavior**:
1. Validate key exists in schema
2. If value provided: validate and save
3. If no value: display current value (indicate if default)
4. Update in-memory state immediately
5. Apply setting to current session

**Errors**:

| Condition | Message |
|-----------|---------|
| Unknown key | "Unknown setting: {key}. Use 'config' to see available settings." |
| Invalid value | "Invalid value for {key}: {reason}" |
| Permission denied | "Error: Cannot save config: permission denied" |

---

## unset

Remove a setting from configuration (revert to default).

**Syntax**: `unset <key>`

**Arguments**:

| Argument | Required | Description |
|----------|----------|-------------|
| key | Yes | Dotted key path to remove |

**Output**:
```
Removed slow.warn (using default: 100)
```

**If key not in config**:
```
Setting slow.warn is not configured (already using default)
```

**Behavior**:
1. Validate key exists in schema
2. Remove key from config file (if present)
3. Revert in-memory value to default
4. Apply default to current session

**Errors**:

| Condition | Message |
|-----------|---------|
| Unknown key | "Unknown setting: {key}. Use 'config' to see available settings." |
| Permission denied | "Error: Cannot save config: permission denied" |

---

## Value Parsing

### Arrays

Space-separated values:
```
set default.levels ERROR WARNING FATAL
```
Parses to: `["ERROR", "WARNING", "FATAL"]`

### Booleans

Case-insensitive:
```
set default.follow true
set default.follow TRUE
set default.follow True
set default.follow false
set default.follow FALSE
```

### Integers

Plain numbers:
```
set slow.warn 50
```

### Strings

Quoted for spaces, unquoted otherwise:
```
set theme.name dark
set display.timestamp_format "%H:%M:%S.%f"
```

---

## Autocomplete Support

Commands should register with `PgtailCompleter`:

```python
# Command completions
"config": ["edit", "reset", "path"]
"set": [<all valid keys>]
"unset": [<all valid keys>]

# Key completions for set/unset
SETTING_KEYS = [
    "default.levels", "default.follow",
    "slow.warn", "slow.error", "slow.critical",
    "display.timestamp_format", "display.show_pid", "display.show_level",
    "theme.name",
    "notifications.enabled", "notifications.levels", "notifications.quiet_hours"
]
```
