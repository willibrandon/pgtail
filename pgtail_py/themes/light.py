"""Light theme for pgtail.

Designed for light terminal backgrounds with darker colors.
"""

from pgtail_py.theme import ColorStyle, Theme

LIGHT_THEME = Theme(
    name="light",
    description="Light theme for light terminal backgrounds",
    levels={
        "PANIC": ColorStyle(fg="white", bg="darkred", bold=True),
        "FATAL": ColorStyle(fg="darkred", bold=True),
        "ERROR": ColorStyle(fg="darkred"),
        "WARNING": ColorStyle(fg="darkorange"),
        "NOTICE": ColorStyle(fg="darkcyan"),
        "LOG": ColorStyle(fg="ansiblack"),
        "INFO": ColorStyle(fg="darkgreen"),
        "DEBUG": ColorStyle(fg="gray"),
        "DEBUG1": ColorStyle(fg="gray"),
        "DEBUG2": ColorStyle(fg="gray"),
        "DEBUG3": ColorStyle(fg="gray"),
        "DEBUG4": ColorStyle(fg="gray"),
        "DEBUG5": ColorStyle(fg="gray"),
    },
    ui={
        "prompt": ColorStyle(fg="darkgreen"),
        "timestamp": ColorStyle(fg="gray"),
        "pid": ColorStyle(fg="gray"),
        "highlight": ColorStyle(fg="black", bg="yellow"),
        "slow_warning": ColorStyle(fg="darkorange"),
        "slow_slow": ColorStyle(fg="darkorange", bold=True),
        "slow_critical": ColorStyle(fg="darkred", bold=True),
        "detail": ColorStyle(fg="ansiblack"),
        # SQL syntax highlighting
        "sql_keyword": ColorStyle(fg="darkblue", bold=True),
        "sql_identifier": ColorStyle(fg="teal"),
        "sql_string": ColorStyle(fg="darkgreen"),
        "sql_number": ColorStyle(fg="darkmagenta"),
        "sql_operator": ColorStyle(fg="darkorange"),
        "sql_comment": ColorStyle(fg="gray"),
        "sql_function": ColorStyle(fg="darkblue"),
        # Status bar (tail mode) - dark text on light gray background
        "status": ColorStyle(fg="ansiblack", bg="silver"),
        "status_follow": ColorStyle(fg="darkgreen", bg="silver", bold=True),
        "status_paused": ColorStyle(fg="darkorange", bg="silver", bold=True),
        "status_error": ColorStyle(fg="darkred", bg="silver", bold=True),
        "status_warning": ColorStyle(fg="darkorange", bg="silver"),
        "status_filter": ColorStyle(fg="teal", bg="silver"),
        "status_instance": ColorStyle(fg="ansiblack", bg="silver"),
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="darkgreen", bold=True),
        # Separator lines
        "separator": ColorStyle(fg="gray"),
        # REPL bottom toolbar
        "bottom-toolbar": ColorStyle(fg="#333333", bg="#e0e0e0"),
        "bottom-toolbar.text": ColorStyle(fg="#333333", bg="#e0e0e0"),
        "toolbar": ColorStyle(fg="#333333", bg="#e0e0e0"),
        "toolbar.dim": ColorStyle(fg="#888888", bg="#e0e0e0"),
        "toolbar.filter": ColorStyle(fg="#007acc", bg="#e0e0e0"),
        "toolbar.warning": ColorStyle(fg="#d9831f", bg="#e0e0e0"),
        "toolbar.shell": ColorStyle(fg="#000000", bg="#e0e0e0", bold=True),
        # Semantic highlighting (hl_* keys)
        # Structural
        "hl_timestamp_date": ColorStyle(fg="gray"),
        "hl_timestamp_time": ColorStyle(fg="gray"),
        "hl_timestamp_ms": ColorStyle(fg="gray", dim=True),
        "hl_timestamp_tz": ColorStyle(fg="gray", dim=True),
        "hl_pid": ColorStyle(fg="teal"),
        "hl_context": ColorStyle(fg="darkorange", bold=True),
        # Diagnostic
        "hl_sqlstate_success": ColorStyle(fg="darkgreen"),
        "hl_sqlstate_warning": ColorStyle(fg="darkorange"),
        "hl_sqlstate_error": ColorStyle(fg="darkred"),
        "hl_sqlstate_internal": ColorStyle(fg="darkred", bold=True),
        "hl_error_name": ColorStyle(fg="darkred"),
        # Performance
        "hl_duration_fast": ColorStyle(fg="darkgreen"),
        "hl_duration_slow": ColorStyle(fg="darkorange"),
        "hl_duration_very_slow": ColorStyle(fg="darkorange", bold=True),
        "hl_duration_critical": ColorStyle(fg="darkred", bold=True),
        "hl_memory_value": ColorStyle(fg="darkmagenta"),
        "hl_memory_unit": ColorStyle(fg="darkmagenta", dim=True),
        "hl_statistics": ColorStyle(fg="teal"),
        # Objects
        "hl_identifier": ColorStyle(fg="teal"),
        "hl_relation": ColorStyle(fg="teal", bold=True),
        "hl_schema": ColorStyle(fg="teal"),
        # WAL
        "hl_lsn_segment": ColorStyle(fg="darkblue"),
        "hl_lsn_offset": ColorStyle(fg="darkblue", dim=True),
        "hl_wal_segment": ColorStyle(fg="darkblue"),
        "hl_txid": ColorStyle(fg="darkmagenta"),
        # Connection
        "hl_host": ColorStyle(fg="darkgreen"),
        "hl_port": ColorStyle(fg="darkgreen", dim=True),
        "hl_user": ColorStyle(fg="darkgreen"),
        "hl_database": ColorStyle(fg="darkgreen", bold=True),
        "hl_ip": ColorStyle(fg="darkgreen"),
        "hl_backend": ColorStyle(fg="teal"),
        # SQL (additional to existing sql_* keys)
        "hl_param": ColorStyle(fg="darkorange"),
        # Lock
        "hl_lock_share": ColorStyle(fg="darkorange"),
        "hl_lock_exclusive": ColorStyle(fg="darkred"),
        "hl_lock_wait": ColorStyle(fg="darkorange", bold=True),
        # Checkpoint/Recovery
        "hl_checkpoint": ColorStyle(fg="darkblue"),
        "hl_recovery": ColorStyle(fg="darkgreen"),
        # Misc
        "hl_bool_true": ColorStyle(fg="darkgreen"),
        "hl_bool_false": ColorStyle(fg="darkred"),
        "hl_null": ColorStyle(fg="gray", italic=True),
        "hl_oid": ColorStyle(fg="darkmagenta"),
        "hl_path": ColorStyle(fg="teal"),
    },
)
