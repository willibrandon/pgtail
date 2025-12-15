"""PostgreSQL instance representation."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class DetectionSource(Enum):
    """How a PostgreSQL instance was detected."""

    PROCESS = "process"  # Running postgres process
    PGRX = "pgrx"  # ~/.pgrx/data-{version} directory
    PGDATA = "pgdata"  # PGDATA environment variable
    KNOWN_PATH = "known"  # Platform-specific default paths


@dataclass
class Instance:
    """A detected PostgreSQL installation.

    Attributes:
        id: Sequential ID for user reference (1, 2, 3...)
        version: PostgreSQL version string (e.g., "16.1")
        data_dir: Path to the data directory
        log_path: Path to log file, or None if logging is disabled
        source: How this instance was detected
        running: Whether the postgres process is currently running
        pid: Process ID if running, None otherwise
    """

    id: int
    version: str
    data_dir: Path
    log_path: Optional[Path]
    source: DetectionSource
    running: bool
    pid: Optional[int] = None

    @property
    def status_str(self) -> str:
        """Return a human-readable status string."""
        return "running" if self.running else "stopped"

    @property
    def log_status(self) -> str:
        """Return a human-readable log status."""
        if self.log_path is None:
            return "disabled"
        return str(self.log_path)
