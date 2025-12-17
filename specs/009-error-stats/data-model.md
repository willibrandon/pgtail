# Data Model: Error Statistics Dashboard

**Feature**: 009-error-stats
**Date**: 2025-12-16

## Entities

### ErrorEvent

Represents a single tracked error occurrence. Lightweight wrapper around relevant LogEntry fields.

```python
@dataclass(frozen=True)
class ErrorEvent:
    """A tracked error or warning event."""

    timestamp: datetime
    level: LogLevel
    sql_state: str | None  # SQLSTATE code (e.g., "23505")
    message: str           # First 200 chars of message
    pid: int | None
    database: str | None
    user: str | None

    @classmethod
    def from_entry(cls, entry: LogEntry) -> "ErrorEvent":
        """Create ErrorEvent from a LogEntry."""
        return cls(
            timestamp=entry.timestamp or datetime.now(),
            level=entry.level,
            sql_state=entry.sql_state,
            message=entry.message[:200] if entry.message else "",
            pid=entry.pid,
            database=entry.database_name,
            user=entry.user_name,
        )
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | datetime | Yes | When the error occurred |
| level | LogLevel | Yes | Severity (ERROR, FATAL, PANIC, WARNING) |
| sql_state | str | No | SQLSTATE code if available |
| message | str | Yes | Truncated error message |
| pid | int | No | Backend process ID |
| database | str | No | Database name if available |
| user | str | No | User name if available |

**Validation**:
- timestamp must not be None (defaults to now if not in log)
- level must be in {PANIC, FATAL, ERROR, WARNING}
- message is truncated to 200 characters

### ErrorStats

Session-scoped aggregator for error statistics. Main state container.

```python
@dataclass
class ErrorStats:
    """Session-scoped error statistics aggregator."""

    _events: deque[ErrorEvent]  # Sliding window of events
    _max_entries: int = 10000

    # Counters (maintained incrementally)
    error_count: int = 0      # PANIC + FATAL + ERROR
    warning_count: int = 0    # WARNING only

    # Timestamps for tracking
    session_start: datetime
    last_error_time: datetime | None = None
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| _events | deque[ErrorEvent] | Yes | Sliding window of recent events |
| _max_entries | int | Yes | Maximum events to retain (default 10000) |
| error_count | int | Yes | Running count of errors |
| warning_count | int | Yes | Running count of warnings |
| session_start | datetime | Yes | When tracking started |
| last_error_time | datetime | No | Timestamp of most recent error |

**Methods**:
| Method | Description |
|--------|-------------|
| `add(entry: LogEntry)` | Add a log entry if it's an error/warning |
| `clear()` | Reset all statistics |
| `is_empty()` -> bool | Check if any events tracked |
| `get_by_level()` -> dict[LogLevel, int] | Count by severity level |
| `get_by_code()` -> dict[str, int] | Count by SQLSTATE code |
| `get_events_since(dt)` -> list[ErrorEvent] | Events after timestamp |
| `get_trend_buckets(minutes)` -> list[int] | Per-minute counts for trend |

### SQLStateInfo

Static lookup data for SQLSTATE code descriptions.

```python
@dataclass(frozen=True)
class SQLStateInfo:
    """Information about a SQLSTATE error code."""

    code: str        # e.g., "23505"
    name: str        # e.g., "unique_violation"
    category: str    # e.g., "Integrity Constraint Violation"
    class_code: str  # e.g., "23"
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | str | Yes | 5-character SQLSTATE code |
| name | str | Yes | Snake_case error name |
| category | str | Yes | Human-readable category |
| class_code | str | Yes | First 2 characters of code |

**Static Data**:
```python
SQLSTATE_CATEGORIES: dict[str, str] = {
    "23": "Integrity Constraint Violation",
    "42": "Syntax Error or Access Rule Violation",
    "53": "Insufficient Resources",
    "57": "Operator Intervention",
    "58": "System Error",
    # ... other categories
}

SQLSTATE_CODES: dict[str, SQLStateInfo] = {
    "23505": SQLStateInfo("23505", "unique_violation", ...),
    # ... ~100 common codes
}
```

### TrendBucket

Aggregated data for a single time bucket in trend visualization.

```python
@dataclass
class TrendBucket:
    """A time bucket for trend visualization."""

    start_time: datetime
    end_time: datetime
    error_count: int
    warning_count: int
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_time | datetime | Yes | Bucket start timestamp |
| end_time | datetime | Yes | Bucket end timestamp |
| error_count | int | Yes | Errors in this bucket |
| warning_count | int | Yes | Warnings in this bucket |

## Relationships

```
┌─────────────────┐
│    AppState     │
│  (cli.py)       │
└────────┬────────┘
         │ has one
         ▼
┌─────────────────┐
│   ErrorStats    │
│ (error_stats.py)│
└────────┬────────┘
         │ contains many
         ▼
┌─────────────────┐
│   ErrorEvent    │
│ (error_stats.py)│
└────────┬────────┘
         │ references
         ▼
┌─────────────────┐
│  SQLStateInfo   │
│ (error_stats.py)│
└─────────────────┘
```

## State Transitions

### ErrorStats Lifecycle

```
┌────────────────┐
│    Created     │
│ (session start)│
└───────┬────────┘
        │
        ▼
┌────────────────┐     add()      ┌────────────────┐
│    Empty       │ ──────────────▶│   Tracking     │
│ (no events)    │                │ (has events)   │
└───────┬────────┘                └───────┬────────┘
        │                                 │
        │          clear()                │
        ◀─────────────────────────────────┘
```

### Event Flow

```
LogTailer
    │
    │ parse_log_line()
    ▼
LogEntry
    │
    │ on_entry callback (if level in TRACKED_LEVELS)
    ▼
ErrorStats.add()
    │
    │ ErrorEvent.from_entry()
    ▼
deque.append()
    │
    │ (if deque full, oldest removed automatically)
    ▼
Statistics Available
```

## Constraints

1. **Memory Bound**: ErrorStats._events is bounded by maxlen; when full, oldest events are automatically dropped
2. **Thread Safety**: deque operations are atomic under GIL; no explicit locking required
3. **Immutability**: ErrorEvent is frozen dataclass; events cannot be modified after creation
4. **Timestamp Fallback**: If LogEntry.timestamp is None, ErrorEvent uses datetime.now()
5. **Message Truncation**: Messages are truncated to 200 characters to bound memory

## Indexes (Conceptual)

For efficient queries, ErrorStats maintains:

1. **Chronological Order**: Events are naturally ordered by insertion time (deque)
2. **Level Counts**: Incremental counters for errors vs warnings
3. **Time-based Access**: `get_events_since()` iterates from newest to oldest

For statistics by SQLSTATE code, computed on-demand:
```python
def get_by_code(self) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for event in self._events:
        code = event.sql_state or "UNKNOWN"
        counts[code] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))
```
