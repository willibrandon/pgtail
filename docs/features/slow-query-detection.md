# Feature: Slow Query Detection and Highlighting

## Problem

Slow queries are a primary cause of PostgreSQL performance issues. While `log_min_duration_statement` can log slow queries, developers still need to:
- Visually identify slow queries among normal output
- Understand the distribution of query times
- Quickly spot queries exceeding different thresholds

Currently, duration information is in the log but not visually emphasized.

## Proposed Solution

Parse query duration from log entries and apply visual highlighting based on configurable thresholds. Slow queries get progressively more prominent colors (yellow → orange → red) based on severity.

## User Scenarios

### Scenario 1: Spotting Outliers
Developer tailing logs sees mostly white/default output. A query taking 500ms appears in yellow, catching attention. A 5-second query appears in red with bold, impossible to miss.

### Scenario 2: Custom Thresholds
DBA working on a high-performance system sets aggressive thresholds: warn at 10ms, error at 100ms. Default thresholds are too lenient for their use case.

### Scenario 3: Duration Stats
Developer runs `stats` command and sees: "Last 5 minutes: 1,234 queries, avg 12ms, p95 45ms, p99 230ms, max 1.2s"

## Configuration

```
pgtail> slow 100 500 1000
Slow query thresholds set:
  Warning (yellow): > 100ms
  Slow (orange): > 500ms
  Critical (red): > 1000ms

pgtail> slow off
Slow query highlighting disabled

pgtail> slow
Current thresholds: 100ms / 500ms / 1000ms
```

## Visual Design

```
10:23:45.123 [12345] LOG    : duration: 12.345 ms  statement: SELECT ...
10:23:45.456 [12345] LOG    : duration: 234.567 ms  statement: SELECT ...  ← Yellow
10:23:46.789 [12345] LOG    : duration: 1234.567 ms  statement: SELECT ... ← Red/Bold
```

## Success Criteria

1. Duration extracted from standard PostgreSQL log format
2. Three configurable thresholds with distinct colors
3. Thresholds persist across session (saved to config)
4. Works with both `log_duration` and `log_min_duration_statement` output
5. Stats command shows useful percentile breakdown
6. No false positives on non-duration numbers in logs

## Out of Scope

- Query EXPLAIN analysis
- Historical trending/graphing
- Alerts/notifications (separate feature)
- Query plan analysis
