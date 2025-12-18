"""Solarized Dark theme for pgtail.

Based on Ethan Schoonover's Solarized color palette.
Designed for reduced eye strain on dark backgrounds.
"""

from pgtail_py.theme import ColorStyle, Theme

SOLARIZED_DARK_THEME = Theme(
    name="solarized-dark",
    description="Solarized dark color scheme for reduced eye strain",
    levels={
        # Solarized base colors for dark background
        # base03: #002b36 (background)
        # base0: #839496 (body text)
        "PANIC": ColorStyle(fg="#fdf6e3", bg="#dc322f", bold=True),
        "FATAL": ColorStyle(fg="#dc322f", bold=True),
        "ERROR": ColorStyle(fg="#dc322f"),
        "WARNING": ColorStyle(fg="#b58900"),
        "NOTICE": ColorStyle(fg="#2aa198"),
        "LOG": ColorStyle(fg="#839496"),
        "INFO": ColorStyle(fg="#859900"),
        "DEBUG": ColorStyle(fg="#586e75"),
        "DEBUG1": ColorStyle(fg="#586e75"),
        "DEBUG2": ColorStyle(fg="#586e75"),
        "DEBUG3": ColorStyle(fg="#586e75"),
        "DEBUG4": ColorStyle(fg="#586e75"),
        "DEBUG5": ColorStyle(fg="#586e75"),
    },
    ui={
        "prompt": ColorStyle(fg="#859900"),
        "timestamp": ColorStyle(fg="#586e75"),
        "pid": ColorStyle(fg="#586e75"),
        "highlight": ColorStyle(fg="#002b36", bg="#b58900"),
        "slow_warning": ColorStyle(fg="#b58900"),
        "slow_slow": ColorStyle(fg="#cb4b16", bold=True),
        "slow_critical": ColorStyle(fg="#dc322f", bold=True),
        "detail": ColorStyle(fg="#839496"),
    },
)
