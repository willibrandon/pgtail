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
    },
)
