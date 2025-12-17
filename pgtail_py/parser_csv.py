"""PostgreSQL CSV log format (csvlog) parser.

Parses PostgreSQL CSV log files with 26 standard fields as documented in:
https://www.postgresql.org/docs/current/runtime-config-logging.html
"""

# CSV field indices (26 columns in PostgreSQL 14+)
# Older versions may have 22-25 fields; parser handles this gracefully
CSV_FIELD_ORDER: list[str] = [
    "log_time",  # 0
    "user_name",  # 1
    "database_name",  # 2
    "process_id",  # 3
    "connection_from",  # 4
    "session_id",  # 5
    "session_line_num",  # 6
    "command_tag",  # 7
    "session_start_time",  # 8
    "virtual_transaction_id",  # 9
    "transaction_id",  # 10
    "error_severity",  # 11
    "sql_state_code",  # 12
    "message",  # 13
    "detail",  # 14
    "hint",  # 15
    "internal_query",  # 16
    "internal_query_pos",  # 17
    "context",  # 18
    "query",  # 19
    "query_pos",  # 20
    "location",  # 21
    "application_name",  # 22
    "backend_type",  # 23
    "leader_pid",  # 24
    "query_id",  # 25
]
