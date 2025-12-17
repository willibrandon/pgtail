# Quickstart: Connection Tracking Dashboard

**Date**: 2025-12-17
**Feature**: 010-connection-tracking

## Overview

The connection tracking feature adds the `connections` command to pgtail, providing visibility into PostgreSQL connection events parsed from log files.

## Prerequisites

- pgtail installed and functional
- PostgreSQL instance with accessible log files
- Connection logging enabled (`log_connections = on`, `log_disconnections = on`)

## Basic Usage

### 1. Start tailing a log

```
pgtail> list
  1  PostgreSQL 15 (pgrx)    ~/.pgrx/data-15/log/postgresql.log

pgtail> tail 1
Tailing /Users/dev/.pgrx/data-15/log/postgresql.log (Ctrl+C to stop)
```

### 2. View connection summary

```
pgtail> connections
Active connections: 5

By database:
  mydb          3
  postgres      2

By user:
  postgres      4
  app_user      1

By application:
  psql          3
  unknown       2
```

### 3. Watch live connections

```
pgtail> connections --watch
Watching connections (Ctrl+C to exit)
[+] 14:30:15 psql connected from [local] (user: postgres, db: mydb)
[-] 14:30:18 psql disconnected (duration: 3.2s, user: postgres, db: mydb)
```

### 4. View connection history

```
pgtail> connections --history
Connection history (last 60 min)

Total: 45 connects, 40 disconnects (+5 net)

Timeline (15-min buckets):
14:00   3 active
14:15   4 active (+1)
14:30   5 active (+1)
14:45   5 active (0)
```

### 5. Filter by criteria

```
pgtail> connections --db=mydb
Active connections to 'mydb': 3

By user:
  postgres      2
  app_user      1

pgtail> connections --watch app=psql
Watching connections for app=psql (Ctrl+C to exit)
[+] 14:32:00 psql connected from [local] (user: postgres, db: mydb)
```

### 6. Clear statistics

```
pgtail> connections clear
Connection statistics cleared.
```

## Typical Workflows

### Investigating Connection Leaks

1. Start `connections --history` to check trends
2. Look for increasing "net" connections over time
3. Use `--app=X` to identify which application is leaking
4. Use `--watch app=X` to monitor that application's behavior

### Monitoring Application Deployment

1. Start `connections --watch app=myapp`
2. Deploy new version of application
3. Observe connection patterns (old instances disconnecting, new ones connecting)
4. Verify connection count stabilizes

### Capacity Planning

1. Run `connections` periodically during peak hours
2. Note "By database" and "By user" distributions
3. Identify which databases/users consume most connections
4. Use `--history` to understand connection patterns over time

## Tips

- Connection tracking starts when you begin tailing - historical connections before `tail` are not tracked
- Statistics are session-scoped and reset when you exit pgtail
- Use `connections clear` to reset statistics mid-session
- The `[!]` indicator in watch mode highlights connection failures (FATAL errors)
