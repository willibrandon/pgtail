"""High contrast theme for pgtail.

Designed for accessibility with strong color contrast.
WCAG AA compliant colors for better visibility.
"""

from pgtail_py.theme import ColorStyle, Theme

HIGH_CONTRAST_THEME = Theme(
    name="high-contrast",
    description="High contrast theme for accessibility",
    levels={
        "PANIC": ColorStyle(fg="white", bg="red", bold=True),
        "FATAL": ColorStyle(fg="red", bold=True),
        "ERROR": ColorStyle(fg="red", bold=True),
        "WARNING": ColorStyle(fg="yellow", bold=True),
        "NOTICE": ColorStyle(fg="cyan", bold=True),
        "LOG": ColorStyle(fg="white"),
        "INFO": ColorStyle(fg="green", bold=True),
        "DEBUG": ColorStyle(fg="white", dim=True),
        "DEBUG1": ColorStyle(fg="white", dim=True),
        "DEBUG2": ColorStyle(fg="white", dim=True),
        "DEBUG3": ColorStyle(fg="white", dim=True),
        "DEBUG4": ColorStyle(fg="white", dim=True),
        "DEBUG5": ColorStyle(fg="white", dim=True),
    },
    ui={
        "prompt": ColorStyle(fg="green", bold=True),
        "timestamp": ColorStyle(fg="white"),
        "pid": ColorStyle(fg="white"),
        "highlight": ColorStyle(fg="black", bg="yellow", bold=True),
        "slow_warning": ColorStyle(fg="yellow", bold=True),
        "slow_slow": ColorStyle(fg="yellow", bold=True, underline=True),
        "slow_critical": ColorStyle(fg="red", bold=True, underline=True),
        "detail": ColorStyle(fg="white"),
        # SQL syntax highlighting (high saturation for accessibility)
        "sql_keyword": ColorStyle(fg="blue", bold=True),
        "sql_identifier": ColorStyle(fg="cyan", bold=True),
        "sql_string": ColorStyle(fg="green", bold=True),
        "sql_number": ColorStyle(fg="magenta", bold=True),
        "sql_operator": ColorStyle(fg="yellow", bold=True),
        "sql_comment": ColorStyle(fg="white", dim=True),
        "sql_function": ColorStyle(fg="blue", bold=True),
        # Status bar (tail mode) - WCAG AA compliant high contrast
        "status": ColorStyle(fg="white", bg="ansiblack", bold=True),
        "status_follow": ColorStyle(fg="green", bg="ansiblack", bold=True),
        "status_paused": ColorStyle(fg="yellow", bg="ansiblack", bold=True),
        "status_error": ColorStyle(fg="red", bg="ansiblack", bold=True, underline=True),
        "status_warning": ColorStyle(fg="yellow", bg="ansiblack", bold=True),
        "status_filter": ColorStyle(fg="cyan", bg="ansiblack", bold=True),
        "status_instance": ColorStyle(fg="white", bg="ansiblack", bold=True),
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="green", bold=True),
        # Separator lines
        "separator": ColorStyle(fg="white"),
        # REPL bottom toolbar (WCAG AA compliant)
        "bottom-toolbar": ColorStyle(fg="white", bg="ansiblack"),
        "bottom-toolbar.text": ColorStyle(fg="white", bg="ansiblack"),
        "toolbar": ColorStyle(fg="white", bg="ansiblack", bold=True),
        "toolbar.dim": ColorStyle(fg="white", bg="ansiblack"),
        "toolbar.filter": ColorStyle(fg="cyan", bg="ansiblack", bold=True),
        "toolbar.warning": ColorStyle(fg="yellow", bg="ansiblack", bold=True),
        "toolbar.shell": ColorStyle(fg="white", bg="ansiblack", bold=True, underline=True),
        # Semantic highlighting (hl_* keys) - WCAG AA compliant
        # Structural
        "hl_timestamp_date": ColorStyle(fg="white"),
        "hl_timestamp_time": ColorStyle(fg="white"),
        "hl_timestamp_ms": ColorStyle(fg="white", dim=True),
        "hl_timestamp_tz": ColorStyle(fg="white", dim=True),
        "hl_pid": ColorStyle(fg="cyan", bold=True),
        "hl_context": ColorStyle(fg="yellow", bold=True),
        # Diagnostic
        "hl_sqlstate_success": ColorStyle(fg="green", bold=True),
        "hl_sqlstate_warning": ColorStyle(fg="yellow", bold=True),
        "hl_sqlstate_error": ColorStyle(fg="red", bold=True),
        "hl_sqlstate_internal": ColorStyle(fg="red", bold=True, underline=True),
        "hl_error_name": ColorStyle(fg="red", bold=True),
        # Performance
        "hl_duration_fast": ColorStyle(fg="green", bold=True),
        "hl_duration_slow": ColorStyle(fg="yellow", bold=True),
        "hl_duration_very_slow": ColorStyle(fg="yellow", bold=True, underline=True),
        "hl_duration_critical": ColorStyle(fg="red", bold=True, underline=True),
        "hl_memory_value": ColorStyle(fg="magenta", bold=True),
        "hl_memory_unit": ColorStyle(fg="magenta", bold=True),
        "hl_statistics": ColorStyle(fg="cyan", bold=True),
        # Objects
        "hl_identifier": ColorStyle(fg="cyan", bold=True),
        "hl_relation": ColorStyle(fg="cyan", bold=True, underline=True),
        "hl_schema": ColorStyle(fg="cyan", bold=True),
        # WAL
        "hl_lsn_segment": ColorStyle(fg="blue", bold=True),
        "hl_lsn_offset": ColorStyle(fg="blue", bold=True),
        "hl_wal_segment": ColorStyle(fg="blue", bold=True),
        "hl_txid": ColorStyle(fg="magenta", bold=True),
        # Connection
        "hl_host": ColorStyle(fg="green", bold=True),
        "hl_port": ColorStyle(fg="green", bold=True),
        "hl_user": ColorStyle(fg="green", bold=True),
        "hl_database": ColorStyle(fg="green", bold=True, underline=True),
        "hl_ip": ColorStyle(fg="green", bold=True),
        "hl_backend": ColorStyle(fg="cyan", bold=True),
        # SQL (additional to existing sql_* keys)
        "hl_param": ColorStyle(fg="yellow", bold=True),
        # Lock
        "hl_lock_share": ColorStyle(fg="yellow", bold=True),
        "hl_lock_exclusive": ColorStyle(fg="red", bold=True),
        "hl_lock_wait": ColorStyle(fg="yellow", bold=True, underline=True),
        # Checkpoint/Recovery
        "hl_checkpoint": ColorStyle(fg="blue", bold=True),
        "hl_recovery": ColorStyle(fg="green", bold=True),
        # Misc
        "hl_bool_true": ColorStyle(fg="green", bold=True),
        "hl_bool_false": ColorStyle(fg="red", bold=True),
        "hl_null": ColorStyle(fg="white", italic=True),
        "hl_oid": ColorStyle(fg="magenta", bold=True),
        "hl_path": ColorStyle(fg="cyan", bold=True),
    },
)
