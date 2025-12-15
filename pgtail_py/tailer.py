"""Log file tailing with polling."""

import os
import threading
import time
from pathlib import Path
from queue import Empty, Queue

from pgtail_py.colors import print_log_entry
from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry, parse_log_line
from pgtail_py.regex_filter import FilterState


class LogTailer:
    """Tail a PostgreSQL log file with real-time updates.

    Uses simple polling for reliable cross-platform file monitoring.
    Handles log rotation by detecting file truncation or recreation.
    """

    def __init__(
        self,
        log_path: Path,
        active_levels: set[LogLevel] | None = None,
        regex_state: FilterState | None = None,
        poll_interval: float = 0.1,
    ) -> None:
        """Initialize the log tailer.

        Args:
            log_path: Path to the log file to tail.
            active_levels: Set of log levels to display. None means all.
            regex_state: Regex filter state. None means no regex filtering.
            poll_interval: How often to check for new content (seconds).
        """
        self._log_path = log_path
        self._active_levels = active_levels
        self._regex_state = regex_state
        self._poll_interval = poll_interval
        self._position = 0
        self._inode: int | None = None
        self._running = False
        self._queue: Queue[LogEntry] = Queue()
        self._stop_event = threading.Event()
        self._poll_thread: threading.Thread | None = None

    def _get_file_inode(self) -> int | None:
        """Get the inode of the log file for rotation detection."""
        try:
            return os.stat(self._log_path).st_ino
        except OSError:
            return None

    def _check_rotation(self) -> bool:
        """Check if the log file has been rotated.

        Returns:
            True if file was rotated, False otherwise.
        """
        current_inode = self._get_file_inode()
        if current_inode is None:
            return False

        # File was rotated if inode changed or file was truncated
        try:
            size = os.path.getsize(self._log_path)
            if current_inode != self._inode or size < self._position:
                self._inode = current_inode
                self._position = 0
                return True
        except OSError:
            pass

        return False

    def _read_new_lines(self) -> None:
        """Read new lines from the log file and queue them."""
        self._check_rotation()

        try:
            with open(self._log_path, encoding="utf-8", errors="replace") as f:
                f.seek(self._position)
                for line in f:
                    if line.strip():
                        entry = parse_log_line(line)
                        if self._should_show(entry):
                            self._queue.put(entry)
                self._position = f.tell()
        except OSError:
            pass

    def _should_show(self, entry: LogEntry) -> bool:
        """Check if a log entry should be displayed based on active levels and regex filters."""
        # Check level filter
        if self._active_levels is not None and entry.level not in self._active_levels:
            return False

        # Check regex filter (applied to raw line)
        return not (
            self._regex_state is not None
            and self._regex_state.has_filters()
            and not self._regex_state.should_show(entry.raw)
        )

    def _poll_loop(self) -> None:
        """Background thread that polls the file for changes."""
        while not self._stop_event.is_set():
            self._read_new_lines()
            time.sleep(self._poll_interval)

    def start(self) -> None:
        """Start tailing the log file.

        Seeks to the end of the file and begins monitoring for changes.
        """
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        # Initialize position to end of file
        try:
            self._position = os.path.getsize(self._log_path)
            self._inode = self._get_file_inode()
        except OSError:
            self._position = 0
            self._inode = None

        # Start polling thread
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        """Stop tailing the log file."""
        self._running = False
        self._stop_event.set()

        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

    def get_entry(self, timeout: float = 0.1) -> LogEntry | None:
        """Get the next log entry, if available.

        Args:
            timeout: Time to wait for an entry in seconds.

        Returns:
            LogEntry if available, None otherwise.
        """
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def update_levels(self, levels: set[LogLevel] | None) -> None:
        """Update the active log levels filter.

        Args:
            levels: New set of levels to display. None means all.
        """
        self._active_levels = levels

    def update_regex_state(self, regex_state: FilterState | None) -> None:
        """Update the regex filter state.

        Args:
            regex_state: New regex filter state. None means no regex filtering.
        """
        self._regex_state = regex_state

    @property
    def is_running(self) -> bool:
        """Check if the tailer is currently running."""
        return self._running


def tail_file(
    log_path: Path,
    active_levels: set[LogLevel] | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """Tail a log file and print entries with colors.

    Blocking function that runs until stop_event is set.

    Args:
        log_path: Path to the log file.
        active_levels: Set of log levels to display. None means all.
        stop_event: Event to signal when to stop tailing.
    """
    if stop_event is None:
        stop_event = threading.Event()

    tailer = LogTailer(log_path, active_levels)
    tailer.start()

    try:
        while not stop_event.is_set():
            entry = tailer.get_entry(timeout=0.1)
            if entry:
                print_log_entry(entry)
    finally:
        tailer.stop()
