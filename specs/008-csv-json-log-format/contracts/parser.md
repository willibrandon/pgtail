# Parser Contracts

**Module**: `pgtail_py/parser.py` (extended), `pgtail_py/parser_csv.py`, `pgtail_py/parser_json.py`

## Extended LogEntry Dataclass

```python
@dataclass
class LogEntry:
    """A parsed PostgreSQL log entry supporting text, CSV, and JSON formats."""

    # Core fields (always present)
    timestamp: datetime | None
    level: LogLevel
    message: str
    raw: str
    pid: int | None = None
    format: LogFormat = LogFormat.TEXT

    # Extended fields (structured formats only)
    user_name: str | None = None
    database_name: str | None = None
    application_name: str | None = None
    sql_state: str | None = None
    detail: str | None = None
    hint: str | None = None
    context: str | None = None
    query: str | None = None
    internal_query: str | None = None
    location: str | None = None
    session_id: str | None = None
    session_line_num: int | None = None
    command_tag: str | None = None
    virtual_transaction_id: str | None = None
    transaction_id: str | None = None
    backend_type: str | None = None
    leader_pid: int | None = None
    query_id: int | None = None
    connection_from: str | None = None
    remote_host: str | None = None
    remote_port: int | None = None
    session_start: datetime | None = None
    query_pos: int | None = None
    internal_query_pos: int | None = None
    func_name: str | None = None
    file_name: str | None = None
    file_line_num: int | None = None

    def get_field(self, name: str) -> str | int | datetime | None:
        """Get a field value by canonical name.

        Args:
            name: Canonical field name (e.g., "app", "db", "user")

        Returns:
            Field value or None if not available.
        """
        ...

    def available_fields(self) -> list[str]:
        """Get list of field names that have non-None values."""
        ...

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary for JSON serialization.

        Returns:
            Dictionary with all non-None fields.
        """
        ...
```

---

## Format-Specific Parsers

### parser_csv.py

```python
def parse_csv_line(line: str) -> LogEntry:
    """Parse a PostgreSQL CSV log line.

    Args:
        line: Raw CSV log line (26 comma-separated fields)

    Returns:
        LogEntry with format=LogFormat.CSV and all fields populated.

    Raises:
        ValueError: If line cannot be parsed as valid CSV log entry.
    """
    ...

# CSV field indices (for reference)
CSV_FIELD_ORDER: list[str] = [
    "log_time",           # 0
    "user_name",          # 1
    "database_name",      # 2
    "process_id",         # 3
    "connection_from",    # 4
    "session_id",         # 5
    "session_line_num",   # 6
    "command_tag",        # 7
    "session_start_time", # 8
    "virtual_transaction_id",  # 9
    "transaction_id",     # 10
    "error_severity",     # 11
    "sql_state_code",     # 12
    "message",            # 13
    "detail",             # 14
    "hint",               # 15
    "internal_query",     # 16
    "internal_query_pos", # 17
    "context",            # 18
    "query",              # 19
    "query_pos",          # 20
    "location",           # 21
    "application_name",   # 22
    "backend_type",       # 23
    "leader_pid",         # 24
    "query_id",           # 25
]
```

### parser_json.py

```python
def parse_json_line(line: str) -> LogEntry:
    """Parse a PostgreSQL JSON log line.

    Args:
        line: Raw JSON log line (single JSON object)

    Returns:
        LogEntry with format=LogFormat.JSON and available fields populated.

    Raises:
        ValueError: If line cannot be parsed as valid JSON log entry.
    """
    ...

# JSON field key mapping to LogEntry attributes
JSON_FIELD_MAP: dict[str, str] = {
    "timestamp": "timestamp",
    "user": "user_name",
    "dbname": "database_name",
    "pid": "pid",
    "remote_host": "remote_host",
    "remote_port": "remote_port",
    "session_id": "session_id",
    "line_num": "session_line_num",
    "session_start": "session_start",
    "vxid": "virtual_transaction_id",
    "txid": "transaction_id",
    "error_severity": "level",
    "state_code": "sql_state",
    "message": "message",
    "detail": "detail",
    "hint": "hint",
    "internal_query": "internal_query",
    "internal_position": "internal_query_pos",
    "context": "context",
    "statement": "query",
    "cursor_position": "query_pos",
    "func_name": "func_name",
    "file_name": "file_name",
    "file_line_num": "file_line_num",
    "application_name": "application_name",
    "backend_type": "backend_type",
    "leader_pid": "leader_pid",
    "query_id": "query_id",
}
```

---

## Unified Parser Interface

### parser.py (extended)

```python
def parse_log_line(line: str, format: LogFormat = LogFormat.TEXT) -> LogEntry:
    """Parse a log line using the appropriate parser.

    Args:
        line: Raw log line
        format: Expected format (TEXT, CSV, or JSON)

    Returns:
        LogEntry with fields populated according to format.
        For unparseable lines, returns fallback entry with raw preserved.
    """
    ...
```
