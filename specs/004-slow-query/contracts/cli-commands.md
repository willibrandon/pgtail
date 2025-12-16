# CLI Command Contracts: Slow Query Detection

**Feature**: 004-slow-query
**Date**: 2025-12-15

## Commands

### slow

Configure slow query detection and highlighting thresholds.

#### Syntax

```
slow [warning_ms slow_ms critical_ms | off]
```

#### Variants

**1. Display current configuration**
```
pgtail> slow
```

Output (when enabled):
```
Slow query highlighting: enabled
  Warning (yellow):      > 100ms
  Slow (yellow bold):    > 500ms
  Critical (red bold):   > 1000ms
```

Output (when disabled):
```
Slow query highlighting: disabled
Default thresholds: 100ms / 500ms / 1000ms

Usage: slow <warning> <slow> <critical>  Enable with custom thresholds
       slow off                          Disable highlighting
```

---

**2. Enable with custom thresholds**
```
pgtail> slow 100 500 1000
```

Success output:
```
Slow query thresholds set:
  Warning (yellow):      > 100ms
  Slow (yellow bold):    > 500ms
  Critical (red bold):   > 1000ms
```

Error output (invalid thresholds):
```
Error: Thresholds must be in ascending order: warning < slow < critical
```

Error output (non-numeric):
```
Error: All thresholds must be positive numbers
```

---

**3. Disable highlighting**
```
pgtail> slow off
```

Output:
```
Slow query highlighting disabled
```

---

### stats

Display query duration statistics for the current session.

#### Syntax

```
stats
```

#### Output

**When data available:**
```
Query Duration Statistics
─────────────────────────
  Queries:  1,234
  Average:  45.2ms

  Percentiles:
    p50:    12.3ms
    p95:    156.7ms
    p99:    892.4ms
    max:    2,341.5ms
```

**When no data:**
```
No query duration data available yet.
Durations are collected from log entries containing "duration: X ms" patterns.
```

---

## Visual Output Contract

### Slow Query Line Styling

When a log line contains a duration exceeding a threshold, the entire line is styled:

| Condition | Style | Example |
|-----------|-------|---------|
| duration > critical_ms | fg:red bold | `10:23:46.789 [12345] LOG    : duration: 1234.567 ms  statement: SELECT ...` |
| duration > slow_ms | fg:yellow bold | `10:23:45.789 [12345] LOG    : duration: 750.000 ms  statement: SELECT ...` |
| duration > warning_ms | fg:yellow | `10:23:45.456 [12345] LOG    : duration: 234.567 ms  statement: SELECT ...` |
| duration <= warning_ms | (default) | `10:23:45.123 [12345] LOG    : duration: 12.345 ms  statement: SELECT ...` |

**Precedence**: Slow query styling overrides regex highlighting when both match.

---

## Command Completion Contract

### slow command completion

```
pgtail> slow <TAB>
off    Disable slow query highlighting
```

### stats command completion

No arguments (simple command).

---

## Error Handling Contract

| Scenario | Behavior |
|----------|----------|
| `slow` with 1-2 args | Error: "Usage: slow <warning> <slow> <critical>" |
| `slow` with non-numeric args | Error: "All thresholds must be positive numbers" |
| `slow` with negative values | Error: "All thresholds must be positive numbers" |
| `slow` with wrong order | Error: "Thresholds must be in ascending order: warning < slow < critical" |
| `slow 0 100 200` | Error: "All thresholds must be positive numbers" |
| Malformed duration in log | Silently ignored (no highlighting applied) |
| Duration in seconds format | Converted to milliseconds for comparison |
