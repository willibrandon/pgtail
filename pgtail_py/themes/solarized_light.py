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
    },
)
