# Feature: Time-Based Filtering

## Problem

When investigating issues, developers often know the approximate time window:
- "The error happened around 2:30pm"
- "Show me the last 5 minutes"
- "What happened between deploy and rollback?"

Currently, users must visually scan timestamps or grep externally.

## Proposed Solution

Add time-based filtering to show only log entries within a specified time range. Support relative times ("last 5m"), absolute times ("since 14:30"), and ranges ("between 14:30 and 15:00").

## User Scenarios

### Scenario 1: Recent History
Developer just saw an error and wants context:
```
pgtail> since 5m
Showing logs from last 5 minutes
```

### Scenario 2: Specific Time Window
On-call engineer investigating alert that fired at 3:47am:
```
pgtail> since 03:45
Showing logs since 03:45:00 today

pgtail> between 03:45 03:50
Showing logs between 03:45:00 and 03:50:00
```

### Scenario 3: Tail from Time
Developer wants to start tailing from a specific point:
```
pgtail> tail 0 --since 10m
Starting tail from 10 minutes ago
```

## Commands

```
since <time>           Show logs since time
                       Examples: 5m, 1h, 14:30, 2024-01-15T14:30

until <time>           Show logs until time (stops at time, no follow)

between <start> <end>  Show logs in range

since clear            Remove time filter, resume normal tail
```

## Time Format Support

| Format | Example | Meaning |
|--------|---------|---------|
| Relative | 5m, 30s, 2h, 1d | Last N minutes/seconds/hours/days |
| Time only | 14:30, 14:30:45 | Today at specified time |
| Date + time | 2024-01-15T14:30 | Specific datetime |
| ISO 8601 | 2024-01-15T14:30:00Z | Full ISO format |

## Behavior Notes

- `since` with live tail: shows history then continues following
- `since` without tail: shows matching entries from log file
- If time is in future, waits for entries (or errors)
- Times assume local timezone unless Z suffix

## Success Criteria

1. Relative times parsed correctly (m, s, h, d suffixes)
2. Absolute times work with common formats
3. Time filter combines with level and regex filters
4. Seeking to time in large log files is efficient (binary search if possible)
5. Clear feedback on what time range is active
6. Graceful handling of missing/gaps in timestamps

## Out of Scope

- Timezone conversion commands
- Calendar/date picker UI
- Log file archival/retrieval from rotated files
