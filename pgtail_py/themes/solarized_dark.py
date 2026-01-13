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
        # SQL syntax highlighting (Solarized dark palette)
        "sql_keyword": ColorStyle(fg="#268bd2", bold=True),  # Blue
        "sql_identifier": ColorStyle(fg="#2aa198"),  # Cyan
        "sql_string": ColorStyle(fg="#859900"),  # Green
        "sql_number": ColorStyle(fg="#d33682"),  # Magenta
        "sql_operator": ColorStyle(fg="#b58900"),  # Yellow
        "sql_comment": ColorStyle(fg="#586e75"),  # Base01 (gray)
        "sql_function": ColorStyle(fg="#268bd2"),  # Blue
        # Status bar (tail mode) - Solarized dark palette
        "status": ColorStyle(fg="#839496", bg="#073642"),  # Base0 on Base02
        "status_follow": ColorStyle(fg="#859900", bg="#073642", bold=True),  # Green
        "status_paused": ColorStyle(fg="#b58900", bg="#073642", bold=True),  # Yellow
        "status_error": ColorStyle(fg="#dc322f", bg="#073642", bold=True),  # Red
        "status_warning": ColorStyle(fg="#b58900", bg="#073642"),  # Yellow
        "status_filter": ColorStyle(fg="#2aa198", bg="#073642"),  # Cyan
        "status_instance": ColorStyle(fg="#839496", bg="#073642"),  # Base0
        # Input line (tail mode)
        "input": ColorStyle(),
        "input_prompt": ColorStyle(fg="#859900", bold=True),  # Green
        # Separator lines
        "separator": ColorStyle(fg="#586e75"),  # Base01
        # REPL bottom toolbar (Solarized dark palette)
        "bottom-toolbar": ColorStyle(fg="#839496", bg="#073642"),  # Base0 on Base02
        "bottom-toolbar.text": ColorStyle(fg="#839496", bg="#073642"),
        "toolbar": ColorStyle(fg="#839496", bg="#073642"),  # Base0 on Base02
        "toolbar.dim": ColorStyle(fg="#586e75", bg="#073642"),  # Base01
        "toolbar.filter": ColorStyle(fg="#2aa198", bg="#073642"),  # Cyan
        "toolbar.warning": ColorStyle(fg="#b58900", bg="#073642"),  # Yellow
        "toolbar.shell": ColorStyle(fg="#fdf6e3", bg="#073642", bold=True),  # Base3
    },
)
