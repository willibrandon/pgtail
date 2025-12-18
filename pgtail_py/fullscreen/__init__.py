"""Fullscreen TUI mode for pgtail.

This package provides a full-screen terminal UI for viewing PostgreSQL logs
with vim-style navigation, search, and mouse support.
"""

from pgtail_py.fullscreen.buffer import LogBuffer
from pgtail_py.fullscreen.state import DisplayMode, FullscreenState

__all__ = [
    "DisplayMode",
    "FullscreenState",
    "LogBuffer",
]
