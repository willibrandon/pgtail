"""Unit tests for LogBuffer circular buffer."""

import pytest

from pgtail_py.fullscreen.buffer import LogBuffer


class TestLogBufferInit:
    """Tests for LogBuffer initialization."""

    def test_default_maxlen(self) -> None:
        """Buffer has default maxlen of 10000."""
        buf = LogBuffer()
        assert buf.maxlen == 10000

    def test_custom_maxlen(self) -> None:
        """Buffer accepts custom maxlen."""
        buf = LogBuffer(maxlen=100)
        assert buf.maxlen == 100

    def test_invalid_maxlen_zero(self) -> None:
        """Buffer raises ValueError for maxlen=0."""
        with pytest.raises(ValueError, match="maxlen must be positive"):
            LogBuffer(maxlen=0)

    def test_invalid_maxlen_negative(self) -> None:
        """Buffer raises ValueError for negative maxlen."""
        with pytest.raises(ValueError, match="maxlen must be positive"):
            LogBuffer(maxlen=-1)

    def test_empty_buffer_length(self) -> None:
        """Empty buffer has length 0."""
        buf = LogBuffer()
        assert len(buf) == 0


class TestLogBufferAppend:
    """Tests for LogBuffer.append() and FIFO eviction."""

    def test_append_single_line(self) -> None:
        """Appending a line increases buffer length."""
        buf = LogBuffer()
        buf.append("line1")
        assert len(buf) == 1

    def test_append_multiple_lines(self) -> None:
        """Appending multiple lines increases buffer length."""
        buf = LogBuffer()
        buf.append("line1")
        buf.append("line2")
        buf.append("line3")
        assert len(buf) == 3

    def test_fifo_eviction_at_capacity(self) -> None:
        """Oldest line is evicted when buffer is full."""
        buf = LogBuffer(maxlen=3)
        buf.append("line1")
        buf.append("line2")
        buf.append("line3")
        buf.append("line4")  # Should evict line1
        assert len(buf) == 3
        text = buf.get_text()
        assert "line1" not in text
        assert "line2" in text
        assert "line4" in text

    def test_fifo_eviction_preserves_order(self) -> None:
        """Eviction maintains chronological order."""
        buf = LogBuffer(maxlen=3)
        for i in range(5):
            buf.append(f"line{i}")
        lines = buf.get_plain_lines()
        assert lines == ["line2", "line3", "line4"]

    def test_append_empty_line(self) -> None:
        """Empty lines can be appended."""
        buf = LogBuffer()
        buf.append("")
        assert len(buf) == 1
        assert buf.get_text() == ""


class TestLogBufferGetText:
    """Tests for LogBuffer.get_text()."""

    def test_get_text_empty(self) -> None:
        """Empty buffer returns empty string."""
        buf = LogBuffer()
        assert buf.get_text() == ""

    def test_get_text_single_line(self) -> None:
        """Single line buffer returns that line."""
        buf = LogBuffer()
        buf.append("hello")
        assert buf.get_text() == "hello"

    def test_get_text_multiple_lines_joined(self) -> None:
        """Multiple lines are joined with newlines."""
        buf = LogBuffer()
        buf.append("a")
        buf.append("b")
        assert buf.get_text() == "a\nb"

    def test_get_text_preserves_content(self) -> None:
        """get_text() preserves original line content."""
        buf = LogBuffer()
        buf.append("line with spaces")
        buf.append("line\twith\ttabs")
        text = buf.get_text()
        assert "line with spaces" in text
        assert "line\twith\ttabs" in text


class TestLogBufferGetLines:
    """Tests for LogBuffer.get_lines() and get_plain_lines()."""

    def test_get_lines_empty(self) -> None:
        """Empty buffer returns empty list."""
        buf = LogBuffer()
        assert buf.get_lines() == []

    def test_get_lines_returns_copy(self) -> None:
        """get_lines() returns a copy, not the internal deque."""
        buf = LogBuffer()
        buf.append("line1")
        lines = buf.get_lines()
        lines.append([("", "line2")])  # Modify the copy
        assert len(buf) == 1  # Original unchanged

    def test_get_lines_order(self) -> None:
        """get_lines() returns styled lines in chronological order."""
        buf = LogBuffer()
        buf.append("first")
        buf.append("second")
        buf.append("third")
        # get_lines returns StyledLine (list of tuples)
        lines = buf.get_lines()
        assert len(lines) == 3
        # Each line is a list of (style, text) tuples
        assert lines[0] == [("", "first")]
        assert lines[1] == [("", "second")]
        assert lines[2] == [("", "third")]

    def test_get_plain_lines_order(self) -> None:
        """get_plain_lines() returns plain text in chronological order."""
        buf = LogBuffer()
        buf.append("first")
        buf.append("second")
        buf.append("third")
        assert buf.get_plain_lines() == ["first", "second", "third"]


class TestLogBufferClear:
    """Tests for LogBuffer.clear()."""

    def test_clear_empties_buffer(self) -> None:
        """clear() removes all lines."""
        buf = LogBuffer()
        buf.append("line1")
        buf.append("line2")
        buf.clear()
        assert len(buf) == 0
        assert buf.get_text() == ""

    def test_clear_preserves_maxlen(self) -> None:
        """clear() preserves maxlen setting."""
        buf = LogBuffer(maxlen=100)
        buf.append("line1")
        buf.clear()
        assert buf.maxlen == 100


class TestLogBufferNewlineSplitting:
    """Tests for newline splitting in append()."""

    def test_plain_string_with_newline_splits(self) -> None:
        """Plain string with newline is split into multiple lines."""
        buf = LogBuffer()
        buf.append("line1\nline2")
        assert len(buf) == 2
        assert buf.get_plain_lines() == ["line1", "line2"]

    def test_plain_string_multiple_newlines(self) -> None:
        """Multiple newlines create multiple lines."""
        buf = LogBuffer()
        buf.append("a\nb\nc")
        assert len(buf) == 3
        assert buf.get_plain_lines() == ["a", "b", "c"]

    def test_formatted_text_with_newline_splits(self) -> None:
        """FormattedText with newline is split preserving styles."""
        from prompt_toolkit.formatted_text import FormattedText

        buf = LogBuffer()
        buf.append(FormattedText([("class:a", "hello\nworld")]))
        assert len(buf) == 2
        lines = buf.get_lines()
        assert lines[0] == [("class:a", "hello")]
        assert lines[1] == [("class:a", "world")]

    def test_formatted_text_newline_in_middle(self) -> None:
        """Newline in middle of FormattedText splits correctly."""
        from prompt_toolkit.formatted_text import FormattedText

        buf = LogBuffer()
        buf.append(
            FormattedText([("class:a", "foo"), ("class:b", "bar\nbaz"), ("class:c", "qux")])
        )
        assert len(buf) == 2
        lines = buf.get_lines()
        # First line: "foo" + "bar"
        assert ("class:a", "foo") in lines[0]
        assert ("class:b", "bar") in lines[0]
        # Second line: "baz" + "qux"
        assert ("class:b", "baz") in lines[1]
        assert ("class:c", "qux") in lines[1]

    def test_get_text_after_split_matches_original(self) -> None:
        """get_text() after split should reconstruct original content."""
        buf = LogBuffer()
        buf.append("line1\nline2\nline3")
        # get_text joins with \n, so result should match original
        assert buf.get_text() == "line1\nline2\nline3"

    def test_trailing_newline_creates_empty_line(self) -> None:
        """Trailing newline creates an empty line."""
        buf = LogBuffer()
        buf.append("line1\n")
        assert len(buf) == 2
        assert buf.get_plain_lines() == ["line1", ""]
