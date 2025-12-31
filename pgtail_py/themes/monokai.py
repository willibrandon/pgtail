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
    },
)
