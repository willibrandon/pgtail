# Data Model: CSV and JSON Log Format Support

**Feature**: 008-csv-json-log-format
**Date**: 2025-12-16

## Entities

### LogFormat (Enum)

Enumeration of supported log formats.

```
LogFormat
├── TEXT   # Default stderr format (existing)
├── CSV    # csvlog format (26 fields)
└── JSON   # jsonlog format (29 fields, PG15+)
```

**State Transitions**: None (immutable once detected per file session)

---

### LogEntry (Extended)

Represents a single parsed log entry. Extended from existing implementation to support structured format fields.

**Core Fields** (always present):

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | None | Parsed timestamp |
| level | LogLevel | Log severity level |
| message | str | The log message content |
| raw | str | Original line (preserved for fallback) |
| pid | int | None | Process ID |
| format | LogFormat | Detected format of this entry |

**Extended Fields** (structured formats only):

| Field | Type | Description | Available In |
|-------|------|-------------|--------------|
| user_name | str | None | Database user | CSV, JSON |
| database_name | str | None | Database name | CSV, JSON |
| application_name | str | None | Client application | CSV, JSON |
| sql_state | str | None | SQLSTATE code (e.g., 42P01) | CSV, JSON |
| detail | str | None | Error detail message | CSV, JSON |
| hint | str | None | Error hint | CSV, JSON |
| context | str | None | Error context | CSV, JSON |
| query | str | None | User query that caused error | CSV, JSON |
| internal_query | str | None | Internal query that caused error | CSV, JSON |
| location | str | None | PostgreSQL source code location | CSV, JSON |
| session_id | str | None | Session identifier | CSV, JSON |
| session_line_num | int | None | Line number within session | CSV, JSON |
| command_tag | str | None | Command tag (SELECT, INSERT, etc.) | CSV only |
| virtual_transaction_id | str | None | Virtual transaction ID | CSV, JSON |
| transaction_id | str | None | Transaction ID | CSV, JSON |
| backend_type | str | None | Backend type (client, autovacuum) | CSV, JSON |
| leader_pid | int | None | Parallel group leader PID | CSV, JSON |
| query_id | int | None | Query ID | CSV, JSON |
| connection_from | str | None | Client host:port | CSV only |
| remote_host | str | None | Client host | JSON only |
| remote_port | int | None | Client port | JSON only |
| session_start | datetime | None | Session start time | CSV, JSON |
| query_pos | int | None | Error position in query | CSV, JSON |
| internal_query_pos | int | None | Error position in internal query | CSV, JSON |
| func_name | str | None | Error location function name | JSON only |
| file_name | str | None | Error location file name | JSON only |
| file_line_num | int | None | Error location line number | JSON only |

**Validation Rules**:
- `format` must be one of LogFormat values
- `level` must be a valid LogLevel
- Extended fields are None when not available (text format or not present in entry)

---

### DisplayMode (Enum)

Controls how log entries are rendered to the terminal.

```
DisplayMode
├── COMPACT   # Single line: timestamp [pid] level sql_state: message
├── FULL      # All available fields with labels
└── CUSTOM    # User-selected fields only
```

**Associated State**:
- `custom_fields: list[str]` - Field names to display when mode is CUSTOM

---

### FieldFilter (Dataclass)

A single field filter condition.

| Field | Type | Description |
|-------|------|-------------|
| field | str | Canonical field name (e.g., "app", "db") |
| value | str | Value to match (case-sensitive exact match) |

**Canonical Field Aliases**:

| Alias | Canonical Field | LogEntry Attribute |
|-------|-----------------|-------------------|
| app | application | application_name |
| db | database | database_name |
| user | user | user_name |
| pid | pid | pid |
| backend | backend | backend_type |

---

### FieldFilterState (Dataclass)

Manages active field filters.

| Field | Type | Description |
|-------|------|-------------|
| filters | list[FieldFilter] | Active filters (AND logic) |

**Operations**:
- `add(field, value)` - Add a filter condition
- `remove(field)` - Remove filter for a field
- `clear()` - Remove all filters
- `matches(entry: LogEntry) -> bool` - Check if entry passes all filters
- `is_active() -> bool` - True if any filters are set

**Behavior**:
- Multiple filters for different fields: AND logic (entry must match all)
- Filter on field not present in entry: Entry is excluded
- Filter on text format log: Not applicable (returns informative error)

---

### OutputFormat (Enum)

Controls output serialization format.

```
OutputFormat
├── TEXT   # Human-readable colored output (default)
└── JSON   # Machine-readable JSON, one object per line
```

---

## Entity Relationships

```
LogTailer (existing)
├── has-one LogFormat (detected on file open)
├── has-many LogEntry (parsed from file)
├── has-one FieldFilterState
├── has-one DisplayMode
└── has-one OutputFormat

LogEntry
├── has-one LogFormat
├── has-one LogLevel (existing)
└── has-many extended fields (when format != TEXT)

FieldFilterState
├── has-many FieldFilter
└── filters LogEntry instances

AppState (existing, in cli.py)
├── has-one DisplayMode
├── has-one OutputFormat
└── has-one FieldFilterState
```

---

## Field Availability by Format

| Field | TEXT | CSV | JSON |
|-------|------|-----|------|
| timestamp | ✅ | ✅ | ✅ |
| level | ✅ | ✅ | ✅ |
| message | ✅ | ✅ | ✅ |
| pid | ✅ | ✅ | ✅ |
| user_name | ❌ | ✅ | ✅ |
| database_name | ❌ | ✅ | ✅ |
| application_name | ❌ | ✅ | ✅ |
| sql_state | ❌ | ✅ | ✅ |
| detail | ❌ | ✅ | ✅ |
| hint | ❌ | ✅ | ✅ |
| context | ❌ | ✅ | ✅ |
| query | ❌ | ✅ | ✅ |
| backend_type | ❌ | ✅ | ✅ |
| location | ❌ | ✅ | ✅* |

*JSON provides more granular location info (func_name, file_name, file_line_num)
