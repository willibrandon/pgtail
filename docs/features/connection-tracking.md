# Feature: Connection Tracking Dashboard

## Problem

Developers and DBAs need visibility into who/what is connected to PostgreSQL:
- Which applications are connected?
- Where are connections coming from?
- How many connections per user/database?
- When did connections open/close?

This information is in the logs but scattered across many entries.

## Proposed Solution

Track connection events (connect/disconnect) and provide a dashboard view showing active connections aggregated by user, database, application, and source IP.

## User Scenarios

### Scenario 1: Connection Overview
DBA wants to see current connection distribution:
```
pgtail> connections
Active connections: 47

By database:
  production    32
  analytics      8
  test           7

By user:
  app_user      28
  readonly      12
  admin          7

By application:
  rails         20
  sidekiq        8
  psql           5
  unknown       14
```

### Scenario 2: Connection History
Developer investigating connection leak:
```
pgtail> connections --history
Last hour: 234 connects, 180 disconnects, +54 net

10:00  40 active
10:15  45 active (+5)
10:30  52 active (+7)
10:45  61 active (+9)  ← potential leak
```

### Scenario 3: Watch Specific App
Developer monitoring their application:
```
pgtail> connections --watch app=myapp
Watching connections for application: myapp
[+] 10:23:45 myapp connected from 10.0.1.5 (user: app_user, db: production)
[-] 10:23:47 myapp disconnected (duration: 2.3s)
```

## Commands

```
connections              Show current connection summary
connections --history    Show connection counts over time
connections --watch      Live connection events
connections --app=X      Filter by application
connections --user=X     Filter by user
connections --db=X       Filter by database
```

## Log Events Tracked

- `LOG: connection received: host=X port=Y`
- `LOG: connection authorized: user=X database=Y application_name=Z`
- `LOG: disconnection: session time: X`
- `FATAL: too many connections`
- `FATAL: connection limit exceeded`

## Success Criteria

1. Track connections from log events (no direct DB query needed)
2. Summary view shows useful aggregations
3. History shows trends over configurable window
4. Watch mode shows real-time connect/disconnect
5. Detect potential connection leaks (opens >> closes)
6. Works with default log settings (no special config required)

## Out of Scope

- Querying pg_stat_activity directly
- Connection pooler (pgbouncer) awareness
- Killing connections
- Connection limits/alerts
