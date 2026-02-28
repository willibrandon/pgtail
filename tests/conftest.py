"""Shared test fixtures and helpers."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest


@contextlib.contextmanager
def deny_read_access(path: Path) -> Generator[None, None, None]:
    """Cross-platform context manager that denies read access to a file.

    On Unix: uses chmod(0o000) to remove all permissions.
    On Windows: uses icacls to add a deny ACE for the current user.

    The original permissions are restored when the context exits.
    """
    if sys.platform == "win32":
        user = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", str(path), "/deny", f"{user}:(R)"],
            check=True,
            capture_output=True,
        )
        try:
            yield
        finally:
            subprocess.run(
                ["icacls", str(path), "/remove:d", user],
                check=True,
                capture_output=True,
            )
    else:
        original_mode = path.stat().st_mode
        path.chmod(0o000)
        try:
            yield
        finally:
            path.chmod(original_mode)


@contextlib.contextmanager
def deny_write_access(path: Path) -> Generator[None, None, None]:
    """Cross-platform context manager that denies write access to a file.

    On Unix: uses chmod(0o444) to make read-only.
    On Windows: uses icacls to add a deny ACE for write.

    The original permissions are restored when the context exits.
    """
    if sys.platform == "win32":
        user = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", str(path), "/deny", f"{user}:(W)"],
            check=True,
            capture_output=True,
        )
        try:
            yield
        finally:
            subprocess.run(
                ["icacls", str(path), "/remove:d", user],
                check=True,
                capture_output=True,
            )
    else:
        original_mode = path.stat().st_mode
        path.chmod(0o444)
        try:
            yield
        finally:
            path.chmod(original_mode)


@pytest.fixture
def skip_if_root():
    """Skip test if running as root (chmod has no effect for root)."""
    if sys.platform != "win32" and os.getuid() == 0:
        pytest.skip("chmod has no effect when running as root")
