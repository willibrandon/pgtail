# Feature: Configuration File Support

## Problem

Users have preferences that they want to persist:
- Default log level filters
- Slow query thresholds
- Color themes
- Notification settings
- Custom key bindings

Currently, all settings reset when pgtail exits.

## Proposed Solution

Support a configuration file that persists user preferences. Use a simple, human-editable format (TOML). Provide commands to view and modify settings.

## User Scenarios

### Scenario 1: Set Defaults
Developer always wants to filter to ERROR and WARNING:
```
pgtail> set default.levels ERROR WARNING
Default levels set. Will apply on startup.
```

### Scenario 2: Configure Slow Query Thresholds
DBA has specific performance requirements:
```
pgtail> set slow.warn 50
pgtail> set slow.error 200
pgtail> set slow.critical 1000
```

### Scenario 3: Choose Theme
User prefers light terminal:
```
pgtail> set theme light
Theme set to: light
```

### Scenario 4: View All Settings
User wants to see current configuration:
```
pgtail> config
Configuration file: ~/.config/pgtail/config.toml

[default]
levels = ["ERROR", "WARNING"]

[slow]
warn = 50
error = 200
critical = 1000

[theme]
name = "dark"

[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
```

### Scenario 5: Edit Config Directly
Power user wants to edit file:
```
pgtail> config edit
Opening ~/.config/pgtail/config.toml in $EDITOR...
```

## Configuration File Location

| Platform | Path |
|----------|------|
| macOS | ~/Library/Application Support/pgtail/config.toml |
| Linux | ~/.config/pgtail/config.toml |
| Windows | %APPDATA%/pgtail/config.toml |

## Configuration Schema

```toml
[default]
levels = ["ERROR", "WARNING", "FATAL"]  # Default level filter
follow = true                            # Auto-follow new entries

[slow]
warn = 100      # Yellow threshold (ms)
error = 500     # Orange threshold (ms)
critical = 1000 # Red threshold (ms)

[display]
timestamp_format = "%H:%M:%S.%f"  # strftime format
show_pid = true
show_level = true

[theme]
name = "dark"  # dark, light, or custom

[notifications]
enabled = false
levels = ["FATAL", "PANIC"]
quiet_hours = "22:00-08:00"

[keybindings]
scroll_up = "k"
scroll_down = "j"
search = "/"
quit = "q"
```

## Commands

```
config                  Show current configuration
config edit             Open config file in $EDITOR
config reset            Reset to defaults
config path             Show config file path

set <key> <value>       Set a configuration value
set <key>               Show current value
unset <key>             Remove setting (use default)
```

## Success Criteria

1. Config file created on first `set` command
2. All settings documented in default config (commented)
3. Invalid config values show helpful errors
4. Config reloaded when file changes (optional)
5. Command-line flags override config file
6. `config reset` preserves a backup
7. Works correctly when config file doesn't exist

## Out of Scope

- Multiple config profiles
- Config sync across machines
- GUI config editor
- Environment variable overrides for all settings
