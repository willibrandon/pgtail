"""PostgreSQL instance detection - platform dispatcher."""

import re
import sys
from pathlib import Path

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


def get_log_info(data_dir: Path) -> tuple[Path | None, Path | None, bool]:
    """Find the log file path for a PostgreSQL instance.

    Checks postgresql.conf for logging_collector, log_directory, and log_filename
    settings. Returns None if logging is not enabled.

    First tries PostgreSQL's current_logfiles (PG 10+) for the most accurate
    current log path, then falls back to finding the latest log by mtime.

    Args:
        data_dir: Path to the PostgreSQL data directory.

    Returns:
        Tuple of (log_file_path, log_directory, logging_enabled).
    """
    conf_file = data_dir / "postgresql.conf"
    if not conf_file.exists():
        return None, None, False

    try:
        conf_content = conf_file.read_text()
    except (OSError, PermissionError):
        return None, None, False

    # Check if logging_collector is enabled
    logging_enabled_str = _get_conf_value(conf_content, "logging_collector")
    logging_enabled = bool(
        logging_enabled_str and logging_enabled_str.lower() in ("on", "true", "yes", "1")
    )

    if not logging_enabled:
        return None, None, False

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
            return None, None, True  # logging enabled but no log dir yet

    # Try current_logfiles first (PostgreSQL 10+, most reliable)
    log_path = read_current_logfiles(data_dir)
    if log_path and log_path.exists():
        return log_path, log_dir, True

    # Fall back to finding most recent log file by mtime
    return find_latest_log(log_dir), log_dir, True


def get_port(data_dir: Path) -> int | None:
    """Read the PostgreSQL port from postgresql.conf or postmaster.pid.

    First tries postgresql.conf, then falls back to postmaster.pid
    (useful when port is passed via command line, e.g., pgrx).

    Args:
        data_dir: Path to the PostgreSQL data directory.

    Returns:
        Port number, or None if not configured.
    """
    # Try postgresql.conf first
    conf_file = data_dir / "postgresql.conf"
    if conf_file.exists():
        try:
            conf_content = conf_file.read_text()
            port_str = _get_conf_value(conf_content, "port")
            if port_str:
                return int(port_str)
        except (OSError, PermissionError, ValueError):
            pass

    # Fall back to postmaster.pid (line 4 contains port)
    postmaster_pid = data_dir / "postmaster.pid"
    if postmaster_pid.exists():
        try:
            content = postmaster_pid.read_text()
            lines = content.splitlines()
            if len(lines) >= 4:
                return int(lines[3].strip())
        except (OSError, ValueError, IndexError):
            pass

    return None


def _get_conf_value(content: str, key: str) -> str | None:
    """Extract a configuration value from postgresql.conf content."""
    # Match: key = value or key = 'value'
    pattern = rf"^\s*{re.escape(key)}\s*=\s*['\"]?([^'\"#\n]+)['\"]?"
    for line in content.splitlines():
        match = re.match(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def find_latest_log(log_dir: Path) -> Path | None:
    """Find the most recently modified log file in a directory."""
    log_files: list[Path] = []
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


def read_current_logfiles(data_dir: Path) -> Path | None:
    """Read the current log file path from PostgreSQL's current_logfiles.

    PostgreSQL 10+ maintains a current_logfiles file in PGDATA that contains
    the path to the current log file. This is updated atomically on every
    log rotation and server restart.

    Args:
        data_dir: Path to the PostgreSQL data directory.

    Returns:
        Path to current log file, or None if file doesn't exist or is unreadable.
    """
    current_logfiles = data_dir / "current_logfiles"
    try:
        content = current_logfiles.read_text()
        for line in content.splitlines():
            # Format: "stderr log/postgresql.log" or "stderr /absolute/path.log"
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[0] in ("stderr", "csvlog", "jsonlog"):
                path_str = parts[1]
                # Check for absolute path (Unix-style / or Windows drive letter)
                # On Windows, Path("/var/log").is_absolute() returns False,
                # but we should treat paths starting with / as absolute
                is_absolute = path_str.startswith("/") or (
                    len(path_str) >= 2 and path_str[1] == ":"
                )
                log_path = Path(path_str)
                # Handle relative paths (relative to data_dir)
                if not is_absolute:
                    log_path = data_dir / log_path
                return log_path
    except OSError:
        pass
    return None


def _is_process_running(data_dir: Path, known_pids: dict[Path, int]) -> tuple[bool, int | None]:
    """Check if a PostgreSQL process is running for this data directory.

    First checks if we found a running process with this data_dir.
    Falls back to checking postmaster.pid file and verifying the PID is alive.
    """
    import psutil

    # Check if we found this data_dir from process detection
    pid = known_pids.get(data_dir)
    if pid is not None:
        return (True, pid)

    # Fall back to postmaster.pid file check
    # This file exists when PostgreSQL is running and contains the PID
    postmaster_pid = data_dir / "postmaster.pid"
    if postmaster_pid.exists():
        try:
            # First line of postmaster.pid is the PID
            content = postmaster_pid.read_text()
            pid_line = content.splitlines()[0].strip()
            pid = int(pid_line)

            # Verify the process is actually running
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    # Check if it's actually a postgres process
                    if "postgres" in proc.name().lower():
                        return (True, pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (OSError, ValueError, IndexError):
            pass

    return (False, None)


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

        log_path, log_directory, logging_enabled = get_log_info(data_dir)

        instance = Instance(
            id=len(instances),  # 0-indexed like Go version
            version=get_version(data_dir),
            data_dir=data_dir,
            log_path=log_path,
            log_directory=log_directory,
            source=source,
            running=running,
            pid=pid,
            port=get_port(data_dir),
            logging_enabled=logging_enabled,
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
