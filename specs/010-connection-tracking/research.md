# Research: Connection Tracking Dashboard

**Date**: 2025-12-17
**Feature**: 010-connection-tracking

## PostgreSQL Connection Log Messages

### Decision: Log message patterns to parse

PostgreSQL emits connection-related messages at LOG and FATAL levels. The following patterns are used:

#### Connection Events

1. **Connection Received** (before authentication):
   ```
   LOG:  connection received: host=192.168.1.100 port=54321
   LOG:  connection received: host=[local]
   ```

2. **Connection Authorized** (after successful auth):
   ```
   LOG:  connection authorized: user=postgres database=mydb application_name=psql
   LOG:  connection authorized: user=app_user database=production
   ```

3. **Disconnection** (on client disconnect):
   ```
   LOG:  disconnection: session time: 0:00:01.234 user=postgres database=mydb host=192.168.1.100 port=54321
   LOG:  disconnection: session time: 1:23:45.678 user=app_user database=production host=[local]
   ```

4. **Connection Failures** (FATAL level):
   ```
   FATAL:  too many connections for role "app_user"
   FATAL:  sorry, too many clients already
   FATAL:  connection limit exceeded for non-superusers
   FATAL:  password authentication failed for user "unknown"
   FATAL:  database "nonexistent" does not exist
   ```

### Rationale
- These patterns cover the connection lifecycle from receipt through authentication to disconnection
- Parsing the message field from LogEntry works for all formats (TEXT, CSV, JSON)
- CSV/JSON formats provide structured fields (user_name, database_name, application_name) that can supplement message parsing

### Alternatives Considered
1. **Query pg_stat_activity**: Rejected per spec - log-based tracking only
2. **Track only authorized connections**: Would miss connection attempts; less useful for debugging

## Connection State Tracking Strategy

### Decision: Use PID-based correlation

Track connections using PostgreSQL backend PID as the correlation key:
- Store pending connections (received but not yet authorized) keyed by PID
- On authorization, merge connection_received info with authorized info
- On disconnection, look up active connection by PID and calculate duration

### Rationale
- PID is present in all log formats (CSV/JSON provide it directly, TEXT requires regex)
- PIDs are unique within a session (until process terminates and PID is reused)
- Disconnection events include PID, enabling direct lookup

### Alternatives Considered
1. **Session ID tracking**: More reliable but only available in structured formats (CSV/JSON)
2. **Timestamp-based correlation**: Fragile, could match wrong events under high concurrency

## Active Connection Counting

### Decision: Maintain running count with event history

Track both:
1. **Event history** (deque maxlen=10,000): All connection events for trend analysis
2. **Active connections** (dict[int, ConnectionEvent]): Currently open connections keyed by PID

Active count = len(active_connections) at any point.

### Rationale
- Matches error_stats pattern for consistency
- Allows both summary views (count only) and detailed views (connection info)
- PID-keyed dict enables O(1) lookup for disconnection processing

### Alternatives Considered
1. **Count only**: Loses detail needed for aggregations
2. **Unlimited history**: Memory concerns for long-running sessions

## Aggregation Dimensions

### Decision: Support four aggregation dimensions

1. **By database** - `database_name` from LogEntry or parsed from message
2. **By user** - `user_name` from LogEntry or parsed from message
3. **By application** - `application_name` from LogEntry or parsed from message (default: "unknown")
4. **By source IP** - `remote_host` from LogEntry or parsed from "connection received" message

### Rationale
- These are the most commonly needed dimensions for connection troubleshooting
- All four are available in connection authorized/disconnection messages
- Source IP is also in "connection received" messages

### Alternatives Considered
1. **Backend type**: Available but less useful for most users
2. **Connection duration buckets**: Could add later as enhancement

## Watch Mode Implementation

### Decision: Reuse LogTailer with connection-specific callback

Watch mode follows the error_stats --live pattern:
1. Create LogTailer with `on_entry` callback for connection tracking
2. Display events in real-time with filters applied
3. Use ANSI escape codes for in-place updates

### Rationale
- Consistent with existing patterns
- Reuses proven infrastructure
- Keyboard interrupt handling already implemented

### Alternatives Considered
1. **Separate connection tailer class**: Over-engineering for this use case

## History and Trend Display

### Decision: 15-minute buckets for connection trends

Display connection trends using:
- Default window: 60 minutes
- Default bucket size: 15 minutes (4 data points)
- Show: connects, disconnects, net change per bucket

### Rationale
- Connection events are less frequent than errors, so larger buckets make sense
- 15-minute granularity matches spec requirement
- Sparkline visualization reusable from error_trend module

### Alternatives Considered
1. **5-minute buckets**: Too fine-grained for typical connection rates
2. **Hourly buckets**: Too coarse to detect leaks

## Filter Implementation

### Decision: Reuse field_filter pattern for connection filters

Connection filters use the same approach as existing field filters:
- `--db=name` filters by database_name
- `--user=name` filters by user_name
- `--app=name` filters by application_name
- Multiple filters use AND logic

### Rationale
- Consistent user experience with existing field filter command
- Reuses proven filter matching logic
- Intuitive flag syntax

### Alternatives Considered
1. **SQL-like filter syntax**: Over-complicated for the use case
2. **Regex filters**: Available via existing filter command if needed
