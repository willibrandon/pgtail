# Quickstart: Slow Query Detection and Highlighting

**Feature**: 004-slow-query

## Overview

Slow query detection automatically highlights PostgreSQL log entries containing query durations that exceed configurable thresholds. This helps you quickly spot performance issues while tailing logs.

## Basic Usage

### 1. Enable slow query highlighting

```
pgtail> slow 100 500 1000
```

This sets three thresholds:
- **Warning (yellow)**: queries > 100ms
- **Slow (bold yellow)**: queries > 500ms
- **Critical (red bold)**: queries > 1000ms

### 2. Tail logs normally

```
pgtail> tail 1
```

Slow queries will be automatically highlighted in the output.

### 3. View statistics

```
pgtail> stats
```

Shows count, average, and percentile breakdown of observed query durations.

## Examples

### Default thresholds (recommended for most apps)

```
pgtail> slow 100 500 1000
```

### Aggressive thresholds (high-performance systems)

```
pgtail> slow 10 50 100
```

### Lenient thresholds (batch processing)

```
pgtail> slow 1000 5000 10000
```

### Disable highlighting

```
pgtail> slow off
```

### Check current settings

```
pgtail> slow
```

## Prerequisites

For slow query detection to work, PostgreSQL must be configured to log query durations. Add one of these to `postgresql.conf`:

**Option 1: Log all query durations**
```
log_duration = on
```

**Option 2: Log only slow queries (recommended)**
```
log_min_duration_statement = 0   # Log all queries with duration
# OR
log_min_duration_statement = 100  # Log queries > 100ms
```

## Visual Reference

| Duration | Color | Appearance |
|----------|-------|------------|
| ≤ warning | Default | Normal text |
| > warning | Yellow | Warning level |
| > slow | Bold Yellow | Slow level |
| > critical | Bold Red | Critical level |

## Tips

1. **Start with defaults**: `slow 100 500 1000` works well for most web applications
2. **Adjust based on your baseline**: If most queries are <10ms, use more aggressive thresholds
3. **Use stats for insight**: The `stats` command helps you understand your query distribution
4. **Combine with filtering**: Use `filter /SELECT/` to focus on specific query types
