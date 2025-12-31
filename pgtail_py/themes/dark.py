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
    },
)
