---
title: Configuration
description: The configuration file, the commands that change it, and every setting.
---

pgtail keeps its settings in a TOML file.

## Config file location

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/pgtail/config.toml` |
| Linux | `~/.config/pgtail/config.toml` (or `$XDG_CONFIG_HOME/pgtail/config.toml`) |
| Windows | `%APPDATA%\pgtail\config.toml` |

Custom themes live in the `themes` folder beside it. The REPL's command history is kept in `history`, and tail mode's
in `tail_history`: beside the configuration on macOS and Windows, and in `~/.local/share/pgtail/` (or
`$XDG_DATA_HOME/pgtail/`) on Linux.

## Config commands

In the REPL:

```
config              # Show the current configuration as TOML
config path         # Show the config file location
config edit         # Edit it in the built-in editor
config reset        # Reset to the defaults, keeping a backup
```

From the command line:

```sh
pgtail config           # Show the current configuration
pgtail config --path    # Show the config file location
pgtail config --edit    # Edit it in the built-in editor
pgtail config --reset   # Reset to the defaults, keeping a backup
```

`config edit` creates the file from a commented template if it does not exist, then opens it in pgtail's built-in
editor, which highlights the TOML. **Ctrl+S** saves only valid settings: a TOML error, a setting pgtail does not know
(such as a misspelled `slow.warning` for `slow.warn`), an invalid value, or slow thresholds that do not ascend is shown
in the status line instead. **Esc** (or **Ctrl+Q**) closes the editor, and a second **Esc** discards unsaved changes.
When you close it after saving, the REPL reloads the configuration.

A file edited elsewhere is checked when pgtail starts: unknown settings are reported and ignored, and invalid values
are reported and replaced by their defaults. Settings earlier releases wrote that pgtail no longer reads, such as
`updates.last_version`, are accepted silently.

`config reset` renames the file to `config.toml.bak.YYYYMMDD-HHMMSS`, so pgtail runs on its defaults.

## Setting values

```
set <key> <value>   # Set and save a value
set <key>           # Show a value and its default
set                 # List every setting with its default
unset <key>         # Remove a setting, going back to its default
```

Examples:

```
set slow.warn 50
set theme.name monokai
set default.levels ERROR WARNING
set notifications.enabled true
unset slow.warn
```

`set` checks the value, saves it at once, and applies it to the running session. `set` also works in tail mode.

## Settings

### Default levels

```toml
[default]
levels = ["ERROR", "WARNING"]  # Levels shown at startup (empty = all)
```

### Slow query thresholds

```toml
[slow]
warn = 100      # Warning threshold (ms)
error = 500     # Slow threshold (ms)
critical = 1000 # Critical threshold (ms)
```

The thresholds must ascend; see [Slow queries](/guide/slow-queries/).

### Theme

```toml
[theme]
name = "dark"  # dark, light, high-contrast, monokai, solarized-dark, solarized-light, or a custom theme
```

### Notifications

```toml
[notifications]
enabled = false
levels = ["FATAL", "PANIC"]
patterns = ["/deadlock/"]     # /pattern/ matches case, /pattern/i ignores it
error_rate = 10               # Alert above N errors a minute
slow_query_ms = 500           # Alert on queries slower than this
quiet_hours = "22:00-08:00"
```

See [Notifications](/guide/notifications/).

### Updates

```toml
[updates]
check = true       # Check for a newer release when the REPL starts (once a day)
last_check = ""    # When it last checked (managed by pgtail)
```

### Semantic highlighting

```toml
[highlighting]
enabled = true               # Global on/off switch
max_length = 10240           # Characters highlighted per line

[highlighting.duration]
slow = 100                   # Slow threshold (ms)
very_slow = 500              # Very slow threshold (ms)
critical = 5000              # Critical threshold (ms)

[highlighting.enabled_highlighters]
timestamp = true             # Turn individual highlighters on or off
duration = true
sqlstate = true
# ... one key for each of the 30 highlighters

[[highlighting.custom]]      # Custom regular expression highlighters
name = "request_id"
pattern = "REQ-[A-Z]{3}-\\d{6}"
style = "cyan"
priority = 1050
enabled = true
```

See [Highlighting](/guide/highlighting/) for every setting.

## Example config

```toml
# ~/.config/pgtail/config.toml

[default]
levels = ["ERROR", "WARNING", "FATAL"]

[slow]
warn = 50
error = 200
critical = 500

[theme]
name = "monokai"

[notifications]
enabled = true
levels = ["FATAL", "PANIC"]
quiet_hours = "22:00-08:00"
```

pgtail keeps your comments and layout when it saves a setting. A value it cannot use is reported when pgtail starts,
and its default is used instead; a file that is not valid TOML is reported and the defaults are used.

## Environment variables

### NO_COLOR

Turns colors off, keeping bold and the other attributes:

```sh
NO_COLOR=1 pgtail
```

### PGDATA

A data directory to include in instance detection:

```sh
PGDATA=/var/lib/postgresql/16/main pgtail
```

### XDG_CONFIG_HOME and XDG_DATA_HOME

On Linux, move the configuration and the command history (see [Config file location](#config-file-location)).
