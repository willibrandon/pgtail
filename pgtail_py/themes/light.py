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
    },
)
