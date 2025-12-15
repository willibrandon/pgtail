"""PostgreSQL instance representation."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
        id: Sequential ID for user reference (0, 1, 2...)
        version: PostgreSQL version string (e.g., "16.1")
        data_dir: Path to the data directory
        log_path: Path to log file, or None if logging is disabled
        source: How this instance was detected
        running: Whether the postgres process is currently running
        pid: Process ID if running, None otherwise
        port: PostgreSQL port number, or None if not detected
        logging_enabled: Whether logging_collector is enabled
    """

    id: int
    version: str
    data_dir: Path
    log_path: Path | None
    source: DetectionSource
    running: bool
    pid: int | None = None
    port: int | None = None
    logging_enabled: bool = False

    @property
    def status_str(self) -> str:
        """Return a human-readable status string."""
        return "running" if self.running else "stopped"

    @property
    def log_status(self) -> str:
        """Return on/off for logging status."""
        return "on" if self.logging_enabled else "off"

    @property
    def port_str(self) -> str:
        """Return port as string or '-' if not set."""
        return str(self.port) if self.port else "-"
