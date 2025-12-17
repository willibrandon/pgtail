# Quickstart: CSV and JSON Log Format Support

**Feature**: 008-csv-json-log-format

## Prerequisites

- Python 3.10+
- pgtail installed and working
- PostgreSQL instance with csvlog or jsonlog enabled

## Enabling Structured Logging in PostgreSQL

### For CSV logging:

```sql
-- In postgresql.conf or via ALTER SYSTEM
ALTER SYSTEM SET log_destination = 'csvlog';
ALTER SYSTEM SET logging_collector = 'on';
SELECT pg_reload_conf();
```

### For JSON logging (PostgreSQL 15+):

```sql
ALTER SYSTEM SET log_destination = 'jsonlog';
ALTER SYSTEM SET logging_collector = 'on';
SELECT pg_reload_conf();
```

---

## Basic Usage

### Auto-Detection

pgtail automatically detects the log format when you start tailing:

```bash
$ pgtail
pgtail> list
  [0] PostgreSQL 16 (pgrx) - ~/.pgrx/data-16/log/postgresql.csv

pgtail> tail 0
Detected format: csvlog
Tailing with structured parsing...

10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
```

### Display Modes

Switch between display modes during tailing:

```bash
# Default compact mode
pgtail> display compact
10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist

# Full mode shows all fields
pgtail> display full
10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
  Application: myapp
  Database: mydb
  User: postgres
  Query: SELECT * FROM foo
  Location: parse_relation.c:1234

# Custom fields
pgtail> display fields timestamp,level,application_name,message
10:23:45.123 ERROR myapp: relation "foo" does not exist
```

### Field Filtering

Filter by application, database, or user (structured formats only):

```bash
# Filter by application
pgtail> filter app=myapp
Showing only: app=myapp

# Add more filters (AND logic)
pgtail> filter db=production
Showing: app=myapp, db=production

# Clear all filters
pgtail> filter clear
```

### JSON Output

Export as JSON for piping to other tools:

```bash
pgtail> output json
{"timestamp":"2024-01-15T10:23:45.123","level":"ERROR","pid":12345,...}

# Pipe to jq
pgtail> output json
^C  # Stop tailing
$ pgtail tail 0 | jq '.message'
```

---

## Development Workflow

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_parser_csv.py -v

# Run with coverage
pytest --cov=pgtail_py tests/
```

### Module Structure

```
pgtail_py/
├── format_detector.py   # Format auto-detection
├── parser_csv.py        # CSV log parser
├── parser_json.py       # JSON log parser
├── field_filter.py      # Field-based filtering
├── display.py           # Display mode control
├── parser.py            # Extended LogEntry (unified interface)
├── tailer.py            # Extended LogTailer
└── cli.py               # New commands

tests/
├── test_format_detector.py
├── test_parser_csv.py
├── test_parser_json.py
├── test_field_filter.py
└── test_display.py
```

### Key Implementation Notes

1. **Format detection happens once per file session** - stored in LogTailer._detected_format
2. **LogEntry is extended** - new optional fields for structured data
3. **Filter chain order**: time → level → field → regex (cheapest first)
4. **Backward compatible** - text logs work exactly as before

---

## Sample Log Files for Testing

### CSV log sample (postgresql.csv):

```csv
2024-01-15 10:23:45.123 PST,postgres,mydb,12345,"127.0.0.1:5432",abc123,1,SELECT,"2024-01-15 10:00:00 PST",1/1,0,ERROR,42P01,"relation ""foo"" does not exist",,,,,,,,"SELECT * FROM foo",,,myapp,client backend,,0
```

### JSON log sample (postgresql.json):

```json
{"timestamp":"2024-01-15 10:23:45.123 PST","user":"postgres","dbname":"mydb","pid":12345,"remote_host":"127.0.0.1","remote_port":5432,"session_id":"abc123","line_num":1,"session_start":"2024-01-15 10:00:00 PST","error_severity":"ERROR","state_code":"42P01","message":"relation \"foo\" does not exist","statement":"SELECT * FROM foo","application_name":"myapp","backend_type":"client backend"}
```

---

## Troubleshooting

### "Field filtering requires CSV or JSON format"

This means you're trying to use field filters (`app=`, `db=`) on a text format log. Switch to a structured format log or use regex filtering instead.

### Format not detected correctly

If pgtail misdetects the format, the first line may be malformed. Check the log file:

```bash
head -1 /path/to/postgresql.csv
```

### Missing fields in output

Some fields are only populated for errors (e.g., `detail`, `hint`, `query`). Check `display full` to see all available fields.
