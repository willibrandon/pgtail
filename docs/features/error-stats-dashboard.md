# Feature: Error Statistics Dashboard

## Problem

When debugging issues or monitoring health, developers need to understand error patterns:
- What types of errors are occurring?
- Are errors increasing or decreasing?
- Which errors are most frequent?
- What's the error rate relative to normal activity?

Scrolling through logs makes it hard to see patterns and trends.

## Proposed Solution

Track error events and provide a dashboard showing error statistics, trends, and breakdowns by type. Support both point-in-time summaries and live updating views.

## User Scenarios

### Scenario 1: Error Summary
Developer investigating reports of issues:
```
pgtail> errors
Last hour: 47 errors, 12 warnings

By type:
  42P01 relation does not exist    23
  23505 unique_violation           12
  42703 column does not exist       8
  57014 query_canceled              4

By level:
  ERROR     45
  FATAL      2
  WARNING   12
```

### Scenario 2: Error Trend
DBA checking if recent deploy caused issues:
```
pgtail> errors --trend
Error rate (per minute):

12:00 ▁▁▁▂▁▁▁▁▂▁  avg 0.8
12:30 ▁▂▁▁▁▁▁▁▁▁  avg 0.6
13:00 ▂▃▅▇█▇▅▄▃▂  avg 4.2  ← spike at 13:15
13:30 ▂▂▂▁▁▁▁▁▁▁  avg 0.9
```

### Scenario 3: Live Error Counter
Ops monitoring during deployment:
```
pgtail> errors --live
Errors: 3 | Warnings: 7 | Last error: 2s ago
[Updates in place]
```

### Scenario 4: Specific Error Investigation
Developer seeing many unique violations:
```
pgtail> errors --code 23505
23505 unique_violation: 12 occurrences

Recent examples:
  10:23:45 duplicate key value (id)=(123) - table users
  10:23:46 duplicate key value (email)=(foo@bar.com) - table users
  10:23:47 duplicate key value (id)=(456) - table orders
```

## Commands

```
errors                   Summary of recent errors
errors --trend           Show error rate over time
errors --live            Live updating counter
errors --code <SQLSTATE> Filter by error code
errors --since <time>    Time window for stats
errors clear             Reset counters
```

## SQL State Categories

Group errors by category:
- Class 23: Integrity constraint violation
- Class 42: Syntax error or access rule violation
- Class 53: Insufficient resources
- Class 57: Operator intervention
- Class 58: System error

## Success Criteria

1. Track ERROR, FATAL, PANIC, WARNING levels
2. Parse SQLSTATE codes from log entries
3. Summary shows top N error types
4. Trend visualization fits in terminal
5. Live mode updates in place (no scroll)
6. Stats survive across commands (session-scoped)
7. Memory bounded (sliding window, not unbounded)

## Out of Scope

- Persistent storage of stats
- Alerting based on thresholds
- Comparison between time periods
- Error correlation/grouping by root cause
