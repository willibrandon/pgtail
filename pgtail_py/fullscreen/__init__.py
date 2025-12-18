"""Fullscreen TUI mode for pgtail.

This package provides a full-screen terminal UI for viewing PostgreSQL logs
with vim-style navigation, search, and mouse support.
"""

from pgtail_py.fullscreen.app import create_fullscreen_app, run_fullscreen
from pgtail_py.fullscreen.buffer import LogBuffer
from pgtail_py.fullscreen.keybindings import create_keybindings
from pgtail_py.fullscreen.layout import create_layout
from pgtail_py.fullscreen.state import DisplayMode, FullscreenState

__all__ = [
    "DisplayMode",
    "FullscreenState",
    "LogBuffer",
    "create_fullscreen_app",
    "create_keybindings",
    "create_layout",
    "run_fullscreen",
]
