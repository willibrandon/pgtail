"""Multi-file log tailer with timestamp interleaving.

Supports:
- Glob pattern expansion for --file
- Multiple explicit file paths
- Timestamp-ordered interleaving across files
- Dynamic file watching for new glob matches
"""

from __future__ import annotations

import fnmatch
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue

from pgtail_py.field_filter import FieldFilterState
from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat, detect_format
from pgtail_py.parser import LogEntry, parse_log_line
from pgtail_py.regex_filter import FilterState
from pgtail_py.time_filter import TimeFilter

# Default maximum buffer size for storing entries
DEFAULT_BUFFER_MAX_SIZE = 10000


@dataclass
class GlobPattern:
    """A glob pattern with its resolved directory and pattern."""

    directory: Path
    pattern: str
    original: str  # Original user-provided pattern

    @classmethod
    def from_path(cls, path_str: str) -> GlobPattern:
        """Create from a user-provided path string.

        Handles:
        - /path/to/*.log -> directory=/path/to, pattern=*.log
        - *.log -> directory=cwd, pattern=*.log
        - /path/to/specific.log -> directory=/path/to, pattern=specific.log

        Args:
            path_str: User-provided path or glob pattern.

        Returns:
            GlobPattern with resolved directory and pattern.
        """
        path = Path(path_str).expanduser()

        # Check if the path contains glob characters
        if any(c in str(path) for c in "*?["):
            # It's a glob pattern
            # Find the parent directory (up to first glob character)
            parts = path.parts
            directory_parts: list[str] = []
            pattern_parts: list[str] = []
            found_glob = False

            for part in parts:
                if found_glob or any(c in part for c in "*?["):
                    found_glob = True
                    pattern_parts.append(part)
                else:
                    directory_parts.append(part)

            if directory_parts:
                directory = Path(*directory_parts)
            else:
                directory = Path.cwd()

            pattern = str(Path(*pattern_parts)) if pattern_parts else "*"
        else:
            # It's a specific file path
            directory = path.parent
            pattern = path.name

        return cls(
            directory=directory.resolve(),
            pattern=pattern,
            original=path_str,
        )

    def expand(self) -> list[Path]:
        """Expand the glob pattern to matching file paths.

        Returns:
            List of matching file paths, sorted by modification time (newest first).
        """
        matches: list[Path] = []

        if not self.directory.exists():
            return matches

        # Simple single-level glob (e.g., *.log)
        if "/" not in self.pattern and "\\" not in self.pattern:
            for entry in self.directory.iterdir():
                if entry.is_file() and fnmatch.fnmatch(entry.name, self.pattern):
                    matches.append(entry)
        else:
            # Multi-level glob (e.g., **/*.log)
            matches = list(self.directory.glob(self.pattern))
            matches = [p for p in matches if p.is_file()]

        # Sort by modification time (newest first)
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        return matches


@dataclass
class FileTailerState:
    """State for a single file being tailed."""

    path: Path
    position: int = 0
    inode: int | None = None
    mtime: float | None = None
    last_size: int = 0
    detected_format: LogFormat | None = None
    unavailable_since: float | None = None


