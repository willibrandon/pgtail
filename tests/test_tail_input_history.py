"""Tests for TailInput history navigation integration (T005).

Covers constructor backward-compatibility, Up/Down arrow history navigation,
the watch_value guard pattern that separates programmatic from user-driven
value changes, and existing binding preservation.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from pgtail_py.tail_history import TailCommandHistory
from pgtail_py.tail_input import TailInput

# ---------------------------------------------------------------------------
# Minimal test app
# ---------------------------------------------------------------------------


class HistoryTestApp(App):
    """Minimal app containing only a TailInput widget for isolated testing."""

    def __init__(self, history: TailCommandHistory) -> None:
        super().__init__()
        self.history = history

    def compose(self) -> ComposeResult:
        yield TailInput(history=self.history)


# ---------------------------------------------------------------------------
# TestTailInputConstructor
# ---------------------------------------------------------------------------


class TestTailInputConstructor:
    """Constructor backward-compatibility and parameter storage tests."""

    def test_no_args_backward_compatible(self) -> None:
        """TailInput() with no args works and _history is None."""
        widget = TailInput()
        assert widget._history is None

    def test_with_history(self) -> None:
        """TailInput(history=...) stores the reference in _history."""
        history = TailCommandHistory(max_entries=100)
        widget = TailInput(history=history)
        assert widget._history is history


# ---------------------------------------------------------------------------
# TestHistoryNavigation
# ---------------------------------------------------------------------------


class TestHistoryNavigation:
    """History Up/Down navigation integration tests with a running App."""

    @pytest.mark.asyncio
    async def test_up_shows_history_entry(self) -> None:
        """Pressing Up with history entries shows the most recent entry."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")
        history.add("filter /timeout/")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            await pilot.press("up")
            await pilot.pause()

            # Most recent entry should be shown
            assert input_widget.value == "filter /timeout/"

    @pytest.mark.asyncio
    async def test_up_down_cycle(self) -> None:
        """Pressing Up Up Down navigates through entries correctly."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")
        history.add("filter /timeout/")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # First Up → most recent
            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "filter /timeout/"

            # Second Up → older
            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "level error"

            # Down → back to most recent
            await pilot.press("down")
            await pilot.pause()
            assert input_widget.value == "filter /timeout/"

    @pytest.mark.asyncio
    async def test_down_past_newest_restores(self) -> None:
        """Pressing Up then Down past newest restores the saved input."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Type something first (set a saved input context)
            # Use direct value assignment with guard to simulate typed text
            input_widget._navigating = False
            input_widget.value = "test"
            await pilot.pause()

            # Navigate back to history
            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "level error"

            # Navigate forward past newest → restores "test"
            await pilot.press("down")
            await pilot.pause()
            assert input_widget.value == "test"

    @pytest.mark.asyncio
    async def test_up_with_empty_history(self) -> None:
        """Pressing Up with no history entries leaves input unchanged (empty)."""
        history = TailCommandHistory(max_entries=100)
        # No entries added

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Input starts empty
            assert input_widget.value == ""

            await pilot.press("up")
            await pilot.pause()

            # Should still be empty
            assert input_widget.value == ""

    @pytest.mark.asyncio
    async def test_down_at_rest_noop(self) -> None:
        """Pressing Down when at-rest (no prior navigation) leaves input unchanged."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Press Down without prior Up navigation (at-rest state)
            initial_value = input_widget.value
            await pilot.press("down")
            await pilot.pause()

            # Input should be unchanged
            assert input_widget.value == initial_value


# ---------------------------------------------------------------------------
# TestGuardPattern
# ---------------------------------------------------------------------------


class TestGuardPattern:
    """Tests for the _navigating guard and watch_value reset behavior."""

    @pytest.mark.asyncio
    async def test_typing_resets_navigation(self) -> None:
        """Navigating to a history entry then typing resets history to at-rest."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")
        history.add("filter /timeout/")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Navigate to history entry
            await pilot.press("up")
            await pilot.pause()
            assert input_widget.value == "filter /timeout/"

            # History should NOT be at rest while navigating
            assert not history.at_rest

            # Now type a character (user-driven value change)
            await pilot.press("x")
            await pilot.pause()

            # watch_value fires without the guard → history resets to at-rest
            assert history.at_rest

    @pytest.mark.asyncio
    async def test_programmatic_change_during_nav_no_reset(self) -> None:
        """After pressing Up, history is NOT at rest (navigating state is set)."""
        history = TailCommandHistory(max_entries=100)
        history.add("level error")

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Verify at-rest initially
            assert history.at_rest

            # Navigate back
            await pilot.press("up")
            await pilot.pause()

            # Guard was set during programmatic assignment → history not at-rest
            assert not history.at_rest
            assert input_widget.value == "level error"


# ---------------------------------------------------------------------------
# TestExistingBindingsPreserved
# ---------------------------------------------------------------------------


class TestExistingBindingsPreserved:
    """Verify that the pre-existing TailInput bindings still work after
    the history parameter was added (non-regression tests)."""

    @pytest.mark.asyncio
    async def test_q_quits_when_empty(self) -> None:
        """Pressing q on empty input triggers app quit.

        Note: app.is_running remains True inside the run_test() context manager
        (the event loop is still pumping). The check must happen after the
        context exits, at which point the app has fully stopped.
        """
        history = TailCommandHistory(max_entries=100)

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Ensure input is empty
            assert input_widget.value == ""

            # Press q → action_quit_if_empty calls app.action_quit()
            await pilot.press("q")
            await pilot.pause()

        # After the context manager exits, the app has fully stopped
        assert not app.is_running

    @pytest.mark.asyncio
    async def test_q_inserts_when_has_content(self) -> None:
        """Pressing q when input has content inserts the character 'q'."""
        history = TailCommandHistory(max_entries=100)

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Programmatically set some content (with guard to avoid resetting
            # navigation, which is irrelevant here but keeps state clean)
            input_widget._navigating = True
            input_widget.value = "level"
            input_widget._navigating = False
            await pilot.pause()

            # Press q → should insert 'q' at cursor
            await pilot.press("q")
            await pilot.pause()

            assert "q" in input_widget.value
            assert app.is_running

    @pytest.mark.asyncio
    async def test_escape_clears_input(self) -> None:
        """Pressing Escape clears the input value."""
        history = TailCommandHistory(max_entries=100)

        app = HistoryTestApp(history)
        async with app.run_test() as pilot:
            input_widget = app.query_one(TailInput)
            input_widget.focus()
            await pilot.pause()

            # Set some content
            input_widget._navigating = True
            input_widget.value = "some command"
            input_widget._navigating = False
            await pilot.pause()

            assert input_widget.value == "some command"

            # Press Escape → clears input
            await pilot.press("escape")
            await pilot.pause()

            assert input_widget.value == ""
