"""Windows-specific PostgreSQL instance detection."""

import os
from collections.abc import Iterator
from pathlib import Path

import psutil

from pgtail_py.instance import DetectionSource


def detect_from_processes() -> Iterator[tuple[Path, int]]:
    """Detect PostgreSQL instances from running postgres processes on Windows.

    Yields:
        Tuples of (data_dir, pid) for each detected postgres process.
    """
    for proc in psutil.process_iter(["name", "cmdline", "pid"]):
        try:
            info = proc.info
            name = info.get("name", "")
            if name.lower() not in ("postgres.exe", "pg_ctl.exe"):
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
    """Detect PostgreSQL instances from pgrx data directories on Windows.

    Yields:
        Tuples of (data_dir, DetectionSource.PGRX) for each found directory.
    """
    # pgrx uses same path pattern on Windows
    pgrx_dir = Path.home() / ".pgrx"
    if not pgrx_dir.is_dir():
        return

    try:
        for entry in pgrx_dir.iterdir():
            if entry.name.startswith("data-") and entry.is_dir():
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
    """Detect PostgreSQL instances from Windows-specific default paths.

    Yields:
        Tuples of (data_dir, DetectionSource.KNOWN_PATH) for each found directory.
    """
    known_paths = []

    # Program Files locations
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    for pf in [program_files, program_files_x86]:
        pf_path = Path(pf)
        if pf_path.is_dir():
            # Check for PostgreSQL installations
            for pg_dir in pf_path.glob("PostgreSQL/*"):
                data_dir = pg_dir / "data"
                if data_dir.is_dir():
                    known_paths.append(data_dir)

    # Common user data locations
    appdata = os.environ.get("APPDATA")
    if appdata:
        known_paths.append(Path(appdata) / "PostgreSQL" / "data")

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        known_paths.append(Path(localappdata) / "PostgreSQL" / "data")

    # User home locations
    home = Path.home()
    known_paths.extend([
        home / "postgres",
        home / "postgresql",
        home / "PostgreSQL" / "data",
    ])

    for path in known_paths:
        try:
            if path.is_dir() and (path / "PG_VERSION").exists():
                yield (path, DetectionSource.KNOWN_PATH)
        except PermissionError:
            continue
