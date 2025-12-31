"""Textual-based tail mode application for pgtail.

This module provides the TailApp Textual Application that replaces the
prompt_toolkit-based tail mode UI with Textual for built-in text selection
and clipboard support. The Log widget provides native mouse selection via
ALLOW_SELECT = True, OSC 52 clipboard integration, and Rich text styling.

Classes:
    TailApp: Main Textual Application for tail mode with selection support.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Input, Static

from pgtail_py.tail_log import TailLog
from pgtail_py.tail_rich import format_entry_compact
from pgtail_py.tail_status import TailStatus
from pgtail_py.tailer import LogTailer

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance
    from pgtail_py.parser import LogEntry


class TailApp(App[None]):
    """Textual-based tail mode with selection support.

    Main Textual Application that coordinates log display, command input,
    status bar, and log streaming from the existing LogTailer. Replaces
    the prompt_toolkit-based tail mode for built-in text selection.

    Attributes:
        _state: pgtail AppState with filter settings.
        _instance: PostgreSQL instance being tailed.
        _log_path: Path to the log file.
        _max_lines: Maximum lines to buffer (default 10,000).
        _tailer: LogTailer for background log streaming.
        _status: TailStatus for status bar state.
        _running: Application running flag.
    """

    ALLOW_SELECT: ClassVar[bool] = True

    CSS: ClassVar[str] = """
    /* Log area with themed scrollbars */
    TailLog {
        height: 1fr;
        scrollbar-size-vertical: 1;
        scrollbar-size-horizontal: 0;
        scrollbar-background: $surface;
        scrollbar-color: $text-muted;
        scrollbar-color-hover: $text;
        scrollbar-color-active: $primary;
    }

    /* Separator line between log and input */
    .separator {
        height: 1;
        color: $text-muted;
    }

    /* Command input area */
    #input {
        height: 1;
        border: none;
        background: $surface;
    }

    /* Status bar - distinct panel background for visibility */
    #status {
        height: 1;
        width: 100%;
        background: $panel;
        color: $text;
        text-style: bold;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "focus_input", "Command", show=False),
        Binding("tab", "toggle_focus", "Toggle focus", show=False),
    ]

    def __init__(
        self,
        state: AppState,
        instance: Instance,
        log_path: Path,
        max_lines: int = 10000,
    ) -> None:
        """Initialize TailApp.

        Args:
            state: pgtail AppState with filter settings.
            instance: PostgreSQL instance being tailed.
            log_path: Path to the log file.
            max_lines: Maximum lines to buffer (default 10,000).
        """
        super().__init__()
        self._state: AppState = state
        self._instance: Instance = instance
        self._log_path: Path = log_path
        self._max_lines: int = max_lines
        self._tailer: LogTailer | None = None
        self._status: TailStatus | None = None
        self._running: bool = False

    @classmethod
    def run_tail_mode(
        cls,
        state: AppState,
        instance: Instance,
        log_path: Path,
    ) -> None:
        """Run tail mode (blocking).

        This is the main entry point called from cli.py.

        Args:
            state: pgtail AppState with filter settings.
            instance: PostgreSQL instance being tailed.
            log_path: Path to the log file.
        """
        app = cls(state=state, instance=instance, log_path=log_path)
        app.run()

    def compose(self) -> ComposeResult:
        """Compose the application layout.

        Layout (top to bottom):
        - TailLog: Log display area (flexible height)
        - Static: Separator line above input
        - Input: Command input line (tail> prompt)
        - Static: Separator line below input
        - Static: Status bar (bottom, with reverse video styling)

        Yields:
            Widgets in layout order.
        """
        yield TailLog(max_lines=self._max_lines, auto_scroll=True, id="log")
        yield Static("─" * 200, classes="separator")
        yield Input(placeholder="tail> ", id="input")
        yield Static("─" * 200, classes="separator")
        yield Static(id="status")

    def on_mount(self) -> None:
        """Called when app is mounted.

        Initializes the status bar, creates the LogTailer, and starts
        the background consumer worker.
        """
        # Initialize status
        self._status = TailStatus()
        self._status.set_instance_info(
            version=self._instance.version or "",
            port=self._instance.port or 5432,
        )

        # Set initial filter state from AppState
        if self._state.active_levels is not None:
            self._status.set_level_filter(self._state.active_levels)

        if self._state.regex_state and self._state.regex_state.has_filters():
            patterns = [f.pattern for f in self._state.regex_state.includes]
            if patterns:
                self._status.set_regex_filter(patterns[0])

        if self._state.time_filter and self._state.time_filter.is_active():
            self._status.set_time_filter(self._state.time_filter.format_description())

        if self._state.slow_query_config and self._state.slow_query_config.enabled:
            self._status.set_slow_threshold(int(self._state.slow_query_config.warning_ms))

        # Create tailer
        self._tailer = LogTailer(
            log_path=self._log_path,
            active_levels=self._state.active_levels,
            regex_state=self._state.regex_state,
            time_filter=self._state.time_filter,
            field_filter=self._state.field_filter,
            on_entry=self._on_raw_entry,
            data_dir=self._instance.data_dir,
            log_directory=self._log_path.parent if self._log_path else None,
        )

        # Start tailer and consumer
        self._running = True
        self._tailer.start()
        self._start_consumer()

        # Update initial status
        self._update_status()

        # Focus the log widget
        self.query_one("#log", TailLog).focus()

    def on_unmount(self) -> None:
        """Called when app is unmounting.

        Stops the tailer and sets running flag to False.
        """
        self._running = False
        if self._tailer:
            self._tailer.stop()

    # Actions

    async def action_quit(self) -> None:
        """Exit tail mode and return to REPL."""
        self._running = False
        self.exit()

    def _stop_tailing(self) -> None:
        """Sync wrapper to stop tailing for use as callback."""
        self._running = False
        self.exit()

    def action_focus_input(self) -> None:
        """Focus the command input (/ key)."""
        self.query_one("#input", Input).focus()

    def action_toggle_focus(self) -> None:
        """Toggle focus between log and input (Tab key)."""
        input_widget = self.query_one("#input", Input)
        log_widget = self.query_one("#log", TailLog)
        if input_widget.has_focus:
            log_widget.focus()
        else:
            input_widget.focus()

    # Event handlers

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input submission.

        Args:
            event: Input.Submitted event with command text.
        """
        command = event.value.strip()
        event.input.value = ""
        if command:
            self._handle_command(command)
        # Return focus to log
        self.query_one("#log", TailLog).focus()

    # Background worker

    @work(exclusive=True)
    async def _start_consumer(self) -> None:
        """Background worker consuming log entries.

        Runs until self._running becomes False. Polls the tailer queue
        using run_in_executor to avoid blocking the event loop.
        """
        while self._running and self._tailer:
            tailer = self._tailer  # Capture for lambda
            try:
                # Poll for entry in executor to avoid blocking
                entry: LogEntry | None = await asyncio.get_event_loop().run_in_executor(
                    None, lambda t=tailer: t.get_entry(timeout=0.05)
                )

                if entry is not None:
                    self._add_entry(entry)

            except Exception:
                # Don't crash on individual entry errors
                pass

            # Small yield to keep UI responsive
            await asyncio.sleep(0.01)

    def _on_raw_entry(self, entry: LogEntry) -> None:
        """Callback for raw entries from tailer (before filtering).

        Note: Error/warning counting and stats are handled in _add_entry
        AFTER the entry is added to the log. This callback is kept for
        potential future use (e.g., rate limiting alerts).

        Args:
            entry: The raw log entry.
        """
        # Counting handled in _add_entry
        pass

    def _add_entry(self, entry: LogEntry) -> None:
        """Add a log entry to the display.

        Called from the background worker when a new entry is available.

        Args:
            entry: Parsed log entry to display.
        """
        log_widget = self.query_one("#log", TailLog)

        # Format entry as plain text
        formatted = format_entry_compact(entry)

        # Track if we were at end (for FOLLOW mode)
        was_at_end = log_widget.is_vertical_scroll_end

        # Add to log
        log_widget.write_line(formatted)

        # Update status counts
        if self._status:
            self._status.update_from_entry(entry)
            self._status.set_total_lines(log_widget.line_count)
            new_count = 0 if was_at_end else self._status.new_since_pause + 1
            self._status.set_follow_mode(was_at_end, new_count)
            self._update_status()

        # Update stats
        if self._state:
            self._state.error_stats.add(entry)
            self._state.connection_stats.add(entry)

    def _update_status(self) -> None:
        """Update the status bar display with styled Rich text."""
        status_widget = self.query_one("#status", Static)
        if self._status:
            # Use format_rich for styled Textual Static widget
            status_text = self._status.format_rich()
            status_widget.update(status_text)

    def _handle_command(self, command_text: str) -> None:
        """Handle a command entered in the input line.

        Args:
            command_text: The command text entered by the user.
        """
        from pgtail_py.cli_tail import handle_tail_command

        parts = command_text.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        # Get the log widget for commands that need it
        log_widget = self.query_one("#log", TailLog)

        # Guard against uninitialized state (shouldn't happen in normal flow)
        if self._status is None or self._tailer is None:
            return

        handle_tail_command(
            cmd=cmd,
            args=args,
            buffer=None,  # Not used - replaced by log_widget
            status=self._status,
            state=self._state,
            tailer=self._tailer,
            stop_callback=self._stop_tailing,
            log_widget=log_widget,
        )

        self._update_status()
