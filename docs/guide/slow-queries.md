# Slow Query Detection

pgtail can highlight and track slow queries based on configurable duration thresholds.

## Enabling Slow Query Highlighting

In tail mode:

```
slow 100           # Highlight queries > 100ms
slow 500           # Highlight queries > 500ms
```

## Threshold Levels

Queries are highlighted based on three severity levels:

| Level | Default | Color |
|-------|---------|-------|
| Warning | > 100ms | Yellow |
| Slow | > 500ms | Bold yellow |
| Critical | > 1000ms | Bold red |

## Configuring Thresholds

Set thresholds in config:

```
pgtail> set slow.warn 50
pgtail> set slow.error 200
pgtail> set slow.critical 500
```

Or edit `config.toml`:

```toml
[slow]
warn = 50        # Warning threshold (ms)
error = 200      # Slow threshold (ms)
critical = 500   # Critical threshold (ms)
```

## Query Duration Statistics

View statistics for queries observed during tailing:

```
tail> errors
```

Shows:

```
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

## PostgreSQL Configuration

For duration tracking, enable in `postgresql.conf`:

```ini
log_duration = on
# OR
log_min_duration_statement = 0  # Log all with duration
```

Duration appears in logs as:

```
LOG:  duration: 234.567 ms
LOG:  duration: 1.234 s  statement: SELECT ...
```

## Notifications for Slow Queries

Get notified when queries exceed a threshold:

```
notify on slow > 500ms
```

See [Notifications](notifications.md) for more options.