class MultiFileTailer:
    """Tail multiple log files with timestamp-ordered interleaving.

    Supports:
    - Multiple explicit file paths
    - Glob patterns that expand to multiple files
    - Dynamic discovery of new files matching glob patterns
    - Timestamp-based interleaving of entries across files
    """

    def __init__(
        self,
        paths: list[Path],
        glob_pattern: GlobPattern | None = None,
        active_levels: set[LogLevel] | None = None,
        regex_state: FilterState | None = None,
        time_filter: TimeFilter | None = None,
        field_filter: FieldFilterState | None = None,
        poll_interval: float = 0.1,
        on_entry: Callable[[LogEntry], None] | None = None,
        buffer_max_size: int = DEFAULT_BUFFER_MAX_SIZE,
    ) -> None:
        """Initialize the multi-file tailer.

        Args:
            paths: List of file paths to tail.
            glob_pattern: Optional glob pattern for dynamic file discovery.
            active_levels: Set of log levels to display. None means all.
            regex_state: Regex filter state. None means no regex filtering.
            time_filter: Time filter state. None means no time filtering.
            field_filter: Field filter state. None means no field filtering.
            poll_interval: How often to check for new content (seconds).
            on_entry: Callback for ALL parsed entries (before filtering).
            buffer_max_size: Maximum number of entries to store in buffer.
        """
        self._initial_paths = list(paths)
        self._glob_pattern = glob_pattern
        self._active_levels = active_levels
        self._regex_state = regex_state
        self._time_filter = time_filter
        self._field_filter = field_filter
        self._poll_interval = poll_interval
        self._on_entry = on_entry
        self._buffer_max_size = buffer_max_size

        # Per-file state
        self._file_states: dict[Path, FileTailerState] = {}

        # Output queue for timestamp-ordered entries
        self._queue: Queue[LogEntry] = Queue()

        # Buffer of all entries (for filtering replay)
        self._buffer: list[LogEntry] = []
        self._buffer_lock = threading.Lock()

        # Control
        self._running = False
        self._stop_event = threading.Event()
        self._poll_thread: threading.Thread | None = None

        # Format detection callback
        self._format_callback: Callable[[Path, LogFormat], None] | None = None

        # Track last glob scan time for rate limiting
        self._last_glob_scan: float = 0

    def _initialize_file_state(self, path: Path) -> FileTailerState | None:
        """Initialize state for a file.

        Args:
            path: Path to the file.

        Returns:
            FileTailerState or None if file doesn't exist.
        """
        try:
            stat_info = os.stat(path)
            return FileTailerState(
                path=path,
                position=0,
                inode=stat_info.st_ino,
                mtime=stat_info.st_mtime,
                last_size=stat_info.st_size,
            )
        except OSError:
            return None

    def _check_rotation(self, state: FileTailerState) -> bool:
        """Check if a file has been rotated.

        Args:
            state: File state to check.

        Returns:
            True if file was rotated, False otherwise.
        """
        try:
            stat_info = os.stat(state.path)
            current_inode = stat_info.st_ino
            current_mtime = stat_info.st_mtime
            size = stat_info.st_size
        except OSError:
            return False

        inode_changed = current_inode != state.inode
        file_truncated = size < state.position
        mtime_rotation = (
            state.mtime is not None
            and current_mtime != state.mtime
            and size == state.last_size
            and state.position >= size
            and size > 0
        )

        rotated = inode_changed or file_truncated or mtime_rotation

        if rotated:
            state.inode = current_inode
            state.mtime = current_mtime
            state.last_size = size
            state.position = 0
            state.detected_format = None
            return True

        state.mtime = current_mtime
        state.last_size = size
        return False

    def _read_file_entries(self, state: FileTailerState) -> list[LogEntry]:
        """Read new entries from a file.

        Args:
            state: File state to read from.

        Returns:
            List of new log entries.
        """
        entries: list[LogEntry] = []
        self._check_rotation(state)

        try:
            with open(state.path, encoding="utf-8", errors="replace") as f:
                f.seek(state.position)
                for line in f:
                    if line.strip():
                        # Detect format from first line
                        if state.detected_format is None:
                            state.detected_format = detect_format(line)
                            if self._format_callback:
                                self._format_callback(state.path, state.detected_format)

                        # Parse entry
                        entry = parse_log_line(line, state.detected_format or LogFormat.TEXT)

                        # Set source file for multi-file display
                        entry.source_file = state.path.name

                        # Call on_entry callback for ALL entries (before filtering)
                        if self._on_entry:
                            self._on_entry(entry)

                        # Check filters
                        if self._should_show(entry):
                            entries.append(entry)

                state.position = f.tell()

            # File is available - clear unavailability
            if state.unavailable_since is not None:
                state.unavailable_since = None

        except OSError:
            if state.unavailable_since is None:
                state.unavailable_since = time.time()

        return entries

    def _should_show(self, entry: LogEntry) -> bool:
        """Check if a log entry should be displayed based on filters.

        Args:
            entry: Log entry to check.

        Returns:
            True if entry passes all filters.
        """
        # Check time filter first
        if self._time_filter is not None and not self._time_filter.matches(entry):
            return False

        # Check level filter
        if self._active_levels is not None and entry.level not in self._active_levels:
            return False

        # Check field filter
        if self._field_filter is not None and not self._field_filter.matches(entry):
            return False

        # Check regex filter
        return not (
            self._regex_state is not None
            and self._regex_state.has_filters()
            and not self._regex_state.should_show(entry.raw)
        )

    def _check_for_new_files(self) -> None:
        """Check for new files matching the glob pattern.

        Rate-limited to check every 5 seconds.
        """
        if self._glob_pattern is None:
            return

        now = time.time()
        if now - self._last_glob_scan < 5.0:
            return
        self._last_glob_scan = now

        current_files = self._glob_pattern.expand()
        for path in current_files:
            if path not in self._file_states:
                state = self._initialize_file_state(path)
                if state:
                    # Start from beginning for newly discovered files
                    if self._time_filter and self._time_filter.is_active():
                        state.position = 0
                    else:
                        # Start from end for live tailing
                        state.position = state.last_size
                    self._file_states[path] = state

    def _poll_loop(self) -> None:
        """Background thread that polls all files for changes."""
        while not self._stop_event.is_set():
            # Check for new files matching glob
            self._check_for_new_files()

            # Collect entries from all files
            all_entries: list[LogEntry] = []
            for state in list(self._file_states.values()):
                entries = self._read_file_entries(state)
                all_entries.extend(entries)

            # Sort by timestamp for interleaving
            # Use secondary sort by source_file for consistent ordering
            all_entries.sort(
                key=lambda e: (
                    e.timestamp or e.timestamp,  # None timestamps go first
                    e.source_file or "",
                )
            )

            # Queue sorted entries
            for entry in all_entries:
                self._queue.put(entry)
                with self._buffer_lock:
                    self._buffer.append(entry)
                    # Trim buffer if needed
                    while len(self._buffer) > self._buffer_max_size:
                        self._buffer.pop(0)

            time.sleep(self._poll_interval)

    def start(self) -> None:
        """Start tailing all files."""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        # Initialize state for all initial paths
        for path in self._initial_paths:
            state = self._initialize_file_state(path)
            if state:
                # If time filter is active, start from beginning
                if self._time_filter and self._time_filter.is_active():
                    state.position = 0
                else:
                    # Otherwise start from end
                    state.position = state.last_size
                self._file_states[path] = state

        # Start polling thread
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self) -> None:
        """Stop tailing all files."""
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
            return self._queue.get_nowait()
        except Empty:
            time.sleep(timeout)
            try:
                return self._queue.get_nowait()
            except Empty:
                return None

    def get_buffer(self) -> list[LogEntry]:
        """Get all entries collected during tailing.

        Returns:
            List of log entries in chronological order.
        """
        with self._buffer_lock:
            return list(self._buffer)

    def clear_buffer(self) -> None:
        """Clear the buffer of collected entries."""
        with self._buffer_lock:
            self._buffer.clear()

    @property
    def is_running(self) -> bool:
        """Check if the tailer is currently running."""
        return self._running

    @property
    def file_count(self) -> int:
        """Get the number of files being tailed."""
        return len(self._file_states)

    @property
    def file_paths(self) -> list[Path]:
        """Get the list of file paths being tailed."""
        return list(self._file_states.keys())

    def set_format_callback(self, callback: Callable[[Path, LogFormat], None] | None) -> None:
        """Set a callback to be called when format is detected for each file.

        Args:
            callback: Function taking (Path, LogFormat) as arguments, or None to clear.
        """
        self._format_callback = callback

    def update_levels(self, levels: set[LogLevel] | None) -> None:
        """Update the active log levels filter."""
        self._active_levels = levels

    def update_regex_state(self, regex_state: FilterState | None) -> None:
        """Update the regex filter state."""
        self._regex_state = regex_state

    def update_time_filter(self, time_filter: TimeFilter | None) -> None:
        """Update the time filter."""
        self._time_filter = time_filter

    def update_field_filter(self, field_filter: FieldFilterState | None) -> None:
        """Update the field filter state."""
        self._field_filter = field_filter

    @property
    def files_unavailable(self) -> list[Path]:
        """Get list of files that are currently unavailable."""
        return [
            state.path
            for state in self._file_states.values()
            if state.unavailable_since is not None
        ]


def expand_glob_pattern(pattern: str) -> tuple[list[Path], str | None]:
    """Expand a glob pattern to matching file paths.

    Args:
        pattern: Glob pattern (e.g., "*.log", "/path/to/*.log")

    Returns:
        Tuple of (matching_paths, error_message).
        If error_message is not None, matching_paths will be empty.
    """
    glob = GlobPattern.from_path(pattern)
    matches = glob.expand()

    if not matches:
        return [], f"No files match pattern: {pattern}"

    return matches, None


def is_glob_pattern(path_str: str) -> bool:
    """Check if a path string contains glob characters.

    Args:
        path_str: Path string to check.

    Returns:
        True if the path contains glob characters.
    """
    return any(c in path_str for c in "*?[")
