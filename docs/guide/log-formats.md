# Log Formats

pgtail supports three PostgreSQL log formats, each providing different levels of detail.

## Format Comparison

| Format | Config | Fields | PostgreSQL Version |
|--------|--------|--------|-------------------|
| TEXT | `log_destination = 'stderr'` | 5 basic | All |
| CSV | `log_destination = 'csvlog'` | 26 structured | All |
| JSON | `log_destination = 'jsonlog'` | 29 structured | 15+ |

## TEXT Format (stderr)

The default PostgreSQL log format. Logs are written as plain text lines.

**Configuration:**
```ini
log_destination = 'stderr'
logging_collector = on
```

**Available Fields:**

| Field | Description |
|-------|-------------|
| `timestamp` | Log entry time |
| `pid` | Backend process ID |
| `level` | Severity (ERROR, WARNING, etc.) |
| `message` | Log message content |

**Example Log Line:**
```
2024-01-15 10:30:45.123 UTC [12345] ERROR:  relation "users" does not exist
```

## CSV Format (csvlog)

Structured format with 26 fields. Enables field-based filtering and SQLSTATE analysis.

**Configuration:**
```ini
log_destination = 'csvlog'
logging_collector = on
```

**Available Fields:**

| Field | Index | Description |
|-------|-------|-------------|
| `log_time` | 0 | Timestamp |
| `user_name` | 1 | Database user |
| `database_name` | 2 | Database name |
| `process_id` | 3 | Backend PID |
| `connection_from` | 4 | Client host:port |
| `session_id` | 5 | Session identifier |
| `session_line_num` | 6 | Line within session |
| `command_tag` | 7 | Command type (SELECT, INSERT, etc.) |
| `session_start_time` | 8 | Session start |
| `virtual_transaction_id` | 9 | Virtual xact ID |
| `transaction_id` | 10 | Transaction ID |
| `error_severity` | 11 | Log level |
| `sql_state_code` | 12 | SQLSTATE (e.g., 23505) |
| `message` | 13 | Primary message |
| `detail` | 14 | Error detail |
| `hint` | 15 | Error hint |
| `internal_query` | 16 | Internal query |
| `internal_query_pos` | 17 | Position in internal query |
| `context` | 18 | Error context |
| `query` | 19 | User's query |
| `query_pos` | 20 | Error position in query |
| `location` | 21 | Source code location |
| `application_name` | 22 | Client application |
| `backend_type` | 23 | Backend type |
| `leader_pid` | 24 | Parallel leader PID |
| `query_id` | 25 | Query identifier |

## JSON Format (jsonlog)

Structured JSON format introduced in PostgreSQL 15. Similar to CSV with additional error location fields.

**Configuration:**
```ini
log_destination = 'jsonlog'
logging_collector = on
```

**Additional Fields (vs CSV):**

| Field | Description |
|-------|-------------|
| `remote_host` | Client host (separate from port) |
| `remote_port` | Client port |
| `func_name` | Error function name |
| `file_name` | Error source file |
| `file_line_num` | Error source line |

**Example Log Line:**
```json
{"timestamp":"2024-01-15 10:30:45.123 UTC","user":"postgres","dbname":"mydb","pid":12345,"error_severity":"ERROR","state_code":"42P01","message":"relation \"users\" does not exist"}
```

## Feature Requirements by Format

### Works with ANY Format

These features work with TEXT, CSV, and JSON:

| Feature | Description |
|---------|-------------|
| Level filtering | `level error`, `level warning+` |
| Regex filtering | `filter /pattern/` |
| Time filtering | `since 5m`, `until 14:00` |
| SQL highlighting | Automatic in log messages |
| Basic error counts | Error/warning totals |
| Connection tracking | Parsed from message text |
| Slow query detection | Parsed from `duration: Xms` |

### Requires CSV or JSON

These features need structured fields only available in CSV/JSON:

| Feature | Required Fields | Description |
|---------|-----------------|-------------|
| Field filtering | `application_name`, `database_name`, `user_name` | `filter app=myapp`, `filter db=prod` |
| SQLSTATE breakdown | `sql_state` | Error categorization by code (23505, 42P01) |
| Full display mode | All structured fields | `display full` shows all available fields |
| Custom field display | Selected fields | `display fields user,database,query` |

!!! warning "Field Filtering with TEXT Format"
    If you use field filtering (`filter app=myapp`) with TEXT format, pgtail will warn:
    ```
    Warning: Field filtering requires CSV or JSON log format
    ```

## PostgreSQL Settings for Features

Some pgtail features require specific PostgreSQL configuration:

### Slow Query Detection

Requires duration logging:

```ini
# Option 1: Log duration for all statements
log_duration = on
log_statement = 'all'

# Option 2: Log only slow queries (recommended for production)
log_min_duration_statement = 100  # Log queries taking > 100ms
```

### Connection Statistics

Requires connection logging:

```ini
log_connections = on       # Log successful connections
log_disconnections = on    # Log disconnections with duration
```

### Error Statistics with SQLSTATE

SQLSTATE codes are automatically included in error messages. No additional configuration needed, but requires CSV or JSON format to parse the structured `sql_state` field.

## Recommended Configurations

### Development

Full logging for debugging:

```ini
log_destination = 'jsonlog'  # Or 'csvlog'
logging_collector = on
log_directory = 'log'

log_statement = 'all'
log_duration = on
log_connections = on
log_disconnections = on

log_line_prefix = '%m [%p] %q%u@%d '
```

### Production

Balanced logging:

```ini
log_destination = 'csvlog'
logging_collector = on
log_directory = 'log'

log_min_duration_statement = 100  # Only log slow queries
log_connections = on
log_disconnections = on

log_error_verbosity = default
```

## Switching Formats

To change log format:

1. Edit `postgresql.conf`:
   ```ini
   log_destination = 'jsonlog'  # or 'csvlog' or 'stderr'
   ```

2. Reload PostgreSQL:
   ```bash
   pg_ctl reload
   # Or: SELECT pg_reload_conf();
   ```

3. New log files use the new format. pgtail auto-detects the format when tailing.

!!! note "Log File Extensions"
    - TEXT: `.log`
    - CSV: `.csv`
    - JSON: `.json`

    PostgreSQL creates separate files for each format if multiple are enabled.
