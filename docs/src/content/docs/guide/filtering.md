---
title: Filtering
description: Filter by level, regular expression, structured field, and time, and combine them.
---

pgtail combines several kinds of filter. In tail mode each change redraws the log from every entry read so far, so
widening or clearing a filter brings back entries it hid.

## Level filtering

Filter entries by severity. In tail mode the command is `level`; in the REPL it is `levels`.

### Basic level filter

```
level error      # ERROR only
level warning    # WARNING only
level log        # LOG only
level all        # Every level (clears the level filter)
```

### Severity ranges

Levels run from most to least severe: PANIC, FATAL, ERROR, WARNING, NOTICE, LOG, INFO, DEBUG1 through DEBUG5.

```
level error+     # ERROR and more severe (FATAL, PANIC)
level warning+   # WARNING, ERROR, FATAL, PANIC
level warning-   # WARNING and less severe (NOTICE, LOG, INFO, DEBUG1-5)
```

### Several levels

```
level error,warning      # ERROR and WARNING
level error warning      # The same
levels ERROR WARNING     # In the REPL
```

### Level abbreviations

| Abbreviation | Level |
|--------------|-------|
| `e`, `err` | ERROR |
| `w`, `warn` | WARNING |
| `f`, `fat` | FATAL |
| `p`, `pan` | PANIC |
| `n`, `not`, `ntc` | NOTICE |
| `l` | LOG |
| `i`, `inf` | INFO |
| `d`, `dbg`, `debug` | DEBUG1 |

Examples:

```
level e+    # ERROR and above
level w     # WARNING only
```

Level names ignore case. The `default.levels` setting chooses the levels pgtail starts with (see
[Configuration](/configuration/)).

## Regular expression filtering

Filter by a pattern in the log message:

```
filter /deadlock/        # Lines matching 'deadlock', ignoring case
filter /deadlock/c       # Case-sensitive
```

### Combining patterns

| Syntax | Meaning |
|--------|---------|
| `filter /pattern/` | Show only lines matching the pattern, replacing the earlier include patterns |
| `filter +/pattern/` | Also show lines matching this pattern (OR) |
| `filter &/pattern/` | Lines must also match this pattern (AND) |
| `filter -/pattern/` | Hide lines matching this pattern |
| `filter clear` | Remove every regular expression and field filter |
| `filter` | Show the active filters |

For example, to see statements on `users` or `orders` that are not `SELECT`s:

```
filter /users/
filter +/orders/
filter -/SELECT/
```

### Pattern syntax

Patterns use the regular expression syntax of ripgrep, matched by a linear-time engine: matching takes time
proportional to the line whatever the pattern, so no pattern can stall the log. Classes (`\d`, `\w`, `[a-z]`),
repetition (`+`, `*`, `{3}`), alternation, groups, and anchors all work; backreferences do not.

```
filter /user_\d+/            # 'user_' followed by digits
filter /timeout|deadlock/    # Either word
```

The REPL toolbar shows the first pattern, with `i` when it ignores case and `+N more` when there are others; tail
mode's status bar shows the first include pattern.

## Field filtering

Filter by structured fields (CSV and JSON log formats only).

### Available fields

| Field | Description |
|-------|-------------|
| `app` / `application` | Application name |
| `db` / `database` | Database name |
| `user` | User name |
| `pid` | Process ID |
| `backend` | Backend type |
| `host` / `ip` / `client` / `connection_from` | Connection source |

### Examples

```
filter app=myapp         # Application name
filter db=production     # Database name
filter user=postgres     # User name
```

Field filters combine with AND, and `filter clear` removes them.

:::caution[Format requirement]
Field filtering needs the CSV or JSON log format. With the TEXT format, pgtail warns that a field filter has no
effect.
:::

## Time filtering

See [Time filters](/guide/time-filters/) for every time format.

```
since 5m                 # The last 5 minutes
until 14:00              # Before 2 PM today
between 14:00 16:00      # Between 2 and 4 PM
```

## Filter order

Filters run cheapest first:

1. **Time filter**: one comparison
2. **Level filter**: a set lookup
3. **Field filter**: string comparisons
4. **Regular expression filter**: a scan of the message

## Combining filters

All filter kinds combine with AND:

```
level error+
filter /timeout/
since 1h
```

This shows only ERROR, FATAL, and PANIC entries containing "timeout" from the last hour.

## Filter anchor

The level, regular expression, and time filters in effect when tail mode starts (for example from
`tail 0 --since 1h`) are its **anchor**:

- `clear` returns to the anchor's filters
- `clear force` removes every filter, the anchor's included, and empties the log; new entries appear as they arrive
