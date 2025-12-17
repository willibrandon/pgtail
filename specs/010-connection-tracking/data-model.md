# Data Model: Connection Tracking Dashboard

**Date**: 2025-12-17
**Feature**: 010-connection-tracking

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ConnectionStats                         │
│  (Session aggregator - mirrors ErrorStats pattern)           │
├─────────────────────────────────────────────────────────────┤
│  - _events: deque[ConnectionEvent] (max 10,000)             │
│  - _active: dict[int, ConnectionEvent]  (PID → connection)  │
│  - session_start: datetime                                   │
│  - connect_count: int                                        │
│  - disconnect_count: int                                     │
├─────────────────────────────────────────────────────────────┤
│  + add(entry: LogEntry) → bool                              │
│  + clear() → None                                            │
│  + is_empty() → bool                                         │
│  + active_count() → int                                      │
│  + get_by_database() → dict[str, int]                       │
│  + get_by_user() → dict[str, int]                           │
│  + get_by_application() → dict[str, int]                    │
│  + get_by_host() → dict[str, int]                           │
│  + get_events_since(datetime) → list[ConnectionEvent]       │
│  + get_trend_buckets(minutes: int) → list[tuple[int,int]]   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ contains
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     ConnectionEvent                          │
│  (Immutable event record - frozen dataclass)                 │
├─────────────────────────────────────────────────────────────┤
│  timestamp: datetime                                         │
│  event_type: ConnectionEventType (CONNECT | DISCONNECT)      │
│  pid: int | None                                             │
│  user: str | None                                            │
│  database: str | None                                        │
│  application: str | None  (default: "unknown")               │
│  host: str | None                                            │
│  port: int | None                                            │
│  duration_seconds: float | None  (disconnect only)           │
├─────────────────────────────────────────────────────────────┤
│  + from_log_entry(entry: LogEntry) → ConnectionEvent | None │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   ConnectionEventType                        │
│  (Enum for event classification)                             │
├─────────────────────────────────────────────────────────────┤
│  CONNECT = "connect"                                         │
│  DISCONNECT = "disconnect"                                   │
│  CONNECTION_FAILED = "failed"  (FATAL connection errors)     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   ConnectionFilter                           │
│  (Filter criteria for display commands)                      │
├─────────────────────────────────────────────────────────────┤
│  database: str | None                                        │
│  user: str | None                                            │
│  application: str | None                                     │
│  host: str | None                                            │
├─────────────────────────────────────────────────────────────┤
│  + matches(event: ConnectionEvent) → bool                   │
│  + is_empty() → bool                                         │
└─────────────────────────────────────────────────────────────┘
```

## Entity Details

### ConnectionEvent

Represents a single connection or disconnection event parsed from PostgreSQL logs.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| timestamp | datetime | When the event occurred | LogEntry.timestamp |
| event_type | ConnectionEventType | CONNECT, DISCONNECT, or CONNECTION_FAILED | Parsed from message |
| pid | int \| None | PostgreSQL backend process ID | LogEntry.pid |
| user | str \| None | Database user name | LogEntry.user_name or message |
| database | str \| None | Database name | LogEntry.database_name or message |
| application | str \| None | Client application name | LogEntry.application_name or message |
| host | str \| None | Client IP address or "[local]" | LogEntry.remote_host or message |
| port | int \| None | Client port number | LogEntry.remote_port or message |
| duration_seconds | float \| None | Session duration (disconnect only) | Parsed from message |

**Validation Rules**:
- timestamp is required (default to now() if LogEntry.timestamp is None)
- event_type is required
- application defaults to "unknown" if empty/None
- duration_seconds only valid when event_type is DISCONNECT

**Factory Method**: `from_log_entry(entry: LogEntry) → ConnectionEvent | None`
- Returns None if entry is not a connection-related message
- Parses message content for connection details
- Extracts structured fields when available (CSV/JSON formats)

### ConnectionStats

Session-scoped aggregator for connection metrics. Follows the ErrorStats pattern.

| Field | Type | Description |
|-------|------|-------------|
| _events | deque[ConnectionEvent] | History of all events (max 10,000) |
| _active | dict[int, ConnectionEvent] | Currently active connections by PID |
| session_start | datetime | When tracking started |
| connect_count | int | Total connections seen |
| disconnect_count | int | Total disconnections seen |

**Key Methods**:

| Method | Returns | Description |
|--------|---------|-------------|
| add(entry) | bool | Process LogEntry, return True if connection event |
| clear() | None | Reset all statistics |
| is_empty() | bool | True if no events tracked |
| active_count() | int | Number of currently active connections |
| get_by_database() | dict[str, int] | Active connections per database |
| get_by_user() | dict[str, int] | Active connections per user |
| get_by_application() | dict[str, int] | Active connections per application |
| get_by_host() | dict[str, int] | Active connections per host |
| get_events_since(dt) | list[ConnectionEvent] | Events after timestamp |
| get_trend_buckets(min) | list[tuple[int, int]] | (connects, disconnects) per bucket |

**State Transitions**:
1. On CONNECT event: Add to _events, add to _active[pid], increment connect_count
2. On DISCONNECT event: Add to _events, remove from _active[pid], increment disconnect_count
3. On clear(): Reset all fields, set new session_start

### ConnectionEventType

Enum classifying connection events:

| Value | Description | Log Pattern |
|-------|-------------|-------------|
| CONNECT | Successful connection | "connection authorized:" |
| DISCONNECT | Client disconnected | "disconnection:" |
| CONNECTION_FAILED | Connection failed | FATAL level connection errors |

### ConnectionFilter

Filter criteria for the `connections` command display.

| Field | Type | Description |
|-------|------|-------------|
| database | str \| None | Filter by database name |
| user | str \| None | Filter by user name |
| application | str \| None | Filter by application name |
| host | str \| None | Filter by client host |

**Match Logic**: All non-None fields must match (AND logic). Empty filter matches all.

## Message Parsing Patterns

### connection authorized
```regex
connection authorized: user=(?P<user>\S+) database=(?P<database>\S+)(?:\s+application_name=(?P<application>\S+))?
```

### disconnection
```regex
disconnection: session time: (?P<duration>[\d:\.]+) user=(?P<user>\S+) database=(?P<database>\S+) host=(?P<host>\S+)(?:\s+port=(?P<port>\d+))?
```

### connection received
```regex
connection received: host=(?P<host>\S+)(?:\s+port=(?P<port>\d+))?
```

## Integration Points

### AppState
Add `connection_stats: ConnectionStats` field (similar to `error_stats: ErrorStats`)

### LogTailer
Add `on_connection` callback or reuse `on_entry` for connection tracking

### Commands
Register `connections` command in `commands.py` and `PgtailCompleter`
