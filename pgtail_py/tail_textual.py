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
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Input, Static

from pgtail_py.filter import LogLevel
from pgtail_py.regex_filter import FilterState
from pgtail_py.tail_input import TailInput
from pgtail_py.tail_log import TailLog
from pgtail_py.tail_rich import format_entry_compact
from pgtail_py.tail_status import TailStatus
from pgtail_py.tailer import LogTailer
from pgtail_py.time_filter import TimeFilter

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance
    from pgtail_py.parser import LogEntry


@dataclass
class FilterAnchor:
    """Stores initial filter state for reset-to-anchor behavior.

    When the user enters tail mode with filters (e.g., `tail 0 --since 1h`),
    this captures those initial filters. The `clear` command resets to this
    anchor, while `clear force` clears everything including the anchor.
    """

    active_levels: set[LogLevel] | None = None
    regex_state: FilterState = field(default_factory=FilterState.empty)
    time_filter: TimeFilter = field(default_factory=TimeFilter.empty)


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

    /* Header bar with keybinding hints */
    #header {
        height: 1;
        width: 100%;
        background: $panel;
        color: $text-muted;
    }

    /* Status bar at bottom */
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
        Binding("question_mark", "show_help", "Help", show=False),
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
        # Store all entries for filter-based rebuilding
        self._entries: list[LogEntry] = []
        # Anchor stores initial filter state for reset behavior
        self._anchor: FilterAnchor | None = None
        # Explicit pause flag - prevents auto-follow when user issues pause command
        self._paused: bool = False

    @property
    def status(self) -> TailStatus | None:
        """Get the status object (for testing)."""
        return self._status

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
        - Static: Header with keybinding hints
        - Static: Separator line
        - TailLog: Log display area (flexible height)
        - Static: Separator line
        - TailInput: Command input line (tail> prompt)
        - Static: Separator line
        - Static: Status bar (FOLLOW/PAUSED, counts, filters)

        Yields:
            Widgets in layout order.
        """
        yield Static(id="header")
        yield Static("─" * 200, classes="separator")
        yield TailLog(max_lines=self._max_lines, auto_scroll=True, id="log")
        yield Static("─" * 200, classes="separator")
        yield TailInput()
        yield Static("─" * 200, classes="separator")
        yield Static(id="status")

    def on_mount(self) -> None:
        """Called when app is mounted.

        Initializes the status bar, creates the LogTailer, and starts
        the background consumer worker.
        """
        # Capture initial filter state as anchor (for clear command reset)
        self._anchor = FilterAnchor(
            active_levels=(set(self._state.active_levels) if self._state.active_levels else None),
            regex_state=(
                deepcopy(self._state.regex_state)
                if self._state.regex_state
                else FilterState.empty()
            ),
            time_filter=(
                deepcopy(self._state.time_filter) if self._state.time_filter else TimeFilter.empty()
            ),
        )

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

        # Expose tailer on state for export/pipe commands to access buffer
        self._state.tailer = self._tailer

        # Start tailer and consumer
        self._running = True
        self._tailer.start()
        self._start_consumer()

        # Update initial status
        self._update_status()

        # Focus the input widget (tail> prompt) - users expect to type commands
        self.query_one("#input", TailInput).focus()

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

    def action_show_help(self) -> None:
        """Show help overlay with keybindings (? key)."""
        from pgtail_py.tail_help import HelpScreen

        self.push_screen(HelpScreen())

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

    @on(TailLog.PauseRequested)
    def on_pause_requested(self, event: TailLog.PauseRequested) -> None:
        """Handle pause request from TailLog (p key).

        Args:
            event: PauseRequested event.
        """
        self._paused = True
        if self._status:
            self._status.set_follow_mode(False, 0)
            self._update_status()

    @on(TailLog.FollowRequested)
    def on_follow_requested(self, event: TailLog.FollowRequested) -> None:
        """Handle follow request from TailLog (f key).

        Args:
            event: FollowRequested event.
        """
        self._paused = False
        # Rebuild log to include entries that arrived while paused
        self._rebuild_log()
        if self._status:
            self._status.set_follow_mode(True, 0)
            self._update_status()

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
                loop = asyncio.get_running_loop()
                entry: LogEntry | None = await loop.run_in_executor(
                    None, lambda t=tailer: t.get_entry(timeout=0.05)
                )

                if entry is not None:
                    self._add_entry(entry)

            except asyncio.CancelledError:
                # Task was cancelled, stop cleanly
                break
            except Exception:
                # Log error but don't crash on individual entry errors
                logger.debug("Error processing log entry", exc_info=True)

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
        # Store entry for filter-based rebuilding (limit to max_lines)
        self._entries.append(entry)
        if len(self._entries) > self._max_lines:
            self._entries.pop(0)

        # Update global stats (always, regardless of filter)
        if self._state:
            self._state.error_stats.add(entry)
            self._state.connection_stats.add(entry)

        # Check if entry passes current filters
        if not self._entry_matches_filters(entry):
            return

        # When paused, don't add to visible log - just count new entries
        if self._paused:
            if self._status:
                self._status.update_from_entry(entry)
                self._status.set_follow_mode(False, self._status.new_since_pause + 1)
                self._update_status()
            return

        log_widget = self.query_one("#log", TailLog)

        # Format entry with current theme for SQL highlighting
        formatted = format_entry_compact(entry, theme=self._state.theme_manager.current_theme)

        # Track if we were at end (for FOLLOW mode)
        was_at_end = log_widget.is_vertical_scroll_end

        # Add to log
        log_widget.write_line(formatted)

        # Update status counts (only for displayed entries)
        if self._status:
            self._status.update_from_entry(entry)
            self._status.set_total_lines(log_widget.line_count)
            new_count = 0 if was_at_end else self._status.new_since_pause + 1
            self._status.set_follow_mode(was_at_end, new_count)
            self._update_status()

    def _entry_matches_filters(self, entry: LogEntry) -> bool:
        """Check if an entry matches current filter settings.

        Args:
            entry: Log entry to check.

        Returns:
            True if entry should be displayed, False if filtered out.
        """
        # Level filter
        if self._state.active_levels is not None and entry.level not in self._state.active_levels:
            return False

        # Regex filter
        if (
            self._state.regex_state
            and self._state.regex_state.has_filters()
            and not self._state.regex_state.should_show(entry.raw)
        ):
            return False

        # Time filter
        if self._state.time_filter and self._state.time_filter.is_active():
            return self._state.time_filter.matches(entry)

        return True

    def _rebuild_log(self) -> None:
        """Rebuild log display from stored entries with current filters.

        Clears the log widget and re-adds all entries that match the
        current filter settings. Called when filters change.
        """
        log_widget = self.query_one("#log", TailLog)

        # Clear log and reset status counts
        log_widget.clear()
        if self._status:
            self._status.error_count = 0
            self._status.warning_count = 0

        # Re-add entries that match current filters
        for entry in self._entries:
            if self._entry_matches_filters(entry):
                formatted = format_entry_compact(entry, theme=self._state.theme_manager.current_theme)
                log_widget.write_line(formatted)
                if self._status:
                    self._status.update_from_entry(entry)

        # Update total line count
        if self._status:
            self._status.set_total_lines(log_widget.line_count)
            self._update_status()

    def _reset_to_anchor(self) -> None:
        """Reset filters to the initial anchor state.

        Restores filters to what they were when tail mode was entered
        (e.g., `tail 0 --since 1h`). Called by `clear` command.
        """
        if self._anchor is None or self._tailer is None:
            return

        # Restore filter state from anchor
        self._state.active_levels = (
            set(self._anchor.active_levels) if self._anchor.active_levels else None
        )
        self._state.regex_state = deepcopy(self._anchor.regex_state)
        self._state.time_filter = deepcopy(self._anchor.time_filter)

        # Update tailer with restored filters
        self._tailer.update_levels(self._state.active_levels)
        self._tailer.update_regex_state(self._state.regex_state)
        self._tailer.update_time_filter(self._state.time_filter)

        # Update status bar
        if self._status:
            if self._state.active_levels is None:
                self._status.set_level_filter(LogLevel.all_levels())
            else:
                self._status.set_level_filter(self._state.active_levels)

            if self._state.regex_state and self._state.regex_state.has_filters():
                patterns = [f.pattern for f in self._state.regex_state.includes]
                self._status.set_regex_filter(patterns[0] if patterns else None)
            else:
                self._status.set_regex_filter(None)

            if self._state.time_filter and self._state.time_filter.is_active():
                self._status.set_time_filter(self._state.time_filter.format_description())
            else:
                self._status.set_time_filter(None)

        # Rebuild log with restored filters
        self._rebuild_log()

    def _update_status(self) -> None:
        """Update the header and status bar displays with styled Rich text."""
        if self._status:
            # Update header with keybinding hints
            header_widget = self.query_one("#header", Static)
            header_widget.update(self._status.format_header())

            # Update status bar with mode, counts, filters
            status_widget = self.query_one("#status", Static)
            status_widget.update(self._status.format_rich())

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

        # Handle clear command specially for anchor behavior
        if cmd == "clear":
            if args and args[0].lower() == "force":
                # clear force: clear everything including anchor, start fresh
                self._entries.clear()
                handle_tail_command(
                    cmd=cmd,
                    args=[],  # Don't pass 'force' to cli_tail
                    buffer=None,
                    status=self._status,
                    state=self._state,
                    tailer=self._tailer,
                    stop_callback=self._stop_tailing,
                    log_widget=log_widget,
                )
            else:
                # clear: reset to anchor (initial filters when tail mode started)
                self._reset_to_anchor()
            self._update_status()
            return

        # Handle pause/follow commands to set explicit pause flag
        if cmd in ("pause", "p"):
            self._paused = True
            self._status.set_follow_mode(False, 0)
            self._update_status()
            return

        if cmd in ("follow", "f"):
            self._paused = False
            self._status.set_follow_mode(True, 0)
            # Rebuild log to include entries that arrived while paused
            self._rebuild_log()
            log_widget.scroll_end()
            self._update_status()
            return

        # Handle theme command - switch theme and rebuild log with new colors
        if cmd == "theme":
            if not args:
                # Show current theme
                current = self._state.theme_manager.current_theme
                if current:
                    log_widget.write_line(f"[dim]Current theme:[/] [bold cyan]{current.name}[/]")
                else:
                    log_widget.write_line("[dim]No theme set[/]")
            else:
                theme_name = args[0]
                if self._state.theme_manager.switch_theme(theme_name):
                    # Rebuild log to re-render all entries with new theme colors
                    self._rebuild_log()
                    # Show success message with theme name in color
                    log_widget.write_line(f"[bold green]✓[/] Switched to theme [bold cyan]{theme_name}[/]")
                else:
                    # Show error - theme not found
                    available = ", ".join(sorted(self._state.theme_manager._themes.keys()))
                    log_widget.write_line(f"[bold red]✗[/] Unknown theme [bold yellow]{theme_name}[/]. Available: {available}")
            self._update_status()
            return

        # Check if this is a help request (don't rebuild log for help)
        is_help_request = args and args[0].lower() in ("help", "?")

        # Track if this is a filter command that needs log rebuild
        filter_commands = {"level", "filter", "since", "until", "between"}
        needs_rebuild = cmd in filter_commands and not is_help_request

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

        # Rebuild log with new filters applied to stored entries
        if needs_rebuild:
            self._rebuild_log()

        self._update_status()
