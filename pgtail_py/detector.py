"""PostgreSQL instance detection - platform dispatcher."""

import re
import sys
from pathlib import Path
from typing import Optional

from pgtail_py.instance import DetectionSource, Instance

# Import platform-specific module
if sys.platform == "win32":
    from pgtail_py import detector_windows as platform_detector
else:
    from pgtail_py import detector_unix as platform_detector


def get_version(data_dir: Path) -> str:
    """Read PostgreSQL version from PG_VERSION file.

    Args:
        data_dir: Path to the PostgreSQL data directory.

    Returns:
        Version string (e.g., "16" or "15.4"), or "unknown" if not readable.
    """
    pg_version_file = data_dir / "PG_VERSION"
    try:
        return pg_version_file.read_text().strip()
    except (OSError, PermissionError):
        return "unknown"


def get_log_path(data_dir: Path) -> Optional[Path]:
    """Find the log file path for a PostgreSQL instance.

    Checks postgresql.conf for logging_collector, log_directory, and log_filename
    settings. Returns None if logging is not enabled.

    Args:
        data_dir: Path to the PostgreSQL data directory.

    Returns:
        Path to the current log file, or None if logging is disabled.
    """
    conf_file = data_dir / "postgresql.conf"
    if not conf_file.exists():
        return None

    try:
        conf_content = conf_file.read_text()
    except (OSError, PermissionError):
        return None

    # Check if logging_collector is enabled
    logging_enabled = _get_conf_value(conf_content, "logging_collector")
    if logging_enabled and logging_enabled.lower() not in ("on", "true", "yes", "1"):
        return None

    # Get log_directory (default: 'log' relative to data_dir)
    log_directory = _get_conf_value(conf_content, "log_directory") or "log"
    if not log_directory.startswith("/"):
        log_dir = data_dir / log_directory
    else:
        log_dir = Path(log_directory)

    if not log_dir.is_dir():
        # Try pg_log for older versions
        log_dir = data_dir / "pg_log"
        if not log_dir.is_dir():
            return None

    # Find the most recent log file
    return _find_latest_log(log_dir)


def _get_conf_value(content: str, key: str) -> Optional[str]:
    """Extract a configuration value from postgresql.conf content."""
    # Match: key = value or key = 'value'
    pattern = rf"^\s*{re.escape(key)}\s*=\s*['\"]?([^'\"#\n]+)['\"]?"
    for line in content.splitlines():
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _find_latest_log(log_dir: Path) -> Optional[Path]:
    """Find the most recently modified log file in a directory."""
    log_files = []
    try:
        for f in log_dir.iterdir():
            if f.suffix == ".log" or f.name.startswith("postgresql"):
                log_files.append(f)
    except (OSError, PermissionError):
        return None

    if not log_files:
        return None

    # Return most recently modified
    return max(log_files, key=lambda f: f.stat().st_mtime)


def _is_process_running(data_dir: Path, known_pids: dict[Path, int]) -> tuple[bool, Optional[int]]:
    """Check if a PostgreSQL process is running for this data directory."""
    pid = known_pids.get(data_dir)
    return (pid is not None, pid)


def detect_all() -> list[Instance]:
    """Detect all PostgreSQL instances on the system.

    Uses multiple detection methods in priority order:
    1. Running processes (highest priority - most accurate)
    2. pgrx data directories
    3. PGDATA environment variable
    4. Platform-specific known paths

    Returns:
        List of detected Instance objects, deduplicated by data directory.
    """
    instances: list[Instance] = []
    seen_dirs: set[Path] = set()

    # First, collect running process info
    process_pids: dict[Path, int] = {}
    try:
        for data_dir, pid in platform_detector.detect_from_processes():
            process_pids[data_dir.resolve()] = pid
    except Exception:
        pass  # Continue with other detection methods

    # Helper to add instance if not duplicate
    def add_instance(data_dir: Path, source: DetectionSource) -> None:
        resolved = data_dir.resolve()
        if resolved in seen_dirs:
            return
        seen_dirs.add(resolved)

        running, pid = _is_process_running(resolved, process_pids)
        # If found via process, it's definitely running
        if source == DetectionSource.PROCESS:
            running = True

        instance = Instance(
            id=len(instances) + 1,
            version=get_version(data_dir),
            data_dir=data_dir,
            log_path=get_log_path(data_dir),
            source=source,
            running=running,
            pid=pid,
        )
        instances.append(instance)

    # Add instances from running processes first
    for data_dir in process_pids:
        add_instance(data_dir, DetectionSource.PROCESS)

    # Then check pgrx directories
    try:
        for data_dir, source in platform_detector.detect_from_pgrx():
            add_instance(data_dir, source)
    except Exception:
        pass

    # Check PGDATA
    try:
        for data_dir, source in platform_detector.detect_from_pgdata():
            add_instance(data_dir, source)
    except Exception:
        pass

    # Check known paths
    try:
        for data_dir, source in platform_detector.detect_from_known_paths():
            add_instance(data_dir, source)
    except Exception:
        pass

    return instances
