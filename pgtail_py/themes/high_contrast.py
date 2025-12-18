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
    },
)
