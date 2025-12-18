"""Circular buffer for storing formatted log lines."""

from collections import deque


class LogBuffer:
    """Circular buffer for storing formatted log lines.

    Thread-safe for single-writer (tailer) / single-reader (UI) pattern.
    Uses collections.deque with maxlen for automatic FIFO eviction.
    """

    def __init__(self, maxlen: int = 10000) -> None:
        """Initialize buffer with maximum line capacity.

        Args:
            maxlen: Maximum number of lines to retain (default 10000)

        Raises:
            ValueError: If maxlen <= 0
        """
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self._lines: deque[str] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def append(self, line: str) -> None:
        """Add a formatted log line to the buffer.

        If buffer is at capacity, oldest line is automatically evicted.
        Thread-safe via GIL (single atomic append).

        Args:
            line: Formatted log line (should not contain newline)
        """
        self._lines.append(line)

    def get_text(self) -> str:
        """Get all lines joined as single string for TextArea.

        Returns:
            All lines joined with newlines
        """
        return "\n".join(self._lines)

    def get_lines(self) -> list[str]:
        """Get copy of all lines as list.

        Returns:
            List of lines in chronological order
        """
        return list(self._lines)

    def clear(self) -> None:
        """Remove all lines from buffer."""
        self._lines.clear()

    def __len__(self) -> int:
        """Return current number of lines in buffer."""
        return len(self._lines)

    @property
    def maxlen(self) -> int:
        """Maximum buffer capacity."""
        return self._maxlen
