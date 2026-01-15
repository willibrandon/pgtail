"""Dark theme for pgtail (default).

Designed for dark terminal backgrounds with good contrast.
"""

from pgtail_py.theme import ColorStyle, Theme

DARK_THEME = Theme(
    name="dark",
    description="Default dark theme for dark terminal backgrounds",
    levels={
        "PANIC": ColorStyle(fg="white", bg="red", bold=True),
        "FATAL": ColorStyle(fg="red", bold=True),
        "ERROR": ColorStyle(fg="red"),
        "WARNING": ColorStyle(fg="yellow"),
        "NOTICE": ColorStyle(fg="cyan"),
        "LOG": ColorStyle(fg="ansidefault"),
        "INFO": ColorStyle(fg="green"),
        "DEBUG": ColorStyle(fg="ansibrightblack"),
        "DEBUG1": ColorStyle(fg="ansibrightblack"),
        "DEBUG2": ColorStyle(fg="ansibrightblack"),
        "DEBUG3": ColorStyle(fg="ansibrightblack"),
        "DEBUG4": ColorStyle(fg="ansibrightblack"),
        "DEBUG5": ColorStyle(fg="ansibrightblack"),
    },
    ui={
        "prompt": ColorStyle(fg="green"),
        "timestamp": ColorStyle(fg="ansibrightblack"),
        "pid": ColorStyle(fg="ansibrightblack"),
        "highlight": ColorStyle(fg="black", bg="yellow"),
        "slow_warning": ColorStyle(fg="yellow"),
        "slow_slow": ColorStyle(fg="yellow", bold=True),
        "slow_critical": ColorStyle(fg="red", bold=True),
        "detail": ColorStyle(fg="ansidefault"),
        # SQL syntax highlighting
        "sql_keyword": ColorStyle(fg="ansiblue", bold=True),
        "sql_identifier": ColorStyle(fg="ansicyan"),
        "sql_string": ColorStyle(fg="ansigreen"),
        "sql_number": ColorStyle(fg="ansimagenta"),
        "sql_operator": ColorStyle(fg="ansiyellow"),
        "sql_comment": ColorStyle(fg="ansibrightblack"),
        "sql_function": ColorStyle(fg="ansiblue"),
        # Status bar (tail mode)
        "status": ColorStyle(fg="ansiwhite", bg="ansiblue"),
        "status_follow": ColorStyle(fg="ansigreen", bg="ansiblue", bold=True),
        "status_paused": ColorStyle(fg="ansiyellow", bg="ansiblue", bold=True),
        "status_error": ColorStyle(fg="ansired", bg="ansiblue", bold=True),
        "status_warning": ColorStyle(fg="ansiyellow", bg="ansiblue"),
        "status_filter": ColorStyle(fg="ansicyan", bg="ansiblue"),
        "status_instance": ColorStyle(fg="ansiwhite", bg="ansiblue"),
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="ansigreen", bold=True),
        # Separator lines
        "separator": ColorStyle(fg="ansibrightblack"),
        # REPL bottom toolbar
        "bottom-toolbar": ColorStyle(fg="#cccccc", bg="#1a1a1a"),
        "bottom-toolbar.text": ColorStyle(fg="#cccccc", bg="#1a1a1a"),
        "toolbar": ColorStyle(fg="#cccccc", bg="#1a1a1a"),
        "toolbar.dim": ColorStyle(fg="#666666", bg="#1a1a1a"),
        "toolbar.filter": ColorStyle(fg="#55ffff", bg="#1a1a1a"),
        "toolbar.warning": ColorStyle(fg="#ffff55", bg="#1a1a1a"),
        "toolbar.shell": ColorStyle(fg="#ffffff", bg="#1a1a1a", bold=True),
        # Semantic highlighting (hl_* keys)
        # Structural
        "hl_timestamp_date": ColorStyle(fg="ansibrightblack"),
        "hl_timestamp_time": ColorStyle(fg="ansibrightblack"),
        "hl_timestamp_ms": ColorStyle(fg="ansibrightblack", dim=True),
        "hl_timestamp_tz": ColorStyle(fg="ansibrightblack", dim=True),
        "hl_pid": ColorStyle(fg="ansicyan"),
        "hl_context": ColorStyle(fg="ansiyellow", bold=True),
        # Diagnostic
        "hl_sqlstate_success": ColorStyle(fg="ansigreen"),
        "hl_sqlstate_warning": ColorStyle(fg="ansiyellow"),
        "hl_sqlstate_error": ColorStyle(fg="ansired"),
        "hl_sqlstate_internal": ColorStyle(fg="ansired", bold=True),
        "hl_error_name": ColorStyle(fg="ansired"),
        # Performance
        "hl_duration_fast": ColorStyle(fg="ansigreen"),
        "hl_duration_slow": ColorStyle(fg="ansiyellow"),
        "hl_duration_very_slow": ColorStyle(fg="ansibrightyellow", bold=True),
        "hl_duration_critical": ColorStyle(fg="ansired", bold=True),
        "hl_memory_value": ColorStyle(fg="ansimagenta"),
        "hl_memory_unit": ColorStyle(fg="ansimagenta", dim=True),
        "hl_statistics": ColorStyle(fg="ansicyan"),
        # Objects
        "hl_identifier": ColorStyle(fg="ansicyan"),
        "hl_relation": ColorStyle(fg="ansicyan", bold=True),
        "hl_schema": ColorStyle(fg="ansicyan"),
        # WAL
        "hl_lsn_segment": ColorStyle(fg="ansiblue"),
        "hl_lsn_offset": ColorStyle(fg="ansiblue", dim=True),
        "hl_wal_segment": ColorStyle(fg="ansiblue"),
        "hl_txid": ColorStyle(fg="ansimagenta"),
        # Connection
        "hl_host": ColorStyle(fg="ansigreen"),
        "hl_port": ColorStyle(fg="ansigreen", dim=True),
        "hl_user": ColorStyle(fg="ansigreen"),
        "hl_database": ColorStyle(fg="ansigreen", bold=True),
        "hl_ip": ColorStyle(fg="ansigreen"),
        "hl_backend": ColorStyle(fg="ansicyan"),
        # SQL (additional to existing sql_* keys)
        "hl_param": ColorStyle(fg="ansiyellow"),
        # Lock
        "hl_lock_share": ColorStyle(fg="ansiyellow"),
        "hl_lock_exclusive": ColorStyle(fg="ansired"),
        "hl_lock_wait": ColorStyle(fg="ansibrightyellow"),
        # Checkpoint/Recovery
        "hl_checkpoint": ColorStyle(fg="ansiblue"),
        "hl_recovery": ColorStyle(fg="ansigreen"),
        # Misc
        "hl_bool_true": ColorStyle(fg="ansigreen"),
        "hl_bool_false": ColorStyle(fg="ansired"),
        "hl_null": ColorStyle(fg="ansibrightblack", italic=True),
        "hl_oid": ColorStyle(fg="ansimagenta"),
        "hl_path": ColorStyle(fg="ansicyan"),
    },
)
