"""Unix-specific PostgreSQL instance detection (macOS and Linux)."""

import os
import re
from collections.abc import Iterator
from pathlib import Path

import psutil

from pgtail_py.instance import DetectionSource


def detect_from_processes() -> Iterator[tuple[Path, int]]:
    """Detect PostgreSQL instances from running postgres processes.

    Yields:
        Tuples of (data_dir, pid) for each detected postgres process.
    """
    for proc in psutil.process_iter(["name", "cmdline", "pid"]):
        try:
            info = proc.info
            name = info.get("name", "")
            if name not in ("postgres", "postmaster"):
                continue

            cmdline = info.get("cmdline") or []
            data_dir = _extract_data_dir(cmdline)
            if data_dir and data_dir.is_dir():
                yield (data_dir, info["pid"])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def _extract_data_dir(cmdline: list[str]) -> Path | None:
    """Extract the data directory from postgres command line arguments."""
    for i, arg in enumerate(cmdline):
        if arg == "-D" and i + 1 < len(cmdline):
            return Path(cmdline[i + 1])
        if arg.startswith("-D"):
            return Path(arg[2:])
        if arg.startswith("--data="):
            return Path(arg[7:])
    return None


def detect_from_pgrx() -> Iterator[tuple[Path, DetectionSource]]:
    """Detect PostgreSQL instances from pgrx data directories.

    Scans ~/.pgrx/data-* for PostgreSQL data directories.

    Yields:
        Tuples of (data_dir, DetectionSource.PGRX) for each found directory.
    """
    pgrx_dir = Path.home() / ".pgrx"
    if not pgrx_dir.is_dir():
        return

    pattern = re.compile(r"^data-\d+$")
    try:
        for entry in pgrx_dir.iterdir():
            if pattern.match(entry.name) and entry.is_dir():
                pg_version_file = entry / "PG_VERSION"
                if pg_version_file.exists():
                    yield (entry, DetectionSource.PGRX)
    except PermissionError:
        pass


def detect_from_pgdata() -> Iterator[tuple[Path, DetectionSource]]:
    """Detect PostgreSQL instance from PGDATA environment variable.

    Yields:
        Tuple of (data_dir, DetectionSource.PGDATA) if PGDATA is set and valid.
    """
    pgdata = os.environ.get("PGDATA")
    if pgdata:
        path = Path(pgdata)
        if path.is_dir() and (path / "PG_VERSION").exists():
            yield (path, DetectionSource.PGDATA)


def detect_from_known_paths() -> Iterator[tuple[Path, DetectionSource]]:
    """Detect PostgreSQL instances from platform-specific default paths.

    Yields:
        Tuples of (data_dir, DetectionSource.KNOWN_PATH) for each found directory.
    """
    known_paths = [
        # macOS Homebrew
        Path("/usr/local/var/postgres"),
        Path("/opt/homebrew/var/postgres"),
        Path("/usr/local/var/postgresql@16"),
        Path("/usr/local/var/postgresql@15"),
        Path("/usr/local/var/postgresql@14"),
        Path("/opt/homebrew/var/postgresql@16"),
        Path("/opt/homebrew/var/postgresql@15"),
        Path("/opt/homebrew/var/postgresql@14"),
        # Linux package managers
        Path("/var/lib/postgresql"),
        Path("/var/lib/pgsql/data"),
        # Common version-specific paths
        Path("/var/lib/postgresql/16/main"),
        Path("/var/lib/postgresql/15/main"),
        Path("/var/lib/postgresql/14/main"),
    ]

    # Also check user home directory
    home = Path.home()
    known_paths.extend(
        [
            home / "postgres",
            home / "postgresql",
            home / ".postgres",
        ]
    )

    for path in known_paths:
        try:
            if path.is_dir() and (path / "PG_VERSION").exists():
                yield (path, DetectionSource.KNOWN_PATH)
        except PermissionError:
            continue
