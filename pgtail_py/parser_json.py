"""PostgreSQL JSON log format (jsonlog) parser.

Parses PostgreSQL JSON log files introduced in PostgreSQL 15 with up to 29 fields
as documented in: https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

# JSON field key mapping to LogEntry attributes
# Maps PostgreSQL JSON log keys to canonical LogEntry field names
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
