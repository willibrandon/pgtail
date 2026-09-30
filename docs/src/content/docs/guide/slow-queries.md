---
title: Slow queries
description: Highlight slow queries by duration thresholds and see query duration statistics.
---

pgtail reads the duration PostgreSQL logs for each statement, colors slow queries by configurable thresholds, and
collects duration statistics.

## Threshold levels

Slow query highlighting is on from the start, with three thresholds:

| Level | Default | Theme element | Color in the dark theme |
|-------|---------|---------------|-------------------------|
| Warning | > 100 ms | `slow_warning` | Yellow |
| Slow | > 500 ms | `slow_slow` | Bold yellow |
| Critical | > 1000 ms | `slow_critical` | Bold red |

An entry over a threshold is drawn in that level's style in tail mode's log, in streamed output (`tail --stream`), and
in `export --highlighted`. With slow query highlighting off, the
[`duration` highlighter](/guide/highlighting/#duration-threshold-coloring) still colors each duration by its own
thresholds.

## Setting thresholds

In the REPL, `slow` sets all three at once:

```
pgtail> slow 100 500 1000     # warning, slow, critical in ms
pgtail> slow                  # Show the current thresholds
pgtail> slow off              # Turn slow query highlighting off
```

In tail mode, `slow` takes one threshold and sets the others from it (slow at twice it, critical at five times),
redraws the log in the new colors, and the status bar shows it as `slow:>Nms`:

```
tail> slow 200        # warning 200 ms, slow 400 ms, critical 1000 ms
tail> slow off        # Turn it off (also: slow clear)
```

## Saving thresholds

`slow` lasts for the session. To keep thresholds, set them in the configuration:

```
pgtail> set slow.warn 50
pgtail> set slow.error 200
pgtail> set slow.critical 500
```

Or in `config.toml`:

```toml
[slow]
warn = 50        # Warning threshold (ms)
error = 200      # Slow threshold (ms)
critical = 500   # Critical threshold (ms)
```

## Query duration statistics

`stats` in the REPL summarizes the durations seen while tailing:

```
pgtail> stats
Query Duration Statistics
─────────────────────────
  Queries:  1,234
  Average:  45.2ms

  Percentiles:
    p50:    12.3ms
    p95:    234.5ms
    p99:    567.8ms
    max:    1234.5ms
```

Statistics are collected from every entry read, whatever the filters show.

## PostgreSQL configuration

For durations to appear in the log, set in `postgresql.conf`:

```ini
log_duration = on
# OR
log_min_duration_statement = 0  # Log every statement with its duration
```

Durations appear in the log as:

```
LOG:  duration: 234.567 ms
LOG:  duration: 1234.567 ms  statement: SELECT ...
```

## Notifications for slow queries

Get a desktop notification when a query exceeds a threshold:

```
notify on slow > 500ms
```

See [Notifications](/guide/notifications/) for more.
