"""Configuration and platform-specific paths."""

import os
import sys
from pathlib import Path

APP_NAME = "pgtail"


def get_history_path() -> Path:
    """Return the platform-appropriate path for command history.

    Returns:
        - Linux: ~/.local/share/pgtail/history (XDG_DATA_HOME)
        - macOS: ~/Library/Application Support/pgtail/history
        - Windows: %APPDATA%/pgtail/history
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux and other Unix-like systems
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

    return base / APP_NAME / "history"


def ensure_history_dir() -> Path:
    """Ensure the history directory exists and return the history file path."""
    history_path = get_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return history_path
