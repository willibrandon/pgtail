---
title: Highlighting
description: Semantic highlighting of log messages, its 30 built-in highlighters, and custom patterns.
---

pgtail colors meaningful parts of PostgreSQL log messages, so logs can be read at a glance.

## Overview

Semantic highlighting recognizes:

- **Timestamps** with date, time, and time zone
- **Process IDs** in brackets
- **SQLSTATE codes**, colored by error class
- **Query durations**, colored by threshold
- **Object names** such as tables, indexes, and schema-qualified identifiers
- **WAL information** including LSNs and segment file names
- **Connection details** including IP addresses and backend types
- **Lock information** including lock types and waits
- **SQL** keywords, strings, numbers, parameters, and operators in statements

## Commands

The same `highlight` commands work in the REPL and in tail mode, where the log redraws after each change. Changes
are saved to the configuration file.

| Command | Description |
|---------|-------------|
| `highlight` | Show the global status and every highlighter |
| `highlight list` | The same |
| `highlight on` | Turn highlighting on |
| `highlight off` | Turn highlighting off |
| `highlight enable <name>` | Turn on one highlighter |
| `highlight disable <name>` | Turn off one highlighter |
| `highlight add <name> <pattern> [--style <style>] [--priority <n>]` | Add a custom highlighter |
| `highlight remove <name>` | Remove a custom highlighter |
| `highlight preview` | Show sample lines with every highlighter |
| `highlight reset` | Reset all highlighting settings to the defaults |
| `highlight export [--file <path>]` | Print the settings as TOML, or write them to a file |
| `highlight import <path>` | Load settings from a TOML file |

## Viewing highlighters

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

## Turning highlighting on and off

```
pgtail> highlight off
Highlighting disabled.

pgtail> highlight on
Highlighting enabled.
```

## Enabling and disabling highlighters

```
pgtail> highlight disable timestamp
Disabled highlighter 'timestamp'.

pgtail> highlight enable timestamp
Enabled highlighter 'timestamp'.
```

A misspelled name gets a suggestion, such as `Unknown highlighter 'timestamps'. Did you mean 'timestamp'?`. `enable`
and `disable` also work on custom highlighters.

## Built-in highlighters

### Structural

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `timestamp` | Dates and times with time zone | `2024-01-15 14:30:45.123 UTC` |
| `pid` | Process IDs in brackets | `[12345]` |
| `context` | Context labels | `DETAIL:`, `HINT:`, `CONTEXT:` |

### Diagnostic

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `sqlstate` | SQLSTATE error codes | `23505` |
| `error_name` | PostgreSQL error names | `unique_violation`, `deadlock_detected` |

### Performance

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `duration` | Query durations | `150.234 ms` |
| `memory` | Memory sizes | `1024 MB`, `256 kB` |
| `statistics` | Statistics with percentages | `wrote 1500 buffers (9.2%)` |

### Objects

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `identifier` | Double-quoted identifiers | `"users_pkey"` |
| `relation` | Table and index names | `relation "users"` |
| `schema` | Schema-qualified names | `public.users` |

### WAL

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `lsn` | Log sequence numbers | `0/1234ABCD` |
| `wal_segment` | WAL segment file names | `000000010000000100000023` |
| `txid` | Transaction IDs | `xmin: 1234567` |

### Connection

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `connection` | Connection info | `user=postgres database=mydb` |
| `ip` | IP addresses (v4 and v6) | `192.168.1.100`, `2001:db8::1` |
| `backend` | Backend process types | `autovacuum launcher`, `checkpointer` |

### SQL

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `sql_keyword` | SQL keywords | `SELECT`, `FROM`, `WHERE` |
| `sql_string` | SQL string literals | `'hello'` |
| `sql_number` | SQL numbers | `42`, `3.14` |
| `sql_param` | Parameter placeholders | `$1`, `$2` |
| `sql_operator` | SQL operators | `\|\|`, `::` |

### Lock

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `lock_type` | Lock type names | `ShareLock`, `ExclusiveLock` |
| `lock_wait` | Lock waits | `still waiting for ExclusiveLock` |

### Checkpoint

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `checkpoint` | Checkpoint messages | `checkpoint starting: time` |
| `recovery` | Recovery messages | `redo done at 0/1234ABCD` |

### Misc

| Highlighter | Matches | Example |
|-------------|---------|---------|
| `boolean` | Boolean values | `on`, `off`, `true`, `false` |
| `null` | The NULL keyword | `NULL` |
| `oid` | Object IDs | `OID 16384` |
| `path` | File paths | `/var/log/postgresql/...` |

## Duration threshold coloring

The `duration` highlighter colors each duration by its own thresholds:

| Range | Default | Theme element | Color in the dark theme |
|-------|---------|---------------|-------------------------|
| Fast | < 100 ms | `hl_duration_fast` | Green |
| Slow | 100–499 ms | `hl_duration_slow` | Yellow |
| Very slow | 500–4999 ms | `hl_duration_very_slow` | Bold bright yellow |
| Critical | ≥ 5000 ms | `hl_duration_critical` | Bold red |

### Setting the thresholds

```
pgtail> set highlighting.duration.slow 50
pgtail> set highlighting.duration.very_slow 200
pgtail> set highlighting.duration.critical 1000
```

