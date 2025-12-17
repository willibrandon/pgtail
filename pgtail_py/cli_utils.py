"""Shared utility functions for CLI commands."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance


def warn(msg: str) -> None:
    """Print a warning message.

    Args:
        msg: Warning message to display.
    """
    print(f"Warning: {msg}")


def shorten_path(path: Path) -> str:
    """Replace home directory with ~ for display.

    Args:
        path: Path to shorten.

    Returns:
        Path string with home directory replaced by ~.
    """
    home = Path.home()
    path_str = str(path)
    home_str = str(home)
    if path_str.startswith(home_str):
        return "~" + path_str[len(home_str) :]
    return path_str


def detect_windows_shell() -> str:
    """Detect the parent shell on Windows.

    Returns:
        'powershell' if running from PowerShell, 'cmd' otherwise.
    """
    import psutil

    try:
        proc = psutil.Process()
        # Walk up the process tree to find the shell
        for _ in range(5):  # Check up to 5 levels
            parent = proc.parent()
            if parent is None:
                break
            name = parent.name().lower()
            if "powershell" in name or "pwsh" in name:
                return "powershell"
            if name == "cmd.exe":
                return "cmd"
            proc = parent
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    # Default to PowerShell on modern Windows
    return "powershell"


def run_shell(cmd_line: str) -> None:
    """Run a shell command.

    Args:
        cmd_line: The command to run.
    """
    if not cmd_line:
        return

    if sys.platform == "win32":
        shell = detect_windows_shell()
        if shell == "powershell":
            shell_cmd = ["powershell", "-NoProfile", "-Command", cmd_line]
        else:
            shell_cmd = ["cmd", "/c", cmd_line]
    else:
        shell_cmd = ["sh", "-c", cmd_line]

    try:
        subprocess.run(shell_cmd, check=False)
    except Exception as e:
        print(f"Shell error: {e}")


def find_instance(state: AppState, arg: str) -> Instance | None:
    """Find an instance by ID or path.

    Args:
        state: Current application state.
        arg: Instance ID (number) or data directory path.

    Returns:
        Instance if found, None otherwise.
    """
    # Try as numeric ID first
    try:
        instance_id = int(arg)
        for inst in state.instances:
            if inst.id == instance_id:
                return inst
        return None
    except ValueError:
        pass

    # Try as path
    path = Path(arg).resolve()
    for inst in state.instances:
        if inst.data_dir.resolve() == path:
            return inst

    return None
