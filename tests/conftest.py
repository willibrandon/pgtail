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
    On Windows: uses icacls to add a deny ACE for file read data.
        Denies only (RD) — not the full generic (R) — so that
        READ_CONTROL remains available for ACL cleanup.

    The original permissions are restored when the context exits.
    """
    if sys.platform == "win32":
        user = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", str(path), "/deny", f"{user}:(RD)"],
            check=True,
            capture_output=True,
        )
        try:
            yield
        finally:
            # Remove deny ACE. Don't check=True — if cleanup fails,
            # the temp directory cleanup will handle the file.
            subprocess.run(
                ["icacls", str(path), "/remove:d", user],
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
    On Windows: uses icacls to add a deny ACE for write data and append data.

    The original permissions are restored when the context exits.
    """
    if sys.platform == "win32":
        user = os.environ.get("USERNAME", "")
        subprocess.run(
            ["icacls", str(path), "/deny", f"{user}:(WD,AD)"],
            check=True,
            capture_output=True,
        )
        try:
            yield
        finally:
            subprocess.run(
                ["icacls", str(path), "/remove:d", user],
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
