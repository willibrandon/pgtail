# CLI Reference

Complete reference for all pgtail commands.

## REPL Commands

### Instance Management

| Command | Description |
|---------|-------------|
| `list` | List detected PostgreSQL instances |
| `select <id>` | Select an instance for commands |
| `scan` | Re-scan for instances |

### Tailing

| Command | Description |
|---------|-------------|
| `tail <id>` | Enter tail mode for instance |
| `tail <id> --since <time>` | Tail with time filter |
| `tail <id> --stream` | Legacy streaming mode |
| `stop` | Stop tailing |

### Filtering

| Command | Description |
|---------|-------------|
| `level <lvl>` | Set level filter |
| `level <lvl>+` | Level and more severe |
| `level <lvl>-` | Level and less severe |
| `filter /pattern/` | Add regex filter |
| `filter /pattern/i` | Case-insensitive regex |
| `filter field=value` | Field filter (CSV/JSON) |
| `unfilter /pattern/` | Remove regex filter |

### Time Filters

| Command | Description |
|---------|-------------|
| `since <time>` | Show from time onward |
| `until <time>` | Show up to time |
| `between <start> <end>` | Time range |
| `since clear` | Clear since filter |
| `until clear` | Clear until filter |

### Statistics

| Command | Description |
|---------|-------------|
| `errors` | Error summary |
| `errors --trend` | Error rate sparkline |
| `errors --live` | Live error counter |
| `errors --code <CODE>` | Filter by SQLSTATE |
| `errors clear` | Reset statistics |
| `connections` | Connection summary |
| `connections --history` | Connection history |
| `connections --watch` | Live connection stream |
| `connections clear` | Reset statistics |

### Export

| Command | Description |
|---------|-------------|
| `export <file>` | Export to file |
| `export --format <fmt> <file>` | Export with format |
| `export --append <file>` | Append to file |
| `export --since <time> <file>` | Time-scoped export |
| `export --follow <file>` | Continuous export |
| `pipe <cmd>` | Pipe to command |
| `pipe --format <fmt> <cmd>` | Pipe with format |

### Notifications

| Command | Description |
|---------|-------------|
| `notify` | Show notification status |
| `notify on <levels>` | Enable for levels |
| `notify on /pattern/` | Enable for pattern |
| `notify on errors > N/min` | Enable for error rate |
| `notify on slow > Nms` | Enable for slow queries |
| `notify off` | Disable all |
| `notify test` | Send test notification |
| `notify quiet HH:MM-HH:MM` | Set quiet hours |
| `notify clear` | Remove all rules |

### Configuration

| Command | Description |
|---------|-------------|
| `config` | Show current config |
| `config path` | Show config file path |
| `config edit` | Edit in $EDITOR |
| `config reset` | Reset to defaults |
| `set <key> <value>` | Set config value |
| `unset <key>` | Remove config value |

### Themes

| Command | Description |
|---------|-------------|
| `theme` | Show current theme |
| `theme <name>` | Switch theme |
| `theme list` | List available themes |
| `theme preview <name>` | Preview theme |
| `theme edit <name>` | Create/edit custom theme |
| `theme reload` | Reload current theme |

### Display

| Command | Description |
|---------|-------------|
| `display` | Show display mode |
| `display compact` | Compact single-line mode |
| `display full` | Full multi-line mode |
| `display fields <f1,f2>` | Custom field selection |
| `output text` | Text output format |
| `output json` | JSON Lines format |

### PostgreSQL

| Command | Description |
|---------|-------------|
| `enable-logging <id>` | Enable logging for instance |

### Slow Queries

| Command | Description |
|---------|-------------|
| `slow <ms>` | Set slow query threshold |
| `slow off` | Disable slow query highlighting |

### General

| Command | Description |
|---------|-------------|
| `help` | Show help |
| `clear` | Clear filters |
| `clear force` | Clear all including anchor |
| `exit` / `quit` | Exit pgtail |

## Tail Mode Commands

In tail mode (after `tail <id>`), use the `tail>` prompt:

| Command | Description |
|---------|-------------|
| `level <lvl>` | Level filter |
| `filter /pattern/` | Regex filter |
| `since <time>` | Time filter |
| `until <time>` | End time filter |
| `between <s> <e>` | Time range |
| `slow <ms>` | Slow query threshold |
| `clear` | Reset to anchor filters |
| `clear force` | Clear all filters |
| `errors` | Show error stats |
| `connections` | Show connection stats |
| `pause` / `p` | Pause auto-scroll |
| `follow` / `f` | Resume follow |
| `help` | Show help |
| `stop` / `q` | Exit tail mode |

## Tail Mode Keys

See [Tail Mode](guide/tail-mode.md) for complete key reference.
