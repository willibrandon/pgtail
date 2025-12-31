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
    },
)
