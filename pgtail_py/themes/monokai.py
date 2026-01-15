"""Monokai theme for pgtail.

Based on the popular Monokai color scheme for code editors.
"""

from pgtail_py.theme import ColorStyle, Theme

MONOKAI_THEME = Theme(
    name="monokai",
    description="Monokai editor color scheme",
    levels={
        "PANIC": ColorStyle(fg="#f8f8f2", bg="#f92672", bold=True),
        "FATAL": ColorStyle(fg="#f92672", bold=True),
        "ERROR": ColorStyle(fg="#f92672"),
        "WARNING": ColorStyle(fg="#fd971f"),
        "NOTICE": ColorStyle(fg="#66d9ef"),
        "LOG": ColorStyle(fg="#f8f8f2"),
        "INFO": ColorStyle(fg="#a6e22e"),
        "DEBUG": ColorStyle(fg="#75715e"),
        "DEBUG1": ColorStyle(fg="#75715e"),
        "DEBUG2": ColorStyle(fg="#75715e"),
        "DEBUG3": ColorStyle(fg="#75715e"),
        "DEBUG4": ColorStyle(fg="#75715e"),
        "DEBUG5": ColorStyle(fg="#75715e"),
    },
    ui={
        "prompt": ColorStyle(fg="#a6e22e"),
        "timestamp": ColorStyle(fg="#75715e"),
        "pid": ColorStyle(fg="#75715e"),
        "highlight": ColorStyle(fg="#272822", bg="#e6db74"),
        "slow_warning": ColorStyle(fg="#fd971f"),
        "slow_slow": ColorStyle(fg="#fd971f", bold=True),
        "slow_critical": ColorStyle(fg="#f92672", bold=True),
        "detail": ColorStyle(fg="#f8f8f2"),
        # SQL syntax highlighting (Monokai palette)
        "sql_keyword": ColorStyle(fg="#f92672", bold=True),  # Pink
        "sql_identifier": ColorStyle(fg="#66d9ef"),  # Cyan
        "sql_string": ColorStyle(fg="#e6db74"),  # Yellow
        "sql_number": ColorStyle(fg="#ae81ff"),  # Purple
        "sql_operator": ColorStyle(fg="#f8f8f2"),  # White
        "sql_comment": ColorStyle(fg="#75715e"),  # Gray
        "sql_function": ColorStyle(fg="#a6e22e"),  # Green
        # Status bar (tail mode) - Monokai palette
        "status": ColorStyle(fg="#f8f8f2", bg="#3e3d32"),  # Light text on dark gray
        "status_follow": ColorStyle(fg="#a6e22e", bg="#3e3d32", bold=True),  # Green
        "status_paused": ColorStyle(fg="#fd971f", bg="#3e3d32", bold=True),  # Orange
        "status_error": ColorStyle(fg="#f92672", bg="#3e3d32", bold=True),  # Pink
        "status_warning": ColorStyle(fg="#fd971f", bg="#3e3d32"),  # Orange
        "status_filter": ColorStyle(fg="#66d9ef", bg="#3e3d32"),  # Cyan
        "status_instance": ColorStyle(fg="#f8f8f2", bg="#3e3d32"),
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="#a6e22e", bold=True),  # Green
        # Separator lines
        "separator": ColorStyle(fg="#75715e"),  # Gray
        # REPL bottom toolbar (Monokai palette)
        "bottom-toolbar": ColorStyle(fg="#f8f8f2", bg="#3e3d32"),
        "bottom-toolbar.text": ColorStyle(fg="#f8f8f2", bg="#3e3d32"),
        "toolbar": ColorStyle(fg="#f8f8f2", bg="#3e3d32"),
        "toolbar.dim": ColorStyle(fg="#75715e", bg="#3e3d32"),
        "toolbar.filter": ColorStyle(fg="#66d9ef", bg="#3e3d32"),
        "toolbar.warning": ColorStyle(fg="#fd971f", bg="#3e3d32"),
        "toolbar.shell": ColorStyle(fg="#f8f8f2", bg="#3e3d32", bold=True),
        # Semantic highlighting (hl_* keys) - Monokai palette
        # Structural
        "hl_timestamp_date": ColorStyle(fg="#75715e"),
        "hl_timestamp_time": ColorStyle(fg="#75715e"),
        "hl_timestamp_ms": ColorStyle(fg="#75715e", dim=True),
        "hl_timestamp_tz": ColorStyle(fg="#75715e", dim=True),
        "hl_pid": ColorStyle(fg="#66d9ef"),  # Cyan
        "hl_context": ColorStyle(fg="#fd971f", bold=True),  # Orange
        # Diagnostic
        "hl_sqlstate_success": ColorStyle(fg="#a6e22e"),  # Green
        "hl_sqlstate_warning": ColorStyle(fg="#fd971f"),  # Orange
        "hl_sqlstate_error": ColorStyle(fg="#f92672"),  # Pink
        "hl_sqlstate_internal": ColorStyle(fg="#f92672", bold=True),
        "hl_error_name": ColorStyle(fg="#f92672"),  # Pink
        # Performance
        "hl_duration_fast": ColorStyle(fg="#a6e22e"),  # Green
        "hl_duration_slow": ColorStyle(fg="#fd971f"),  # Orange
        "hl_duration_very_slow": ColorStyle(fg="#fd971f", bold=True),
        "hl_duration_critical": ColorStyle(fg="#f92672", bold=True),  # Pink
        "hl_memory_value": ColorStyle(fg="#ae81ff"),  # Purple
        "hl_memory_unit": ColorStyle(fg="#ae81ff", dim=True),
        "hl_statistics": ColorStyle(fg="#66d9ef"),  # Cyan
        # Objects
        "hl_identifier": ColorStyle(fg="#66d9ef"),  # Cyan
        "hl_relation": ColorStyle(fg="#66d9ef", bold=True),
        "hl_schema": ColorStyle(fg="#66d9ef"),
        # WAL
        "hl_lsn_segment": ColorStyle(fg="#ae81ff"),  # Purple
        "hl_lsn_offset": ColorStyle(fg="#ae81ff", dim=True),
        "hl_wal_segment": ColorStyle(fg="#ae81ff"),
        "hl_txid": ColorStyle(fg="#ae81ff"),  # Purple
        # Connection
        "hl_host": ColorStyle(fg="#a6e22e"),  # Green
        "hl_port": ColorStyle(fg="#a6e22e", dim=True),
        "hl_user": ColorStyle(fg="#a6e22e"),
        "hl_database": ColorStyle(fg="#a6e22e", bold=True),
        "hl_ip": ColorStyle(fg="#a6e22e"),
        "hl_backend": ColorStyle(fg="#66d9ef"),  # Cyan
        # SQL (additional to existing sql_* keys)
        "hl_param": ColorStyle(fg="#e6db74"),  # Yellow
        # Lock
        "hl_lock_share": ColorStyle(fg="#e6db74"),  # Yellow
        "hl_lock_exclusive": ColorStyle(fg="#f92672"),  # Pink
        "hl_lock_wait": ColorStyle(fg="#fd971f", bold=True),  # Orange
        # Checkpoint/Recovery
        "hl_checkpoint": ColorStyle(fg="#ae81ff"),  # Purple
        "hl_recovery": ColorStyle(fg="#a6e22e"),  # Green
        # Misc
        "hl_bool_true": ColorStyle(fg="#a6e22e"),  # Green
        "hl_bool_false": ColorStyle(fg="#f92672"),  # Pink
        "hl_null": ColorStyle(fg="#75715e", italic=True),  # Gray
        "hl_oid": ColorStyle(fg="#ae81ff"),  # Purple
        "hl_path": ColorStyle(fg="#66d9ef"),  # Cyan
    },
)
