"""Circular buffer for storing formatted log lines."""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import FormattedText


# Type alias for a single line's styled content (list of style/text tuples)
StyledLine = list[tuple[str, str]]


class LogBuffer:
    """Circular buffer for storing formatted log lines with styling.

    Thread-safe for single-writer (tailer) / single-reader (UI) pattern.
    Uses collections.deque with maxlen for automatic FIFO eviction.

    Stores FormattedText (styled content) to preserve theme colors and
    SQL syntax highlighting when displayed in fullscreen TUI mode.
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
        self._lines: deque[StyledLine] = deque(maxlen=maxlen)
        self._maxlen = maxlen

    def append(self, line: FormattedText | str) -> None:
        """Add a formatted log line to the buffer.

        If buffer is at capacity, oldest line is automatically evicted.
        Thread-safe via GIL (single atomic append).

        Args:
            line: FormattedText with styling or plain string
        """
        if isinstance(line, str):
            # Plain string - wrap in empty style
            self._lines.append([("", line)])
        else:
            # FormattedText - convert to list of tuples
            self._lines.append(list(line))

    def get_formatted_text(self) -> list[tuple[str, str]]:
        """Get all lines as FormattedText tuples for styled display.

        Returns:
            List of (style, text) tuples with newlines between lines
        """
        result: list[tuple[str, str]] = []
        for i, line in enumerate(self._lines):
            if i > 0:
                result.append(("", "\n"))
            result.extend(line)
        return result

    def get_text(self) -> str:
        """Get all lines joined as plain text string.

        Returns:
            All lines joined with newlines (no styling)
        """
        plain_lines: list[str] = []
        for line in self._lines:
            plain_lines.append("".join(fragment[1] for fragment in line))
        return "\n".join(plain_lines)

    def get_lines(self) -> list[StyledLine]:
        """Get copy of all lines as list.

        Returns:
            List of styled lines in chronological order
        """
        return list(self._lines)

    def get_plain_lines(self) -> list[str]:
        """Get copy of all lines as plain text list.

        Returns:
            List of plain text lines in chronological order
        """
        return ["".join(fragment[1] for fragment in line) for line in self._lines]

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
