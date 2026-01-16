# Semantic Highlighting

pgtail automatically colorizes meaningful patterns in PostgreSQL log output, making it easier to scan and understand logs at a glance.

## Overview

Semantic highlighting extends beyond SQL syntax highlighting to recognize:

- **Timestamps** with date, time, and timezone
- **Process IDs** in brackets
- **SQLSTATE codes** with error class coloring
- **Query durations** with threshold-based severity coloring
- **Object names** like tables, indexes, and schema-qualified identifiers
- **WAL information** including LSNs and segment filenames
- **Connection details** including IP addresses and backend types
- **Lock information** including lock types and wait conditions

## Commands

| Command | Description |
|---------|-------------|
| `highlight` | Show global status and all highlighters |
| `highlight list` | Same as above |
| `highlight on` | Enable all highlighting |
| `highlight off` | Disable all highlighting |
| `highlight enable <name>` | Enable a specific highlighter |
| `highlight disable <name>` | Disable a specific highlighter |
| `highlight add <name> <pattern> [--style <style>]` | Add custom highlighter |
| `highlight remove <name>` | Remove custom highlighter |
| `highlight preview` | Preview highlighting with sample output |
| `highlight reset` | Reset all settings to defaults |
| `highlight export [--file <path>]` | Export config as TOML |
| `highlight import <path>` | Import config from file |

## Viewing Highlighters

```
pgtail> highlight
Semantic Highlighting: enabled

Structural
  [on ] timestamp            Timestamps with date, time, ms, tz
  [on ] pid                  Process IDs in brackets
  [on ] context              DETAIL:, HINT:, CONTEXT: labels

Diagnostic
  [on ] sqlstate             SQLSTATE error codes
  [on ] error_name           Error names (unique_violation, etc.)

Performance
  [on ] duration             Query durations with threshold coloring
  [on ] memory               Memory values (kB, MB, GB)
  [on ] statistics           Checkpoint/vacuum statistics
...
```

## Toggling Global Highlighting

```
pgtail> highlight off
Highlighting disabled.

pgtail> highlight on
Highlighting enabled.
```

## Enabling/Disabling Specific Highlighters

```
pgtail> highlight disable timestamp
Disabled highlighter 'timestamp'.

pgtail> highlight enable timestamp
Enabled highlighter 'timestamp'.
```

## Built-in Highlighter Categories

### Structural (priority 100-199)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `timestamp` | Dates and times with timezone | `2024-01-15 14:30:45.123 UTC` |
| `pid` | Process IDs in brackets | `[12345]` |
| `context` | Context labels | `DETAIL:`, `HINT:`, `CONTEXT:` |

### Diagnostic (priority 200-299)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `sqlstate` | SQLSTATE error codes | `23505` |
| `error_name` | PostgreSQL error names | `unique_violation`, `deadlock_detected` |

### Performance (priority 300-399)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `duration` | Query durations | `150.234 ms` |
| `memory` | Memory sizes | `1024 MB`, `256 kB` |
| `statistics` | Stats with percentages | `wrote 1500 buffers (9.2%)` |

### Objects (priority 400-499)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `identifier` | Double-quoted identifiers | `"users_pkey"` |
| `relation` | Table/index names | `relation "users"` |
| `schema` | Schema-qualified names | `public.users` |

### WAL (priority 500-599)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `lsn` | Log Sequence Numbers | `0/1234ABCD` |
| `wal_segment` | WAL segment filenames | `000000010000000100000023` |
| `txid` | Transaction IDs | `xmin: 1234567` |

### Connection (priority 600-699)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `connection` | Connection info | `user=postgres database=mydb` |
| `ip` | IP addresses (v4 and v6) | `192.168.1.100`, `2001:db8::1` |
| `backend` | Backend process types | `autovacuum launcher`, `checkpointer` |

### SQL (priority 700-799)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `sql_keyword` | SQL keywords | `SELECT`, `FROM`, `WHERE` |
| `sql_string` | SQL string literals | `'hello'` |
| `sql_number` | SQL numbers | `42`, `3.14` |
| `sql_param` | Parameter placeholders | `$1`, `$2` |
| `sql_operator` | SQL operators | `||`, `::` |

### Lock (priority 800-899)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `lock_type` | Lock type names | `ShareLock`, `ExclusiveLock` |
| `lock_wait` | Lock wait information | `waiting for ExclusiveLock` |

### Checkpoint (priority 900-999)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `checkpoint` | Checkpoint messages | `checkpoint starting: time` |
| `recovery` | Recovery messages | `redo done at 0/1234ABCD` |

### Misc (priority 1000+)

| Highlighter | Pattern | Example |
|-------------|---------|---------|
| `boolean` | Boolean values | `on`, `off`, `true`, `false` |
| `null` | NULL keyword | `NULL` |
| `oid` | Object IDs | `OID 16384` |
| `path` | File paths | `/var/log/postgresql/...` |

## Duration Threshold Coloring

