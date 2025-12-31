"""Tests for pgtail_py.tail_textual module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.instance import DetectionSource, Instance
from pgtail_py.tail_help import HelpScreen
from pgtail_py.tail_textual import TailApp

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_instance(tmp_path: Path) -> Instance:
    """Create a minimal Instance for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    log_file = tmp_path / "postgresql.log"
    log_file.write_text("")
    return Instance(
        id=0,
        version="16.0",
        data_dir=data_dir,
        log_path=log_file,
        log_directory=tmp_path,
        source=DetectionSource.PGRX,
        running=True,
        pid=12345,
        port=5432,
        logging_enabled=True,
    )


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a minimal mock AppState for testing."""
    state = MagicMock()
    state.active_levels = None
    state.regex_state = None
    state.time_filter = None
    state.field_filter = None
    state.slow_query_config = None
    state.error_stats = MagicMock()
    state.connection_stats = MagicMock()
    return state


class TestTailAppHelpOverlay:
    """Tests for help overlay functionality."""

    @pytest.mark.asyncio
    async def test_question_mark_shows_help_screen(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that pressing ? shows the help overlay."""
        log_file = tmp_path / "postgresql.log"
        log_file.write_text("")

        app = TailApp(
            state=mock_state,
            instance=mock_instance,
            log_path=log_file,
        )

        # Patch LogTailer to prevent actual file tailing
        with patch("pgtail_py.tail_textual.LogTailer") as mock_tailer_class:
            mock_tailer = MagicMock()
            mock_tailer.queue = MagicMock()
            mock_tailer.queue.get = MagicMock(side_effect=TimeoutError)
            mock_tailer_class.return_value = mock_tailer

            async with app.run_test() as pilot:
                # Verify no modal screen initially
                assert len(app.screen_stack) == 1

                # Focus the log widget (not input) so ? triggers app binding
                app.query_one("#log").focus()

                # Press ? to show help
                await pilot.press("?")

                # Verify HelpScreen was pushed
                assert len(app.screen_stack) == 2
                assert isinstance(app.screen_stack[-1], HelpScreen)

    @pytest.mark.asyncio
    async def test_help_screen_dismisses_with_escape(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that pressing Escape dismisses the help overlay."""
        log_file = tmp_path / "postgresql.log"
        log_file.write_text("")

        app = TailApp(
            state=mock_state,
            instance=mock_instance,
            log_path=log_file,
        )

        with patch("pgtail_py.tail_textual.LogTailer") as mock_tailer_class:
            mock_tailer = MagicMock()
            mock_tailer.queue = MagicMock()
            mock_tailer.queue.get = MagicMock(side_effect=TimeoutError)
            mock_tailer_class.return_value = mock_tailer

            async with app.run_test() as pilot:
                # Focus log widget so ? triggers app binding
                app.query_one("#log").focus()

                # Open help
                await pilot.press("?")
                assert len(app.screen_stack) == 2

                # Dismiss with Escape
                await pilot.press("escape")
                assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_help_screen_dismisses_with_q(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that pressing q dismisses the help overlay."""
        log_file = tmp_path / "postgresql.log"
        log_file.write_text("")

        app = TailApp(
            state=mock_state,
            instance=mock_instance,
            log_path=log_file,
        )

        with patch("pgtail_py.tail_textual.LogTailer") as mock_tailer_class:
            mock_tailer = MagicMock()
            mock_tailer.queue = MagicMock()
            mock_tailer.queue.get = MagicMock(side_effect=TimeoutError)
            mock_tailer_class.return_value = mock_tailer

            async with app.run_test() as pilot:
                # Focus log widget so ? triggers app binding
                app.query_one("#log").focus()

                # Open help
                await pilot.press("?")
                assert len(app.screen_stack) == 2

                # Dismiss with q
                await pilot.press("q")
                assert len(app.screen_stack) == 1

    @pytest.mark.asyncio
    async def test_help_screen_dismisses_with_question_mark(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that pressing ? again dismisses the help overlay."""
        log_file = tmp_path / "postgresql.log"
        log_file.write_text("")

        app = TailApp(
            state=mock_state,
            instance=mock_instance,
            log_path=log_file,
        )

        with patch("pgtail_py.tail_textual.LogTailer") as mock_tailer_class:
            mock_tailer = MagicMock()
            mock_tailer.queue = MagicMock()
            mock_tailer.queue.get = MagicMock(side_effect=TimeoutError)
            mock_tailer_class.return_value = mock_tailer

            async with app.run_test() as pilot:
                # Focus log widget so ? triggers app binding
                app.query_one("#log").focus()

                # Open help
                await pilot.press("?")
                assert len(app.screen_stack) == 2

                # Dismiss with ? again
                await pilot.press("?")
                assert len(app.screen_stack) == 1
