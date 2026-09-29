---
title: Log formats
description: The text, csvlog, and jsonlog formats, their fields, and the features each one supports.
---

pgtail reads the three PostgreSQL log formats. It detects the format from the first line it reads, so the same
commands work on all three; the structured formats carry more fields.

## Format comparison

| Format | Config | Fields | PostgreSQL version |
|--------|--------|--------|--------------------|
| TEXT | `log_destination = 'stderr'` | Time, process ID, level, message | All |
| CSV | `log_destination = 'csvlog'` | 26 structured | All |
| JSON | `log_destination = 'jsonlog'` | 29 structured | 15+ |

## TEXT format (stderr)

PostgreSQL's default format: plain text lines.

**Configuration:**

```ini
log_destination = 'stderr'
logging_collector = on
```

**Available fields:**

| Field | Description |
|-------|-------------|
| `timestamp` | Log entry time |
| `pid` | Backend process ID |
| `level` | Severity (ERROR, WARNING, and so on) |
| `message` | Log message content |

**Example log line:**

```
2024-01-15 10:30:45.123 UTC [12345] ERROR:  relation "users" does not exist
```

pgtail recognizes the default `log_line_prefix` form `time zone [pid] LEVEL:`, the bracketed form
`[time zone] [pid] [context] LEVEL:`, and `time zone LEVEL:` without a process ID, which is common on Windows.

PostgreSQL writes a message's `DETAIL:`, `HINT:`, `CONTEXT:`, `STATEMENT:`, `QUERY:`, and `LOCATION:` on lines of their
own, and indents the further lines of a multi-line message with a tab. pgtail joins these lines to the entry they belong
to, as csvlog and jsonlog keep them in one record, so a level filter keeps an error's detail and statement with it and
the error counts once:

```
10:30:45.123 [12345] ERROR  : duplicate key value violates unique constraint "users_pkey"
DETAIL:  Key (id)=(1) already exists.
STATEMENT:  insert into users values (1)
```

A line in any other shape becomes a LOG entry whose message is the whole line.

## CSV format (csvlog)

A structured format with 26 fields. It enables field filtering and SQLSTATE analysis.

**Configuration:**

```ini
log_destination = 'csvlog'
logging_collector = on
```

**Available fields:**

| Field | Index | Description |
|-------|-------|-------------|
| `log_time` | 0 | Timestamp |
| `user_name` | 1 | Database user |
| `database_name` | 2 | Database name |
| `process_id` | 3 | Backend PID |
| `connection_from` | 4 | Client host:port |
| `session_id` | 5 | Session identifier |
| `session_line_num` | 6 | Line within session |
| `command_tag` | 7 | Command type (SELECT, INSERT, and so on) |
| `session_start_time` | 8 | Session start |
| `virtual_transaction_id` | 9 | Virtual transaction ID |
| `transaction_id` | 10 | Transaction ID |
| `error_severity` | 11 | Log level |
| `sql_state_code` | 12 | SQLSTATE (for example 23505) |
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

## JSON format (jsonlog)

A structured JSON format introduced in PostgreSQL 15, with the fields of csvlog and a few more.

**Configuration:**

```ini
log_destination = 'jsonlog'
logging_collector = on
```

**Additional fields (compared with CSV):**

| Field | Description |
|-------|-------------|
| `remote_host` | Client host (separate from the port) |
| `remote_port` | Client port |
| `func_name` | Function that raised the error |
| `file_name` | Source file that raised the error |
| `file_line_num` | Source line that raised the error |

**Example log line:**

```json
{"timestamp":"2024-01-15 10:30:45.123 UTC","user":"postgres","dbname":"mydb","pid":12345,"error_severity":"ERROR","state_code":"42P01","message":"relation \"users\" does not exist"}
```

## Features by format

### Works with any format

| Feature | Description |
|---------|-------------|
| Level filtering | `level error`, `level warning+` |
| Regex filtering | `filter /pattern/` |
| Time filtering | `since 5m`, `until 14:00` |
| Semantic highlighting | SQL, durations, identifiers, and more in messages |
| Error counts | Error and warning totals |
| Connection tracking | Parsed from the message text |
| Slow query detection | Parsed from `duration: N ms` |

### Needs CSV or JSON

These features use structured fields that only CSV and JSON logs have:

| Feature | Fields used | Description |
|---------|-------------|-------------|
| Field filtering | `application_name`, `database_name`, `user_name`, and others | `filter app=myapp`, `filter db=prod` |
| SQLSTATE breakdown | `sql_state` | Errors grouped by code (23505, 42P01) |
| Full display mode | All structured fields | `display full` shows every field an entry has |
| Custom field display | Chosen fields | `display fields user,database,query` |

:::caution[Field filtering with TEXT format]
A field filter on a TEXT log warns that it has no effect, since text lines have no structured fields:

```
Warning: Field filtering is only effective for CSV/JSON log formats.
```
:::

## PostgreSQL settings for features

Some pgtail features depend on what PostgreSQL logs.

### Slow query detection

Needs durations in the log:

```ini
# Option 1: log the duration of every statement
log_duration = on
log_statement = 'all'

# Option 2: log only slow statements (recommended for production)
log_min_duration_statement = 100  # Log statements taking more than 100 ms
```

### Connection statistics

Needs connection logging:

```ini
log_connections = on       # Log successful connections
log_disconnections = on    # Log disconnections with session time
```

### Error statistics with SQLSTATE

PostgreSQL includes the SQLSTATE of every error in csvlog and jsonlog, so no other setting is needed; pgtail reads it
from the structured `sql_state` field.

## Recommended configurations

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

log_min_duration_statement = 100  # Only log slow statements
log_connections = on
log_disconnections = on

log_error_verbosity = default
```

## Switching formats

1. Edit `postgresql.conf`:

   ```ini
   log_destination = 'jsonlog'  # or 'csvlog' or 'stderr'
   ```

2. Reload PostgreSQL:

   ```sh
   pg_ctl reload
   # Or: SELECT pg_reload_conf();
   ```

3. New log files use the new format, and pgtail detects it when tailing. Streaming output reports it as
   `Detected format: jsonlog`.

:::note[Log file extensions]
PostgreSQL names the files `.log` for TEXT, `.csv` for CSV, and `.json` for JSON, and writes a separate file for each
format when more than one is enabled.
:::
