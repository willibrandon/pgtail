# Research: CSV and JSON Log Format Support

**Feature**: 008-csv-json-log-format
**Date**: 2025-12-16

## PostgreSQL Log Format Specifications

### CSV Log Format (csvlog)

**Decision**: Parse all 26 standard CSV fields using Python's stdlib `csv` module.

**Rationale**: CSV format is well-documented with a fixed field order. Using Python's csv module handles quoting, escaping, and edge cases automatically.

**Alternatives considered**:
- Manual string splitting: Rejected - doesn't handle quoted fields containing commas
- pandas: Rejected - massive dependency for simple parsing

**Field Order (26 columns)**:

| Index | Field Name | Description |
|-------|------------|-------------|
| 0 | log_time | Time stamp with milliseconds |
| 1 | user_name | User name |
| 2 | database_name | Database name |
| 3 | process_id | Process ID |
| 4 | connection_from | Client host:port number |
| 5 | session_id | Session ID |
| 6 | session_line_num | Per-session line number |
| 7 | command_tag | Command tag |
| 8 | session_start_time | Session start time |
| 9 | virtual_transaction_id | Virtual transaction ID |
| 10 | transaction_id | Regular transaction ID |
| 11 | error_severity | Error severity (LOG, ERROR, etc.) |
| 12 | sql_state_code | SQLSTATE code (e.g., 42P01) |
| 13 | message | Error message |
| 14 | detail | Error message detail |
| 15 | hint | Hint |
| 16 | internal_query | Internal query that led to the error |
| 17 | internal_query_pos | Character position in internal query |
| 18 | context | Error context |
| 19 | query | User query that led to the error |
| 20 | query_pos | Character position in user query |
| 21 | location | PostgreSQL source code location |
| 22 | application_name | Application name |
| 23 | backend_type | Backend type (e.g., client backend, autovacuum) |
| 24 | leader_pid | Process ID of parallel group leader |
| 25 | query_id | Query ID |

**Source**: [PostgreSQL 18 Documentation](https://www.postgresql.org/docs/current/runtime-config-logging.html)

---

### JSON Log Format (jsonlog)

**Decision**: Parse JSON using Python's stdlib `json` module, extracting known keys and preserving unknown keys.

**Rationale**: JSON format introduced in PostgreSQL 15. The format explicitly allows future field additions, so parsing must be flexible. Using json module is standard practice.

**Alternatives considered**:
- orjson: Rejected - external dependency, stdlib json is fast enough for log parsing
- ujson: Rejected - same reason

**JSON Field Keys (29 fields)**:

| Key | Type | Description |
|-----|------|-------------|
| timestamp | string | Time stamp with milliseconds |
| user | string | User name |
| dbname | string | Database name |
| pid | number | Process ID |
| remote_host | string | Client host |
| remote_port | number | Client port |
| session_id | string | Session ID |
| line_num | number | Per-session line number |
| ps | string | Current ps display |
| session_start | string | Session start time |
| vxid | string | Virtual transaction ID |
| txid | string | Regular transaction ID |
| error_severity | string | Error severity |
| state_code | string | SQLSTATE code |
| message | string | Error message |
| detail | string | Error message detail |
| hint | string | Error message hint |
| internal_query | string | Internal query that led to the error |
| internal_position | number | Cursor index into internal query |
| context | string | Error context |
| statement | string | Client-supplied query string |
| cursor_position | number | Cursor index into query string |
| func_name | string | Error location function name |
| file_name | string | File name of error location |
| file_line_num | number | File line number of the error location |
| application_name | string | Client application name |
| backend_type | string | Type of backend |
| leader_pid | number | Process ID of leader for parallel workers |
| query_id | number | Query ID |

**Key behaviors**:
- String fields with null values are **excluded** from output (sparse JSON)
- Additional fields may be added in future versions
- Parser must ignore unknown fields gracefully

**Source**: [PostgreSQL 18 Documentation - Table 19.4](https://www.postgresql.org/docs/current/runtime-config-logging.html)

---

## Format Detection Strategy

**Decision**: Content-based detection using first non-empty line patterns.

**Rationale**: File extensions (`.csv`, `.json`) are not reliable - PostgreSQL uses date-based naming. Content detection is simple and reliable.

**Detection Algorithm**:

```
1. Read first non-empty line (up to 4KB)
2. If line starts with '{' and is valid JSON → JSONLOG
3. If line can be parsed as CSV with 22-26 columns → CSVLOG
4. Otherwise → TEXT (existing parser)
```

**Alternatives considered**:
- Check file extension: Rejected - PostgreSQL log files have date-based names like `postgresql-2024-01-15.log`
- Magic bytes: Rejected - text formats have no magic bytes
- User must specify format: Rejected - violates "Zero Configuration" principle

---

## Field Name Mapping

**Decision**: Use canonical field names that work across both formats.

**Rationale**: Users should be able to use the same filter syntax regardless of underlying format.

**Canonical → CSV/JSON mapping**:

| Canonical Name | CSV Field | JSON Key | Filter Alias |
|----------------|-----------|----------|--------------|
| timestamp | log_time | timestamp | - |
| user | user_name | user | user= |
| database | database_name | dbname | db= |
| pid | process_id | pid | pid= |
| application | application_name | application_name | app= |
| level | error_severity | error_severity | - (use existing level command) |
| message | message | message | - |
| sql_state | sql_state_code | state_code | - |
| query | query | statement | - |
| detail | detail | detail | - |
| hint | hint | hint | - |
| context | context | context | - |
| backend_type | backend_type | backend_type | backend= |

---

## Display Mode Implementation

**Decision**: Three display modes with immediate switching during active tailing.

### Compact Mode (default)
Single line per entry, key fields only:
```
10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
```

Format: `{timestamp} [{pid}] {level} {sql_state}: {message}`

### Full Mode
All available fields with labels:
```
10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
  Application: myapp
  Database: mydb
  User: postgres
  Query: SELECT * FROM foo
  Location: parse_relation.c:1234
```

### Fields Mode
User-selected fields only:
```
display fields timestamp,level,application,message
```

---

## Performance Considerations

**Decision**: Parse lazily; detect format once per file session.

**Rationale**: Format detection happens once when file is opened. Parsing happens per-line but uses optimized stdlib modules.

**Benchmarks needed**:
- CSV parsing: `csv.reader()` on typical 100-char log line
- JSON parsing: `json.loads()` on typical 200-char JSON object
- Target: <2x overhead compared to text regex parsing

---

## Integration with Existing Filters

**Decision**: Field filters integrate into existing filter chain (time → level → regex → field).

**Filter order (cheapest first)**:
1. Time filter - datetime comparison O(1)
2. Level filter - set membership O(1)
3. Field filter - string equality O(1)
4. Regex filter - regex match O(n)

**Rationale**: Field filtering is O(1) string comparison, cheaper than regex. Place it before regex in the chain.

---

## References

- [PostgreSQL 18 Error Reporting and Logging](https://www.postgresql.org/docs/current/runtime-config-logging.html)
- [PostgreSQL 15 JSON Logging Feature](https://www.cybertec-postgresql.com/en/json-logs-in-postgresql-15/)
- [pgPedia CSV Log Format](https://pgpedia.info/c/csv-log-file.html)
