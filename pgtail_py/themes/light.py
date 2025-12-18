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
    },
)
