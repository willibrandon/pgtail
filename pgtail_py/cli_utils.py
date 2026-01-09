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


def validate_file_path(path_str: str) -> tuple[Path, str | None]:
    """Validate a file path for tailing.

    Validates that the path exists, is a regular file (not a directory),
    and is readable. Handles tilde (~) expansion for home directory.

    Args:
        path_str: User-provided path string.

    Returns:
        Tuple of (resolved_path, error_message).
        If error_message is None, path is valid.
    """
    # Expand tilde (~) to home directory (T085)
    expanded = Path(path_str).expanduser()
    resolved = expanded.resolve()

    if not resolved.exists():
        return resolved, f"File not found: {resolved}"

    if resolved.is_dir():
        return resolved, f"Not a file: {resolved} (is a directory)"

    try:
        # Check read permission by attempting to open
        with open(resolved, "rb"):
            pass
    except PermissionError:
        return resolved, f"Permission denied: {resolved}"
    except OSError as e:
        return resolved, f"Cannot access file: {resolved} ({e})"

    return resolved, None  # Valid


def validate_tail_args(
    file_path: str | None,
    instance_id: int | None,
    stdin_mode: bool = False,
) -> str | None:
    """Validate tail command arguments for mutual exclusivity.

    Args:
        file_path: Path to file to tail, or None.
        instance_id: Instance ID to tail, or None.
        stdin_mode: Whether --stdin flag was provided.

    Returns:
        Error message if invalid, None if valid.
    """
    # Count how many sources are specified
    sources = sum([
        file_path is not None,
        instance_id is not None,
        stdin_mode,
    ])

    if sources > 1:
        if file_path is not None and instance_id is not None:
            return "Cannot specify both --file and instance ID"
        if stdin_mode and instance_id is not None:
            return "Cannot specify both --stdin and instance ID"
        if stdin_mode and file_path is not None:
            return "Cannot specify both --stdin and --file"

    return None


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
