"""Log file tailing with polling."""

from __future__ import annotations

import os
import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from queue import Empty, Queue

# Windows st_ino is unreliable - can return different values for same file
IS_WINDOWS = sys.platform == "win32"

from pgtail_py.colors import print_log_entry
from pgtail_py.detector import find_latest_log, read_current_logfiles
from pgtail_py.field_filter import FieldFilterState
from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat, detect_format
from pgtail_py.parser import LogEntry, parse_log_line
from pgtail_py.regex_filter import FilterState
from pgtail_py.time_filter import TimeFilter

# Default maximum buffer size for storing entries
DEFAULT_BUFFER_MAX_SIZE = 10000


class LogTailer:
    """Tail a PostgreSQL log file with real-time updates.

    Uses simple polling for reliable cross-platform file monitoring.
    Handles log rotation by detecting file truncation or recreation.

    Resilient to PostgreSQL restarts: automatically detects when a new log
    file is created and switches to it seamlessly.
    """

    def __init__(
        self,
        log_path: Path,
        active_levels: set[LogLevel] | None = None,
        regex_state: FilterState | None = None,
        time_filter: TimeFilter | None = None,
        field_filter: FieldFilterState | None = None,
        poll_interval: float = 0.1,
        on_entry: Callable[[LogEntry], None] | None = None,
        data_dir: Path | None = None,
        log_directory: Path | None = None,
        on_file_change: Callable[[Path], None] | None = None,
        buffer_max_size: int = DEFAULT_BUFFER_MAX_SIZE,
    ) -> None:
        """Initialize the log tailer.

        Args:
            log_path: Path to the log file to tail.
            active_levels: Set of log levels to display. None means all.
            regex_state: Regex filter state. None means no regex filtering.
            time_filter: Time filter state. None means no time filtering.
            field_filter: Field filter state. None means no field filtering.
            poll_interval: How often to check for new content (seconds).
            on_entry: Callback for ALL parsed entries (before filtering).
            data_dir: PostgreSQL data directory for reading current_logfiles.
            log_directory: Directory containing log files for fallback detection.
            on_file_change: Callback when switching to a new log file.
            buffer_max_size: Maximum number of entries to store in buffer.
                Oldest entries are discarded when limit is reached. Default 10000.
        """
        self._log_path = log_path
        self._active_levels = active_levels
        self._regex_state = regex_state
        self._time_filter = time_filter
        self._field_filter = field_filter
        self._poll_interval = poll_interval
        self._position = 0
        self._inode: int | None = None
        self._mtime: float | None = None  # Track modification time for rotation detection
        self._last_size: int = 0  # Track file size for rotation detection
        self._running = False
        self._queue: Queue[LogEntry] = Queue()
        self._stop_event = threading.Event()
        self._poll_thread: threading.Thread | None = None
        self._buffer: deque[LogEntry] = deque(maxlen=buffer_max_size)
        self._detected_format: LogFormat | None = None
        self._format_callback: Callable[[LogFormat], None] | None = None
        self._on_entry = on_entry

        # Resilience: detect new log files after restart/rotation
        self._data_dir = data_dir
        self._log_directory = log_directory
        self._on_file_change = on_file_change
        self._file_unavailable_since: float | None = None
        self._last_directory_scan: float = 0

    def _get_file_inode(self) -> int | None:
        """Get the inode of the log file for rotation detection."""
        try:
            return os.stat(self._log_path).st_ino
        except OSError:
            return None

    def _check_rotation(self) -> bool:
        """Check if the log file has been rotated.

        Detects rotation via:
        - Inode change (file replaced)
        - File truncation (size < position)
        - Modification time change with SAME size at EOF (file recreated with same inode)

        The mtime check handles Linux inode reuse, where a deleted file's inode
        may be immediately reused for a new file at the same path.

        Returns:
            True if file was rotated, False otherwise.
        """
        try:
            stat_info = os.stat(self._log_path)
            current_inode = stat_info.st_ino
            current_mtime = stat_info.st_mtime
            size = stat_info.st_size
        except OSError:
            return False

        # File was rotated if:
        # 1. Inode changed (obvious replacement) - SKIP on Windows where st_ino is unreliable
        # 2. File truncated (size < our position)
        # 3. Size unchanged but mtime changed while we're at EOF (inode reuse case) - SKIP on Windows
        #
        # On Windows:
        # - st_ino can return different values for the same file
        # - Reading a file can update mtime, causing false mtime_rotation triggers
        # So on Windows, we only use file_truncated for rotation detection.
        inode_changed = False if IS_WINDOWS else (current_inode != self._inode)
        file_truncated = size < self._position
        # Same inode, same size, but mtime changed and we're at EOF
        # This catches Linux inode reuse after delete+recreate with same-size content
        # SKIP on Windows: reading files can update mtime, causing infinite re-read loops
        mtime_rotation = False if IS_WINDOWS else (
            self._mtime is not None
            and current_mtime != self._mtime
            and size == self._last_size  # Size must be same (not just growing)
            and self._position >= size  # We must be at EOF
            and size > 0  # File must have content
        )
        rotated = inode_changed or file_truncated or mtime_rotation

        if rotated:
            self._inode = current_inode
            self._mtime = current_mtime
            self._last_size = size
            self._position = 0
            # Reset format detection on rotation - new file may have different format
            self._detected_format = None
            return True

        # Update tracking for next check
        self._mtime = current_mtime
        self._last_size = size
        return False

    def _check_for_new_log_file(self) -> bool:
        """Check if a new log file should be tailed (after restart/rotation).

        Uses PostgreSQL's current_logfiles (most reliable) or falls back to
        finding the latest log file by modification time.

        Returns:
            True if switched to a new file, False otherwise.
        """
        # Rate limit directory scans to every 1 second
        now = time.time()
        if now - self._last_directory_scan < 1.0:
            return False
        self._last_directory_scan = now

        # Try current_logfiles first (PostgreSQL 10+, most reliable)
        if self._data_dir:
            new_path = read_current_logfiles(self._data_dir)
            if new_path and new_path.exists() and new_path.resolve() != self._log_path.resolve():
                self._switch_to_file(new_path)
                return True

        # Fall back to finding latest log file by mtime
        # Only switch to files with the same extension to avoid flip-flopping
        # between .log and .csv when both exist (PostgreSQL logging to both)
        if self._log_directory:
            new_path = find_latest_log(self._log_directory)
            if new_path and new_path.resolve() != self._log_path.resolve():
                # Only switch if same extension (e.g., .log -> .log, not .log -> .csv)
                if new_path.suffix == self._log_path.suffix:
                    self._switch_to_file(new_path)
                    return True

        return False

    def _switch_to_file(self, new_path: Path) -> None:
        """Switch to tailing a new log file.

        Args:
            new_path: Path to the new log file.
        """
        self._log_path = new_path
        self._position = 0
        try:
            stat_info = os.stat(new_path)
            self._inode = stat_info.st_ino
            self._mtime = stat_info.st_mtime
            self._last_size = stat_info.st_size
        except OSError:
            self._inode = None
            self._mtime = None
            self._last_size = 0
        self._detected_format = None
        self._file_unavailable_since = None

        # Notify caller about the file change
        if self._on_file_change:
            self._on_file_change(new_path)

    def _detect_format_if_needed(self, line: str) -> None:
        """Detect format from first non-empty line.

        Args:
            line: First line to use for format detection
        """
        if self._detected_format is None:
            self._detected_format = detect_format(line)
            if self._format_callback:
                self._format_callback(self._detected_format)

    def _read_new_lines(self) -> None:
        """Read new lines from the log file and queue them.

        Handles file unavailability (e.g., during PostgreSQL restart) by
        checking for new log files and switching to them automatically.
        Also proactively checks for new log files when at EOF.
        """
        self._check_rotation()

        try:
            with open(self._log_path, encoding="utf-8", errors="replace") as f:
                f.seek(self._position)
                lines_read = 0
                for line in f:
                    if line.strip():
                        lines_read += 1
                        # Detect format on first non-empty line
                        self._detect_format_if_needed(line)
                        # Parse with detected format
                        entry = parse_log_line(line, self._detected_format or LogFormat.TEXT)
                        # Call on_entry callback for ALL entries (before filtering)
                        if self._on_entry:
                            self._on_entry(entry)
                        if self._should_show(entry):
                            self._queue.put(entry)
                            self._buffer.append(entry)
                self._position = f.tell()

            # File is available - clear unavailability tracking
            if self._file_unavailable_since is not None:
                self._file_unavailable_since = None

            # Proactively check for new log file when at EOF (no new lines)
            # This handles the case where PostgreSQL restarts and creates a new
            # log file while the old one still exists
            if lines_read == 0:
                self._check_for_new_log_file()

        except OSError:
            # File unavailable - try to find a new log file
            if self._file_unavailable_since is None:
                self._file_unavailable_since = time.time()

            # Check for new log file (e.g., after PostgreSQL restart)
            if self._check_for_new_log_file():
                return  # Found new file, will read on next poll

    def _should_show(self, entry: LogEntry) -> bool:
        """Check if a log entry should be displayed based on filters.

        Filter order (cheapest first):
        1. Time filter - datetime comparison is O(1)
        2. Level filter - set membership is O(1)
        3. Field filter - string equality is O(1)
        4. Regex filter - regex match is O(n) where n = line length
        """
        # Check time filter first (cheapest comparison)
        if self._time_filter is not None and not self._time_filter.matches(entry):
            return False

        # Check level filter
        if self._active_levels is not None and entry.level not in self._active_levels:
            return False

        # Check field filter
        if self._field_filter is not None and not self._field_filter.matches(entry):
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

        If a time filter is active, reads from the beginning to show
        historical entries first. Otherwise, seeks to the end.

        Empty files are handled gracefully (T055): tail mode enters normally
        and waits for content to appear. The polling loop continues checking
        for new content until stop() is called.
        """
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        # If time filter is active, start from beginning to show historical entries
        # Otherwise, start from end (only new entries)
        try:
            stat_info = os.stat(self._log_path)
            if self._time_filter is not None and self._time_filter.is_active():
                self._position = 0
            else:
                self._position = stat_info.st_size
            self._inode = stat_info.st_ino
            self._mtime = stat_info.st_mtime
            self._last_size = stat_info.st_size
        except OSError:
            self._position = 0
            self._inode = None
            self._mtime = None
            self._last_size = 0

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

        Uses non-blocking gets with short sleeps to be responsive to Ctrl+C.

        Args:
            timeout: Time to wait for an entry in seconds.

        Returns:
            LogEntry if available, None otherwise.
        """
        # Use non-blocking get to be responsive to KeyboardInterrupt
        try:
            return self._queue.get_nowait()
        except Empty:
            # No entry immediately available, sleep briefly
            # Short sleep allows Ctrl+C to be processed
            time.sleep(timeout)
            try:
                return self._queue.get_nowait()
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

    def update_time_filter(self, time_filter: TimeFilter | None) -> None:
        """Update the time filter.

        Args:
            time_filter: New time filter. None means no time filtering.
        """
        self._time_filter = time_filter

    def update_field_filter(self, field_filter: FieldFilterState | None) -> None:
        """Update the field filter state.

        Args:
            field_filter: New field filter state. None means no field filtering.
        """
        self._field_filter = field_filter

    @property
    def is_running(self) -> bool:
        """Check if the tailer is currently running."""
        return self._running

    @property
    def log_path(self) -> Path:
        """Get the current log file path being tailed."""
        return self._log_path

    @property
    def format(self) -> LogFormat:
        """Get detected format. Returns TEXT if not yet detected."""
        return self._detected_format or LogFormat.TEXT

    def set_format_callback(self, callback: Callable[[LogFormat], None] | None) -> None:
        """Set a callback to be called when format is detected.

        Args:
            callback: Function taking LogFormat as argument, or None to clear.
        """
        self._format_callback = callback

    def get_buffer(self) -> list[LogEntry]:
        """Get all entries collected during tailing.

        Returns:
            List of log entries in chronological order.
            Note: Buffer has a maximum size (default 10000). Older entries
            are discarded when the limit is reached.
        """
        return list(self._buffer)

    def clear_buffer(self) -> None:
        """Clear the buffer of collected entries."""
        self._buffer.clear()

    @property
    def buffer_size(self) -> int:
        """Get the current number of entries in the buffer."""
        return len(self._buffer)

    @property
    def buffer_max_size(self) -> int | None:
        """Get the maximum buffer size. None means unlimited."""
        return self._buffer.maxlen

    @property
    def file_unavailable(self) -> bool:
        """Check if the log file is currently unavailable.

        Returns True when the file has been deleted or is inaccessible.
        The tailer continues polling and will resume when the file returns.
        """
        return self._file_unavailable_since is not None


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
