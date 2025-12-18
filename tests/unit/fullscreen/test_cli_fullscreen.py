"""Unit tests for fullscreen CLI command."""

from unittest.mock import MagicMock, patch

import pytest


class TestFullscreenCommandErrors:
    """Tests for fullscreen_command error handling."""

    def test_error_when_buffer_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """fullscreen command shows error when buffer is empty."""
        from pgtail_py.cli import AppState
        from pgtail_py.cli_fullscreen import fullscreen_command

        # Create state with empty buffer
        with patch.object(AppState, "__post_init__", lambda self: None):
            state = AppState()
            state.fullscreen_buffer = None  # Will create empty buffer

        # Call fullscreen command
        fullscreen_command("", state)

        # Verify error message
        captured = capsys.readouterr()
        assert "No log content" in captured.out or "No log content" in captured.err

    def test_error_message_suggests_tail_command(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error message suggests using 'tail <id>' first."""
        from pgtail_py.cli import AppState
        from pgtail_py.cli_fullscreen import fullscreen_command

        with patch.object(AppState, "__post_init__", lambda self: None):
            state = AppState()
            state.fullscreen_buffer = None

        fullscreen_command("", state)

        captured = capsys.readouterr()
        output = captured.out + captured.err
        assert "tail" in output.lower()


class TestFullscreenCommandWithBufferContent:
    """Tests for fullscreen_command when buffer has content."""

    def test_calls_run_fullscreen_when_buffer_has_content(self) -> None:
        """fullscreen_command calls run_fullscreen when buffer has content."""
        from pgtail_py.cli import AppState
        from pgtail_py.cli_fullscreen import fullscreen_command
        from pgtail_py.fullscreen import LogBuffer

        with patch.object(AppState, "__post_init__", lambda self: None):
            state = AppState()
            state.fullscreen_buffer = LogBuffer()
            state.fullscreen_buffer.append("test log line")

        with patch("pgtail_py.cli_fullscreen.run_fullscreen") as mock_run:
            fullscreen_command("", state)
            mock_run.assert_called_once()

    def test_passes_buffer_and_state_to_run_fullscreen(self) -> None:
        """fullscreen_command passes buffer and state to run_fullscreen."""
        from pgtail_py.cli import AppState
        from pgtail_py.cli_fullscreen import fullscreen_command
        from pgtail_py.fullscreen import FullscreenState, LogBuffer

        with patch.object(AppState, "__post_init__", lambda self: None):
            state = AppState()
            state.fullscreen_buffer = LogBuffer()
            state.fullscreen_buffer.append("test log line")
            state.fullscreen_state = FullscreenState()

        with patch("pgtail_py.cli_fullscreen.run_fullscreen") as mock_run:
            fullscreen_command("", state)
            args = mock_run.call_args[0]
            assert isinstance(args[0], LogBuffer)
            assert isinstance(args[1], FullscreenState)

    def test_works_after_tail_stopped(self) -> None:
        """fullscreen works even after tail has been stopped (buffer preserved)."""
        from pgtail_py.cli import AppState
        from pgtail_py.cli_fullscreen import fullscreen_command
        from pgtail_py.fullscreen import LogBuffer

        with patch.object(AppState, "__post_init__", lambda self: None):
            state = AppState()
            state.tailing = False  # Tail stopped
            state.tailer = None
            state.fullscreen_buffer = LogBuffer()
            state.fullscreen_buffer.append("preserved log line")

        with patch("pgtail_py.cli_fullscreen.run_fullscreen") as mock_run:
            fullscreen_command("", state)
            mock_run.assert_called_once()  # Should still work!