Or in `config.toml`:

```toml
[highlighting.duration]
slow = 50
very_slow = 200
critical = 1000
```

## Custom highlighters

### Adding patterns

```
pgtail> highlight add request_id "REQ-[A-Z]{3}-\d{6}" --style "cyan"
Added custom highlighter 'request_id' with pattern 'REQ-[A-Z]{3}-\d{6}'.

pgtail> highlight add txn_id "TXN:[0-9a-f]{16}" --style "bold magenta"
Added custom highlighter 'txn_id' with pattern 'TXN:[0-9a-f]{16}'.
```

Names start with a letter and use lowercase letters, digits, and underscores, and cannot reuse a built-in name. The
style defaults to `yellow`.

### Pattern syntax

Patterns use ripgrep's regular expression syntax, matched in linear time:

- `\d+`: one or more digits
- `[A-Z]{3}`: exactly three uppercase letters
- `[0-9a-f]+`: hex digits
- `\w+`: word characters
- `(?:...)`: a non-capturing group
- `(?i)...`: ignore case

Backreferences are not supported, and a pattern that can match an empty string is rejected.

### Styles

A style is a list of words:

- Colors: `red`, `green`, `cyan`, `bright_black`, `grey50`, CSS names such as `cornflowerblue`, and hex codes such
  as `#ff6b6b`
- Attributes: `bold`, `dim`, `italic`, `underline`, `reverse`, `strike`
- A background after `on`: `bold white on red`
- Or prefixed colors: `fg:#ffffff bg:ansired bold`

### Priority

Highlighters run in priority order, lowest first, and a later highlighter never recolors text an earlier one already
colored. Custom highlighters get priority 1050 and up by default, after the built-in ones.

```
pgtail> highlight add urgent "CRITICAL" --style "bold red" --priority 50
```

### Removing custom highlighters

```
pgtail> highlight remove request_id
Removed custom highlighter 'request_id'.
```

## Preview

See every highlighter at work on sample log lines:

```
pgtail> highlight preview
Highlight Preview (enabled)

Structural
  Timestamp with timezone and process ID
  2024-01-15 14:30:45.123 UTC [12345] LOG:  database system is ready
...
```

## Export and import

### Printing the settings as TOML

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

### Writing to a file

```
pgtail> highlight export --file ~/highlight-config.toml
Exported highlighting config to /home/you/highlight-config.toml
```

### Importing

```
pgtail> highlight import ~/highlight-config.toml
Imported highlighting config from /home/you/highlight-config.toml
```

## Resetting to the defaults

```
pgtail> highlight reset
Reset complete: enabled highlighting, enabled all highlighters, reset duration thresholds, removed custom highlighters.
```

## Regular expression highlights (REPL)

In the REPL, `highlight /pattern/` marks every match of a pattern with the theme's `highlight` style (black on
yellow in the dark theme) in streamed output, for the rest of the session:

```
pgtail> highlight /deadlock/      # Ignoring case
pgtail> highlight /Deadlock/c     # Case-sensitive
pgtail> highlight clear           # Remove them
```

## Saved settings

Highlighting settings live in `config.toml`:

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

## Theme integration

Highlighting colors come from the theme's `[ui]` table, in elements named `hl_*`:

```toml
[ui]
hl_duration_slow = { fg = "yellow" }
hl_duration_very_slow = { fg = "#ff8800" }
hl_duration_critical = { fg = "red", bold = true }
hl_sqlstate_error = { fg = "red" }
hl_error_name = { fg = "red" }
hl_identifier = { fg = "cyan" }
hl_relation = { fg = "green" }
hl_lsn_segment = { fg = "blue" }
hl_wal_segment = { fg = "magenta" }
```

The elements are `hl_timestamp_date`, `hl_timestamp_time`, `hl_timestamp_ms`, `hl_timestamp_tz`, `hl_pid`,
`hl_context`, `hl_sqlstate_success`, `hl_sqlstate_warning`, `hl_sqlstate_error`, `hl_sqlstate_internal`,
`hl_error_name`, `hl_duration_fast`, `hl_duration_slow`, `hl_duration_very_slow`, `hl_duration_critical`,
`hl_memory_value`, `hl_memory_unit`, `hl_statistics`, `hl_identifier`, `hl_relation`, `hl_schema`, `hl_lsn_segment`,
`hl_lsn_offset`, `hl_wal_segment`, `hl_txid`, `hl_host`, `hl_port`, `hl_user`, `hl_database`, `hl_ip`,
`hl_backend`, `hl_param`, `hl_lock_share`, `hl_lock_exclusive`, `hl_lock_wait`, `hl_checkpoint`, `hl_recovery`,
`hl_bool_true`, `hl_bool_false`, `hl_null`, `hl_oid`, and `hl_path`; SQL uses `sql_keyword`, `sql_identifier`,
`sql_string`, `sql_number`, `sql_operator`, `sql_comment`, and `sql_function`. See [Themes](/guide/themes/) for
creating a theme.

## Performance

Highlighting is built for high throughput:

- Keywords are found with an Aho-Corasick automaton, and every pattern runs on a linear-time engine over the raw
  UTF-8 bytes
- Lines longer than `max_length` (10,240 characters by default) are highlighted only up to that length
- Highlighters never overlap: each one skips text another already colored
