"""Stdin reader for piped log input.

Supports reading PostgreSQL logs from stdin, allowing usage like:
    cat log.gz | gunzip | pgtail tail --stdin
    zcat archived.log.gz | pgtail tail --stdin
"""

from __future__ import annotations

import sys
import threading
import time
from collections import deque
from collections.abc import Callable
from queue import Empty, Queue
from typing import TYPE_CHECKING, TextIO

from pgtail_py.field_filter import FieldFilterState
from pgtail_py.filter import LogLevel
from pgtail_py.format_detector import LogFormat, detect_format
from pgtail_py.parser import LogEntry, parse_log_line
from pgtail_py.regex_filter import FilterState
from pgtail_py.time_filter import TimeFilter

if TYPE_CHECKING:
    pass

# Default maximum buffer size for storing entries
DEFAULT_BUFFER_MAX_SIZE = 10000


class StdinReader:
    """Read log entries from stdin with filtering support.

    Designed for piped input like:
        cat log.gz | gunzip | pgtail tail --stdin

    Handles:
    - Non-blocking read from stdin
    - Format auto-detection from first line
    - All standard filters (level, regex, time, field)
    - EOF detection with graceful shutdown
    - Buffer of entries for filter replay

    The reader runs a background thread that reads lines from stdin
    and queues entries that pass the filters.
    """

    def __init__(
        self,
        active_levels: set[LogLevel] | None = None,
        regex_state: FilterState | None = None,
        time_filter: TimeFilter | None = None,
        field_filter: FieldFilterState | None = None,
        on_entry: Callable[[LogEntry], None] | None = None,
        on_eof: Callable[[], None] | None = None,
        buffer_max_size: int = DEFAULT_BUFFER_MAX_SIZE,
        stdin: TextIO | None = None,
    ) -> None:
        """Initialize the stdin reader.

        Args:
            active_levels: Set of log levels to display. None means all.
            regex_state: Regex filter state. None means no regex filtering.
            time_filter: Time filter state. None means no time filtering.
            field_filter: Field filter state. None means no field filtering.
            on_entry: Callback for ALL parsed entries (before filtering).
            on_eof: Callback when EOF is reached on stdin.
            buffer_max_size: Maximum number of entries to store in buffer.
            stdin: Optional stdin stream for testing. Defaults to sys.stdin.
        """
        self._active_levels = active_levels
        self._regex_state = regex_state
        self._time_filter = time_filter
        self._field_filter = field_filter
        self._on_entry = on_entry
        self._on_eof = on_eof
        self._stdin = stdin or sys.stdin

        self._running = False
        self._queue: Queue[LogEntry] = Queue()
        self._stop_event = threading.Event()
        self._read_thread: threading.Thread | None = None
        self._buffer: deque[LogEntry] = deque(maxlen=buffer_max_size)
        self._detected_format: LogFormat | None = None
        self._format_callback: Callable[[LogFormat], None] | None = None
        self._eof_reached = False
        self._lines_read = 0

    def _detect_format_if_needed(self, line: str) -> None:
        """Detect format from first non-empty line.

        Args:
            line: First line to use for format detection.
        """
        if self._detected_format is None:
            self._detected_format = detect_format(line)
            if self._format_callback:
                self._format_callback(self._detected_format)

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

    def _read_loop(self) -> None:
        """Background thread that reads lines from stdin."""
        try:
            for line in self._stdin:
                if self._stop_event.is_set():
                    break

                if not line.strip():
                    continue

                self._lines_read += 1

                # Detect format from first non-empty line
                self._detect_format_if_needed(line)

                # Parse entry with detected format
                entry = parse_log_line(line, self._detected_format or LogFormat.TEXT)

                # Mark source as stdin
                entry.source_file = "stdin"

                # Call on_entry callback for ALL entries (before filtering)
                if self._on_entry:
                    self._on_entry(entry)

                # Check filters and queue if passes
                if self._should_show(entry):
                    self._queue.put(entry)
                    self._buffer.append(entry)

        except OSError:
            # Stdin closed or error - treat as EOF
            pass
        finally:
            # Mark EOF reached
            self._eof_reached = True
            if self._on_eof:
                self._on_eof()

    def start(self) -> None:
        """Start reading from stdin.

        Spawns a background thread that reads lines from stdin
        and queues parsed entries.
        """
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        # Start reading thread
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def stop(self) -> None:
        """Stop reading from stdin."""
        self._running = False
        self._stop_event.set()

        if self._read_thread:
            # Give thread a short time to finish
            self._read_thread.join(timeout=0.5)
            self._read_thread = None

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
        """Get all entries collected during reading.

        Returns:
            List of log entries in chronological order.
        """
        return list(self._buffer)

    def clear_buffer(self) -> None:
        """Clear the buffer of collected entries."""
        self._buffer.clear()

    @property
    def is_running(self) -> bool:
        """Check if the reader is currently running."""
        return self._running

    @property
    def eof_reached(self) -> bool:
        """Check if EOF has been reached on stdin."""
        return self._eof_reached

    @property
    def lines_read(self) -> int:
        """Get the number of lines read from stdin."""
        return self._lines_read

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


def is_stdin_pipe() -> bool:
    """Check if stdin is a pipe (not a terminal).

    Returns:
        True if stdin is receiving piped input, False if interactive terminal.
    """
    return not sys.stdin.isatty()
