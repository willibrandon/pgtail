# Configuration

pgtail stores configuration in a TOML file.

## Config File Location

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/pgtail/config.toml` |
| Linux | `~/.config/pgtail/config.toml` |
| Windows | `%APPDATA%/pgtail/config.toml` |

## Config Commands

```
config              # Show current configuration
config path         # Show config file location
config edit         # Open in $EDITOR
config reset        # Reset to defaults (creates backup)
```

## Setting Values

```
set <key> <value>   # Set a config value
unset <key>         # Remove a setting (revert to default)
```

Examples:

```
set slow.warn 50
set theme.name monokai
set default.levels ERROR WARNING
unset slow.warn
```

## Available Settings

### Default Behavior

```toml
[default]
levels = ["ERROR", "WARNING"]  # Default level filter (empty = all)
follow = true                   # Auto-follow new entries
```

### Slow Query Thresholds

```toml
[slow]
warn = 100      # Warning threshold (ms)
error = 500     # Slow threshold (ms)
critical = 1000 # Critical threshold (ms)
```

### Display Settings

```toml
[display]
timestamp_format = "%H:%M:%S.%f"  # strftime format
show_pid = true                    # Show process ID
show_level = true                  # Show log level
```

### Theme

```toml
[theme]
name = "dark"  # dark, light, high-contrast, monokai, solarized-dark, solarized-light
```

### Notifications

```toml
[notifications]
enabled = false
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock/"]
error_rate = 10               # Alert above N errors/min
slow_query_ms = 500           # Alert on slow queries
quiet_hours = "22:00-08:00"
```

### Semantic Highlighting

```toml
[highlighting]
enabled = true               # Global on/off switch
max_length = 10240           # Max chars to highlight per line (10KB)

[highlighting.duration]
slow = 100                   # Slow threshold (ms) - yellow
very_slow = 500              # Very slow threshold (ms) - orange
critical = 5000              # Critical threshold (ms) - red

[highlighting.enabled_highlighters]
timestamp = true             # Enable/disable specific highlighters
duration = true
sqlstate = true
# ... more highlighters

[[highlighting.custom]]      # Custom regex highlighters
name = "request_id"
pattern = "REQ-[A-Z]{3}-\\d{6}"
style = "cyan"
priority = 1050
enabled = true
```

See the [Highlighting guide](guide/highlighting.md) for details on all settings.

### Buffer Limits

```toml
[buffer]
tailer_max = 10000           # Log tailer buffer
error_stats_max = 10000      # Error statistics buffer
connection_stats_max = 10000 # Connection statistics buffer
tail_log_max = 10000         # Tail mode display buffer
```

## Example Config

```toml
# ~/.config/pgtail/config.toml

[default]
levels = ["ERROR", "WARNING", "FATAL"]
follow = true

[slow]
warn = 50
error = 200
critical = 500

[display]
timestamp_format = "%H:%M:%S"
show_pid = true

[theme]
name = "monokai"

[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
quiet_hours = "22:00-08:00"
```

## Environment Variables

### NO_COLOR

Disables all color output:

```bash
NO_COLOR=1 pgtail
```

### PGDATA

Used for PostgreSQL instance detection:

```bash
PGDATA=/var/lib/postgresql/16/main pgtail
```
