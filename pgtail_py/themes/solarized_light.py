"""Solarized Light theme for pgtail.

Based on Ethan Schoonover's Solarized color palette.
Designed for reduced eye strain on light backgrounds.
"""

from pgtail_py.theme import ColorStyle, Theme

SOLARIZED_LIGHT_THEME = Theme(
    name="solarized-light",
    description="Solarized light color scheme for reduced eye strain",
    levels={
        # Solarized base colors for light background
        # base3: #fdf6e3 (background)
        # base00: #657b83 (body text)
        "PANIC": ColorStyle(fg="#fdf6e3", bg="#dc322f", bold=True),
        "FATAL": ColorStyle(fg="#dc322f", bold=True),
        "ERROR": ColorStyle(fg="#dc322f"),
        "WARNING": ColorStyle(fg="#b58900"),
        "NOTICE": ColorStyle(fg="#2aa198"),
        "LOG": ColorStyle(fg="#657b83"),
        "INFO": ColorStyle(fg="#859900"),
        "DEBUG": ColorStyle(fg="#93a1a1"),
        "DEBUG1": ColorStyle(fg="#93a1a1"),
        "DEBUG2": ColorStyle(fg="#93a1a1"),
        "DEBUG3": ColorStyle(fg="#93a1a1"),
        "DEBUG4": ColorStyle(fg="#93a1a1"),
        "DEBUG5": ColorStyle(fg="#93a1a1"),
    },
    ui={
        "prompt": ColorStyle(fg="#859900"),
        "timestamp": ColorStyle(fg="#93a1a1"),
        "pid": ColorStyle(fg="#93a1a1"),
        "highlight": ColorStyle(fg="#fdf6e3", bg="#b58900"),
        "slow_warning": ColorStyle(fg="#b58900"),
        "slow_slow": ColorStyle(fg="#cb4b16", bold=True),
        "slow_critical": ColorStyle(fg="#dc322f", bold=True),
        "detail": ColorStyle(fg="#657b83"),
        # SQL syntax highlighting (Solarized light palette)
        "sql_keyword": ColorStyle(fg="#268bd2", bold=True),  # Blue
        "sql_identifier": ColorStyle(fg="#2aa198"),  # Cyan
        "sql_string": ColorStyle(fg="#859900"),  # Green
        "sql_number": ColorStyle(fg="#d33682"),  # Magenta
        "sql_operator": ColorStyle(fg="#b58900"),  # Yellow
        "sql_comment": ColorStyle(fg="#93a1a1"),  # Base1 (gray)
        "sql_function": ColorStyle(fg="#268bd2"),  # Blue
        # Status bar (tail mode) - Solarized light palette
        "status": ColorStyle(fg="#657b83", bg="#eee8d5"),  # Base00 on Base2
        "status_follow": ColorStyle(fg="#859900", bg="#eee8d5", bold=True),  # Green
        "status_paused": ColorStyle(fg="#b58900", bg="#eee8d5", bold=True),  # Yellow
        "status_error": ColorStyle(fg="#dc322f", bg="#eee8d5", bold=True),  # Red
        "status_warning": ColorStyle(fg="#b58900", bg="#eee8d5"),  # Yellow
        "status_filter": ColorStyle(fg="#2aa198", bg="#eee8d5"),  # Cyan
        "status_instance": ColorStyle(fg="#657b83", bg="#eee8d5"),  # Base00
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="#859900", bold=True),  # Green
        # Separator lines
        "separator": ColorStyle(fg="#93a1a1"),  # Base1
        # REPL bottom toolbar (Solarized light palette)
        "bottom-toolbar": ColorStyle(fg="#657b83", bg="#eee8d5"),  # Base00 on Base2
        "bottom-toolbar.text": ColorStyle(fg="#657b83", bg="#eee8d5"),
        "toolbar": ColorStyle(fg="#657b83", bg="#eee8d5"),  # Base00 on Base2
        "toolbar.dim": ColorStyle(fg="#93a1a1", bg="#eee8d5"),  # Base1
        "toolbar.filter": ColorStyle(fg="#2aa198", bg="#eee8d5"),  # Cyan
        "toolbar.warning": ColorStyle(fg="#b58900", bg="#eee8d5"),  # Yellow
        "toolbar.shell": ColorStyle(fg="#002b36", bg="#eee8d5", bold=True),  # Base03
        # Semantic highlighting (hl_* keys) - Solarized light palette
        # Structural
        "hl_timestamp_date": ColorStyle(fg="#93a1a1"),  # Base1
        "hl_timestamp_time": ColorStyle(fg="#93a1a1"),
        "hl_timestamp_ms": ColorStyle(fg="#93a1a1", dim=True),
        "hl_timestamp_tz": ColorStyle(fg="#93a1a1", dim=True),
        "hl_pid": ColorStyle(fg="#2aa198"),  # Cyan
        "hl_context": ColorStyle(fg="#b58900", bold=True),  # Yellow
        # Diagnostic
        "hl_sqlstate_success": ColorStyle(fg="#859900"),  # Green
        "hl_sqlstate_warning": ColorStyle(fg="#b58900"),  # Yellow
        "hl_sqlstate_error": ColorStyle(fg="#dc322f"),  # Red
        "hl_sqlstate_internal": ColorStyle(fg="#dc322f", bold=True),
        "hl_error_name": ColorStyle(fg="#dc322f"),  # Red
        # Performance
        "hl_duration_fast": ColorStyle(fg="#859900"),  # Green
        "hl_duration_slow": ColorStyle(fg="#b58900"),  # Yellow
        "hl_duration_very_slow": ColorStyle(fg="#cb4b16", bold=True),  # Orange
        "hl_duration_critical": ColorStyle(fg="#dc322f", bold=True),  # Red
        "hl_memory_value": ColorStyle(fg="#d33682"),  # Magenta
        "hl_memory_unit": ColorStyle(fg="#d33682", dim=True),
        "hl_statistics": ColorStyle(fg="#2aa198"),  # Cyan
        # Objects
        "hl_identifier": ColorStyle(fg="#2aa198"),  # Cyan
        "hl_relation": ColorStyle(fg="#2aa198", bold=True),
        "hl_schema": ColorStyle(fg="#2aa198"),
        # WAL
        "hl_lsn_segment": ColorStyle(fg="#268bd2"),  # Blue
        "hl_lsn_offset": ColorStyle(fg="#268bd2", dim=True),
        "hl_wal_segment": ColorStyle(fg="#268bd2"),
        "hl_txid": ColorStyle(fg="#d33682"),  # Magenta
        # Connection
        "hl_host": ColorStyle(fg="#859900"),  # Green
        "hl_port": ColorStyle(fg="#859900", dim=True),
        "hl_user": ColorStyle(fg="#859900"),
        "hl_database": ColorStyle(fg="#859900", bold=True),
        "hl_ip": ColorStyle(fg="#859900"),
        "hl_backend": ColorStyle(fg="#2aa198"),  # Cyan
        # SQL (additional to existing sql_* keys)
        "hl_param": ColorStyle(fg="#b58900"),  # Yellow
        # Lock
        "hl_lock_share": ColorStyle(fg="#b58900"),  # Yellow
        "hl_lock_exclusive": ColorStyle(fg="#dc322f"),  # Red
        "hl_lock_wait": ColorStyle(fg="#cb4b16", bold=True),  # Orange
        # Checkpoint/Recovery
        "hl_checkpoint": ColorStyle(fg="#268bd2"),  # Blue
        "hl_recovery": ColorStyle(fg="#859900"),  # Green
        # Misc
        "hl_bool_true": ColorStyle(fg="#859900"),  # Green
        "hl_bool_false": ColorStyle(fg="#dc322f"),  # Red
        "hl_null": ColorStyle(fg="#93a1a1", italic=True),  # Base1
        "hl_oid": ColorStyle(fg="#d33682"),  # Magenta
        "hl_path": ColorStyle(fg="#2aa198"),  # Cyan
    },
)
