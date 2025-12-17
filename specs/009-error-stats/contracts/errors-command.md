# CLI Contract: errors Command

**Feature**: 009-error-stats
**Date**: 2025-12-16

## Command Synopsis

```
errors [--trend | --live | --code CODE | --since TIME | clear]
```

## Description

Display error statistics for the current tailing session. Tracks ERROR, FATAL, PANIC, and WARNING level log entries and provides summaries, trends, and detailed breakdowns.

## Subcommands and Options

### Default (no arguments)

```
errors
```

Display error summary for the session.

**Output Format**:
```
Error Statistics (last hour)
─────────────────────────────
Errors: 47  Warnings: 12

By type:
  42P01 undefined_table           23
  23505 unique_violation          12
  42703 undefined_column           8
  57014 query_canceled             4

By level:
  ERROR     45
  FATAL      2
  WARNING   12
```

**Exit Conditions**:
- If no errors tracked: "No errors recorded in this session."
- If not tailing: "Error tracking requires an active tail session."

### --trend

```
errors --trend
```

Display error rate visualization over time.

**Output Format**:
```
Error rate (per minute):

12:00 ▁▁▁▂▁▁▁▁▂▁  avg 0.8
12:30 ▁▂▁▁▁▁▁▁▁▁  avg 0.6
13:00 ▂▃▅▇█▇▅▄▃▂  avg 4.2  ← spike at 13:15
13:30 ▂▂▁▁▁▁▁▁▁▁  avg 0.9
```

**Behavior**:
- Shows last 60 minutes by default
- Each row is 30 minutes (30 one-minute buckets)
- Sparkline scales to max value in the row
- Annotates significant spikes (>2x average)
- Terminal width determines number of buckets shown

### --live

```
errors --live
```

Display live updating error counter.

**Output Format**:
```
Errors: 3 | Warnings: 7 | Last error: 2s ago
```

**Behavior**:
- Updates in place (no scrolling)
- Updates every 500ms
- Press Ctrl+C to exit live mode
- Returns to command prompt on exit

### --code CODE

```
errors --code 23505
errors --code 42P01
```

Filter statistics by SQLSTATE code.

**Output Format**:
```
23505 unique_violation: 12 occurrences

Recent examples:
  10:23:45 duplicate key value (id)=(123) - table users
  10:23:46 duplicate key value (email)=(foo@bar.com) - table users
  10:23:47 duplicate key value (id)=(456) - table orders
```

**Arguments**:
- CODE: 5-character SQLSTATE code (e.g., "23505", "42P01")

**Exit Conditions**:
- Invalid code format: "Invalid SQLSTATE code format. Expected 5 characters."
- No matches: "No errors with code {CODE} recorded."

### --since TIME

```
errors --since 30m
errors --since 1h
errors --since 14:30
```

Scope statistics to a time window.

**Arguments**:
- TIME: Time specification (same format as `since` command)
  - Relative: `5m`, `30s`, `2h`, `1d`
  - Time only: `14:30`, `14:30:45`
  - ISO 8601: `2024-01-15T14:30`

**Behavior**:
- Filters events to those after the specified time
- Shows the time window in output header
- Combines with other options (e.g., `errors --since 30m --code 23505`)

### clear

```
errors clear
```

Reset all error statistics.

**Output**:
```
Error statistics cleared.
```

**Behavior**:
- Resets all counters to zero
- Clears the event buffer
- New tracking starts from this point

## Option Combinations

| Combination | Valid | Behavior |
|-------------|-------|----------|
| `errors` | Yes | Show summary |
| `errors --trend` | Yes | Show trend |
| `errors --live` | Yes | Start live mode |
| `errors --code 23505` | Yes | Filter by code |
| `errors --since 30m` | Yes | Filter by time |
| `errors --since 30m --code 23505` | Yes | Filter by both |
| `errors --trend --since 1h` | Yes | Trend for last hour |
| `errors --live --since 30m` | No | Invalid: live mode doesn't support time filter |
| `errors clear --trend` | No | Invalid: clear doesn't combine with other options |

## Error Messages

| Condition | Message |
|-----------|---------|
| Not tailing | "Error tracking requires an active tail session. Use 'tail <id>' first." |
| No errors | "No errors recorded in this session." |
| Invalid code | "Invalid SQLSTATE code format. Expected 5 characters (e.g., 23505)." |
| No matching code | "No errors with code {CODE} recorded." |
| Invalid time | "Invalid time format. Use relative (5m, 1h) or absolute (14:30, ISO8601)." |
| Invalid combination | "Cannot use --live with --since or --code filters." |

## Completion Support

The `errors` command provides tab completion for:

1. **Subcommands**: `clear`
2. **Flags**: `--trend`, `--live`, `--code`, `--since`
3. **Code values** (after `--code`): Common SQLSTATE codes with descriptions
4. **Time values** (after `--since`): `5m`, `30m`, `1h`, `2h`, `1d`, `clear`

## Examples

```bash
# Basic error summary
pgtail> errors
Error Statistics (last hour)
─────────────────────────────
Errors: 47  Warnings: 12
...

# View error trend
pgtail> errors --trend
Error rate (per minute):
...

# Live monitoring during deployment
pgtail> errors --live
Errors: 3 | Warnings: 7 | Last error: 2s ago
^C

# Investigate specific error type
pgtail> errors --code 23505
23505 unique_violation: 12 occurrences
...

# Last 30 minutes only
pgtail> errors --since 30m
Error Statistics (since 14:30)
─────────────────────────────
Errors: 8  Warnings: 2
...

# Reset and start fresh
pgtail> errors clear
Error statistics cleared.
```