Query durations are colored based on severity thresholds:

| Threshold | Default | Theme Key | Color |
|-----------|---------|-----------|-------|
| Fast | < 100ms | Default | Normal |
| Slow | 100-499ms | `hl_duration_slow` | Yellow |
| Very Slow | 500-4999ms | `hl_duration_very_slow` | Orange |
| Critical | >= 5000ms | `hl_duration_critical` | Red (bold) |

### Configuring Thresholds

In REPL mode:

```
pgtail> set highlighting.duration.slow 50
pgtail> set highlighting.duration.very_slow 200
pgtail> set highlighting.duration.critical 1000
```

In `config.toml`:

```toml
[highlighting.duration]
slow = 50
very_slow = 200
critical = 1000
```

## Custom Highlighters

### Adding Custom Patterns

```
pgtail> highlight add request_id "REQ-[A-Z]{3}-\d{6}" --style "cyan"
Added custom highlighter 'request_id' with pattern 'REQ-[A-Z]{3}-\d{6}'.

pgtail> highlight add txn_id "TXN:[0-9a-f]{16}" --style "bold magenta"
Added custom highlighter 'txn_id' with pattern 'TXN:[0-9a-f]{16}'.
```

### Pattern Syntax

Custom patterns use Python regex syntax:

- `\d+` - One or more digits
- `[A-Z]{3}` - Exactly 3 uppercase letters
- `[0-9a-f]+` - Hex digits
- `\w+` - Word characters
- `(?:...)` - Non-capturing group

### Style Options

Styles use Rich markup syntax:

- Color names: `red`, `green`, `cyan`, `magenta`, `yellow`
- Hex colors: `#ff6b6b`, `#2ecc71`
- Modifiers: `bold`, `italic`, `underline`
- Combined: `bold red`, `italic #ff6b6b`

### Setting Priority

Higher priority highlighters run first. Default custom highlighter priority is 1050+.

```
pgtail> highlight add high_priority_pattern "CRITICAL" --style "bold red" --priority 50
```

### Removing Custom Highlighters

```
pgtail> highlight remove request_id
Removed custom highlighter 'request_id'.
```

## Preview Mode

See all highlighters in action with sample log lines:

```
pgtail> highlight preview
Highlight Preview (enabled)

Structural
  Timestamp with timezone and process ID
  2024-01-15 14:30:45.123 UTC [12345] LOG:  database system is ready

Performance
  Fast query duration
  LOG:  duration: 45.123 ms  statement: SELECT * FROM users

  Slow query duration
  LOG:  duration: 150.456 ms  statement: SELECT * FROM orders

  Critical query duration
  LOG:  duration: 5500.789 ms  statement: SELECT * FROM large_table
...
```

## Export/Import Configuration

### Exporting to TOML

```
pgtail> highlight export
# pgtail highlighting configuration
# Export generated by: highlight export

[highlighting]
enabled = true
max_length = 10240

[highlighting.duration]
slow = 100
very_slow = 500
critical = 5000

[highlighting.enabled_highlighters]
timestamp = false

[[highlighting.custom]]
name = "request_id"
pattern = "REQ-[A-Z]{3}-\\d{6}"
style = "cyan"
priority = 1050
```

### Exporting to a File

```
pgtail> highlight export --file ~/highlight-config.toml
Exported highlighting config to /Users/you/highlight-config.toml
```

### Importing Configuration

```
pgtail> highlight import ~/highlight-config.toml
Imported highlighting config from /Users/you/highlight-config.toml
```

## Resetting to Defaults

```
pgtail> highlight reset
Reset complete: enabled highlighting, enabled all highlighters, reset duration thresholds, removed custom highlighters.
```

## Configuration Persistence

All highlighting settings are stored in `config.toml`:

```toml
[highlighting]
enabled = true
max_length = 10240

[highlighting.duration]
slow = 100
very_slow = 500
critical = 5000

[highlighting.enabled_highlighters]
timestamp = false
duration = true

[[highlighting.custom]]
name = "request_id"
pattern = "REQ-[A-Z]{3}-\\d{6}"
style = "cyan"
priority = 1050
enabled = true
```

## Theme Integration

Highlighting colors are defined in themes under the `ui` section:

```toml
[ui]
hl_duration_slow = "yellow"
hl_duration_very_slow = "#ff8800"
hl_duration_critical = "bold red"
hl_sqlstate = "bold red"
hl_error_name = "red"
hl_identifier = "cyan"
hl_relation = "green"
hl_lsn = "blue"
hl_wal_segment = "magenta"
# ... more highlight styles
```

See the [Themes guide](themes.md) for creating custom themes.

## Performance

Semantic highlighting is designed for high throughput:

- **10,000+ lines/second** processing speed
- **Lazy initialization** - Aho-Corasick automatons built on first use
- **Max line length** - Lines over 10KB have highlighting applied only to the first 10KB
- **Non-overlapping** - Highlighters respect already-colored regions
