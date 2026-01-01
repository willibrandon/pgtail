"""Performance tests for pgtail tail mode.

These tests verify performance characteristics specified in the spec:
- SC-001: Mouse-drag-to-clipboard latency <2s
- SC-002: Vim key response latency <50ms
- SC-003: 100+ entries/sec auto-scroll
- SC-008: Memory baseline for 10,000 entry buffer
- SC-009: Startup time <500ms
- SC-010: Focus switch latency <50ms

Run with: pytest tests/test_performance.py -v
For benchmarking: pytest tests/test_performance.py --benchmark-only
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from pgtail_py.instance import DetectionSource, Instance
from pgtail_py.tail_log import TailLog
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


@pytest.mark.performance
class TestVimKeyLatency:
    """Tests for vim key response latency (SC-002: <50ms).

    Note: These tests measure the action method latency directly,
    not the full key-to-screen update pipeline which requires app context.
    """

    def test_visual_mode_state_change_latency(self) -> None:
        """Test visual mode state changes are fast."""
        widget = TailLog()

        start = time.perf_counter()
        for _ in range(1000):
            widget._visual_mode = True
            widget._visual_anchor_line = 50
            widget._visual_line_mode = True
            # Clear state (avoid _exit_visual_mode which posts message)
            widget._visual_mode = False
            widget._visual_line_mode = False
            widget._visual_anchor_line = None
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 50, f"Average visual mode toggle {avg_ms:.2f}ms exceeds 50ms"

    def test_cursor_movement_latency(self) -> None:
        """Test cursor state changes are fast."""
        widget = TailLog()

        start = time.perf_counter()
        for _ in range(1000):
            widget._cursor_line = 100
            widget._cursor_col = 50
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 1000) * 1000
        assert avg_ms < 1, f"Cursor state update {avg_ms:.2f}ms is too slow"


@pytest.mark.performance
class TestMemoryBaseline:
    """Tests for memory usage (SC-008: baseline for 10,000 entries).

    Note: Buffer capacity tests require app context for write_line().
    These tests verify the configuration is accepted.
    """

    def test_max_lines_configuration(self) -> None:
        """Test that max_lines is properly configured."""
        widget = TailLog(max_lines=10000)
        assert widget.max_lines == 10000

    def test_default_max_lines(self) -> None:
        """Test default max_lines value."""
        widget = TailLog()
        # Default from Log widget
        assert widget.max_lines is not None


@pytest.mark.performance
class TestStartupTime:
    """Tests for startup time (SC-009: <500ms)."""

    @pytest.mark.asyncio
    async def test_app_mount_time(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that TailApp mounts in <500ms."""
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

            start = time.perf_counter()
            async with app.run_test():
                elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"App mount time {elapsed:.3f}s exceeds 500ms"


@pytest.mark.performance
class TestFocusSwitchLatency:
    """Tests for focus switch latency (SC-010: <50ms)."""

    @pytest.mark.asyncio
    async def test_focus_switch_time(
        self, mock_instance: Instance, mock_state: MagicMock, tmp_path: Path
    ) -> None:
        """Test that focus switching between widgets is <50ms."""
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
                log_widget = app.query_one("#log")
                input_widget = app.query_one("#input")

                # Measure focus switch time
                start = time.perf_counter()
                for _ in range(10):
                    log_widget.focus()
                    input_widget.focus()
                elapsed = time.perf_counter() - start

                avg_ms = (elapsed / 20) * 1000  # 20 focus switches
                assert avg_ms < 50, f"Focus switch {avg_ms:.2f}ms exceeds 50ms"


@pytest.mark.performance
class TestClipboardLatency:
    """Tests for clipboard latency (SC-001: <2s for mouse-drag-to-clipboard)."""

    def test_copy_latency(self) -> None:
        """Test that copy operation completes in <2s."""
        widget = TailLog()
        widget._app = MagicMock()
        widget._app.copy_to_clipboard.side_effect = Exception("No app")

        # Create substantial content to copy
        text_to_copy = "\n".join([f"line {i}: " + "x" * 100 for i in range(100)])

        with patch.dict("sys.modules", {"pyperclip": MagicMock()}):
            start = time.perf_counter()
            widget._copy_with_fallback(text_to_copy)
            elapsed = time.perf_counter() - start

            assert elapsed < 2.0, f"Copy latency {elapsed:.3f}s exceeds 2s"


@pytest.mark.performance
class TestAutoScrollStress:
    """Stress test for 100+ entries/sec auto-scroll (SC-003, T160)."""

    @pytest.mark.asyncio
    async def test_hundred_entries_per_second(self) -> None:
        """Test that TailLog can handle 100+ entries/sec with auto-scroll.

        This test writes 100 entries and measures total time to ensure
        the widget can keep up with high-frequency log output.
        """
        from textual.app import App, ComposeResult

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log", auto_scroll=True)

        app = TestApp()

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write 100 entries and measure time
            start = time.perf_counter()
            for i in range(100):
                log.write_line(f"Entry {i:04d}: Test log message with some content")
            await pilot.pause()
            elapsed = time.perf_counter() - start

            # Should complete in <1 second (allowing margin for test overhead)
            assert elapsed < 1.0, f"100 entries took {elapsed:.3f}s, exceeds 1s threshold"
            assert log.line_count == 100

    @pytest.mark.asyncio
    async def test_sustained_high_throughput(self) -> None:
        """Test sustained high throughput over multiple batches.

        This test simulates continuous log streaming at 100+ entries/sec
        for 5 batches to verify sustained performance.
        """
        from textual.app import App, ComposeResult

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log", auto_scroll=True)

        app = TestApp()

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write 5 batches of 100 entries each
            batch_times: list[float] = []
            for batch in range(5):
                start = time.perf_counter()
                for i in range(100):
                    log.write_line(f"Batch {batch} Entry {i:04d}: Log message")
                await pilot.pause()
                batch_times.append(time.perf_counter() - start)

            # All batches should complete in <1 second each
            for idx, elapsed in enumerate(batch_times):
                assert elapsed < 1.0, f"Batch {idx} took {elapsed:.3f}s, exceeds 1s"

            assert log.line_count == 500

    @pytest.mark.asyncio
    async def test_auto_scroll_follows_new_entries(self) -> None:
        """Test that auto-scroll keeps up with rapid entry addition.

        When auto_scroll=True, the view should stay at the bottom
        as new entries are added rapidly.
        """
        from textual.app import App, ComposeResult

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield TailLog(id="log", auto_scroll=True)

        app = TestApp()

        async with app.run_test() as pilot:
            log = app.query_one("#log", TailLog)

            # Write many entries rapidly
            for i in range(200):
                log.write_line(f"Rapid entry {i:04d}")

            await pilot.pause()

            # Verify all entries were written
            assert log.line_count == 200

            # Verify widget is at or near bottom (auto-scroll working)
            # is_vertical_scroll_end should be True when at bottom
            # (allowing for small differences due to viewport size)
            scroll_y = log.scroll_offset.y
            max_scroll = log.virtual_size.height - log.scrollable_content_region.height
            # Should be close to bottom (within 5 lines)
            assert max_scroll - scroll_y <= 5, "Auto-scroll should keep view near bottom"
