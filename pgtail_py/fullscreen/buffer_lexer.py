"""Custom lexer that uses pre-styled content from LogBuffer.

This lexer returns the exact same styling as streaming mode by reading
the FormattedText stored in the buffer, rather than re-parsing the text
with a different lexer.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.document import Document
from prompt_toolkit.lexers import Lexer

if TYPE_CHECKING:
    from pgtail_py.fullscreen.buffer import LogBuffer


class BufferLexer(Lexer):
    """Lexer that returns pre-styled content from LogBuffer.

    Instead of parsing text and applying new styles, this lexer returns
    the styles already stored in the buffer. This ensures fullscreen mode
    displays the exact same styling as streaming mode.
    """

    def __init__(self, buffer: LogBuffer) -> None:
        """Initialize with buffer reference.

        Args:
            buffer: LogBuffer containing pre-styled content
        """
        self._buffer = buffer

    def lex_document(self, document: Document) -> Callable[[int], list[tuple[str, str]]]:
        """Return a callable that provides styled tokens for each line.

        Args:
            document: The Document to lex (not used - we read from buffer)

        Returns:
            Callable that takes a line number and returns styled tokens
        """
        # Get current buffer lines (snapshot at lex time)
        lines = self._buffer.get_lines()

        def get_line_tokens(line_number: int) -> list[tuple[str, str]]:
            """Get styled tokens for a specific line.

            Args:
                line_number: Zero-based line number

            Returns:
                List of (style, text) tuples for the line
            """
            if 0 <= line_number < len(lines):
                return lines[line_number]
            return []

        return get_line_tokens

    def invalidation_hash(self) -> int:
        """Return hash for cache invalidation.

        We use the buffer length as a simple invalidation mechanism.
        When new lines are added, the hash changes.

        Returns:
            Hash value based on buffer length
        """
        return len(self._buffer)
