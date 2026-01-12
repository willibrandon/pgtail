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
        log_directory: Directory containing log files, for detecting new logs
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
    log_directory: Path | None
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

    @classmethod
    def file_only(cls, log_path: Path) -> "Instance":
        """Create a file-only instance for tailing arbitrary log files.

        Creates a minimal Instance object when tailing an arbitrary log file
        that isn't associated with a detected PostgreSQL installation.

        Args:
            log_path: Path to the log file being tailed.

        Returns:
            Instance with minimal fields set, suitable for file-only tailing.
        """
        return cls(
            id=-1,  # Negative ID indicates file-only mode
            version="",
            data_dir=log_path.parent,
            log_path=log_path,
            log_directory=log_path.parent,
            source=DetectionSource.KNOWN_PATH,  # Closest match for arbitrary file
            running=True,  # Assume the source is active (being written to)
            pid=None,
            port=None,
            logging_enabled=True,
        )
