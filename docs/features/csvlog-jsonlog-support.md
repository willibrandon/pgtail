# Feature: CSV and JSON Log Format Support

## Problem

PostgreSQL supports multiple log formats via `log_destination`:
- `stderr` - Default text format (currently supported)
- `csvlog` - Structured CSV with all fields
- `jsonlog` - Structured JSON (PostgreSQL 15+)

CSV and JSON formats contain more information (error codes, application name, query ID, etc.) but pgtail currently only parses the default text format.

## Proposed Solution

Auto-detect log format and parse accordingly. For structured formats, display information in a user-friendly way while preserving access to all fields.

## User Scenarios

### Scenario 1: Auto-Detection
Developer points pgtail at a CSV log file:
```
pgtail> tail 0
Detected format: csvlog
Tailing with structured parsing...
```

### Scenario 2: Rich Error Information
With csvlog, errors show more context:
```
10:23:45 [12345] ERROR 42P01: relation "foo" does not exist
  Application: myapp
  Query: SELECT * FROM foo
  Location: parse_relation.c:1234
```

### Scenario 3: Field-Based Filtering
Developer filters by application name (only available in structured logs):
```
pgtail> filter app=myapp
Showing only entries from application: myapp
```

### Scenario 4: JSON Output
Developer wants machine-readable output:
```
pgtail> output json
{"timestamp":"2024-01-15T10:23:45.123","level":"ERROR",...}
```

## CSV Log Fields

PostgreSQL csvlog includes:
- log_time, user_name, database_name, process_id
- connection_from, session_id, session_line_num
- command_tag, session_start_time, virtual_transaction_id
- transaction_id, error_severity, sql_state_code
- message, detail, hint, internal_query
- internal_query_pos, context, query, query_pos
- location, application_name, backend_type
- leader_pid, query_id

## Display Modes

```
pgtail> display compact    # One line per entry (default)
pgtail> display full       # Show all available fields
pgtail> display fields timestamp,level,application_name,message
```

## Success Criteria

1. Auto-detect format from file content (first line)
2. Parse all standard fields from csvlog
3. Parse all standard fields from jsonlog (PG15+)
4. Graceful fallback for malformed entries
5. Field-based filtering works (app=, db=, user=)
6. Output as JSON for piping to other tools
7. Performance comparable to text format

## Out of Scope

- Syslog format support
- Custom log_line_prefix parsing
- Writing/converting between formats
