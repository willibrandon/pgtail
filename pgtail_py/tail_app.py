"""Main application coordinator for tail mode (DEPRECATED).

.. deprecated:: 0.2.0
    This module is deprecated in favor of tail_textual.TailApp which provides
    Textual-based tail mode with built-in text selection and clipboard support.
    See pgtail_py.tail_textual for the new implementation.

This module provides the TailApp class that coordinates the layout, buffer,
status bar, and log streaming for the status bar tail mode. It manages the
prompt_toolkit Application event loop and background entry consumption.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.styles import Style

from pgtail_py.display import format_entry_compact
from pgtail_py.tail_buffer import FormattedLogEntry, TailBuffer
from pgtail_py.tail_layout import LAYOUT_STYLES, TailLayout
from pgtail_py.tail_status import TailStatus
from pgtail_py.tailer import LogTailer

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance
    from pgtail_py.parser import LogEntry


class TailApp:
    """Main tail mode application coordinator.

    Coordinates the layout, buffer, status bar, and log streaming for the
    status bar tail mode. Manages the prompt_toolkit Application event loop
    and background entry consumption from the LogTailer.

    Attributes:
        _app: prompt_toolkit Application instance
        _layout: TailLayout manager
        _buffer: TailBuffer for log storage
        _status: TailStatus for status bar state
        _tailer: LogTailer for background log streaming
        _running: Application running flag
        _state: pgtail AppState reference
        _consumer_task: Background task consuming log entries
    """

    def __init__(self) -> None:
        """Initialize the TailApp with default empty state."""
        self._app: Application[None] | None = None
        self._layout: TailLayout | None = None
        self._buffer: TailBuffer | None = None
        self._status: TailStatus | None = None
        self._tailer: LogTailer | None = None
        self._running: bool = False
        self._state: AppState | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._instance: Instance | None = None

    @property
    def is_running(self) -> bool:
        """True if the application is currently running."""
        return self._running

    def start(
        self,
        state: AppState,
        instance: Instance,
        log_path: Path,
    ) -> None:
        """Start the tail mode application.

        This method blocks until the user exits tail mode.

        Args:
            state: pgtail AppState with filter settings
            instance: PostgreSQL instance being tailed
            log_path: Path to the log file

        Side effects:
            - Creates LogTailer for background streaming
            - Creates TailBuffer and TailStatus
            - Builds TailLayout
            - Runs prompt_toolkit Application event loop
            - Returns control to caller when user exits
        """
        self._state = state
        self._instance = instance
        self._running = True

        # Create buffer and status
        self._buffer = TailBuffer()
        self._status = TailStatus()

        # Set instance info
        self._status.set_instance_info(
            version=instance.version or "",
            port=instance.port or 5432,
        )

        # Set initial filter state from AppState
        if state.active_levels is not None:
            self._status.set_level_filter(state.active_levels)

        if state.regex_state and state.regex_state.has_filters():
            patterns: list[str] = [f.pattern for f in state.regex_state.includes]
            if patterns:
                self._status.set_regex_filter(patterns[0])

        if state.time_filter and state.time_filter.is_active():
            self._status.set_time_filter(state.time_filter.format_description())

        if state.slow_query_config and state.slow_query_config.enabled:
            self._status.set_slow_threshold(int(state.slow_query_config.warning_ms))

        # Create layout with callbacks
        self._layout = TailLayout(
            log_content_callback=self._get_log_content,
            status_content_callback=self._get_status_content,
            on_command_submit=self._on_command,
            on_scroll_up=self._on_scroll_up,
            on_scroll_down=self._on_scroll_down,
            on_scroll_to_top=self._on_scroll_to_top,
            on_resume_follow=self._on_resume_follow,
            on_redraw=self._on_redraw,
            debug_info_callback=self._get_debug_info,
        )

        # Create tailer with callbacks
        self._tailer = LogTailer(
            log_path=log_path,
            active_levels=state.active_levels,
            regex_state=state.regex_state,
            time_filter=state.time_filter,
            field_filter=state.field_filter,
            on_entry=self._on_raw_entry,
            data_dir=instance.data_dir,
            log_directory=log_path.parent if log_path else None,
        )

        # Build style from theme (if available) or fallback to defaults
        from pgtail_py.tail_layout import generate_layout_styles_from_theme

        if state.theme_manager and state.theme_manager.current_theme:
            # Use theme-based styles
            layout_styles = generate_layout_styles_from_theme(state.theme_manager.current_theme)
            # Get level styles from theme manager
            level_style_rules = []
            theme = state.theme_manager.current_theme
            for level_name in [
                "PANIC",
                "FATAL",
                "ERROR",
                "WARNING",
                "NOTICE",
                "LOG",
                "INFO",
                "DEBUG",
                "DEBUG1",
                "DEBUG2",
                "DEBUG3",
                "DEBUG4",
                "DEBUG5",
            ]:
                color_style = theme.get_level_style(level_name)
                level_style_rules.append((level_name.lower(), color_style.to_style_string()))
        else:
            # Fallback to hardcoded styles
            layout_styles = dict(LAYOUT_STYLES)
            from pgtail_py.colors import LEVEL_STYLES

            level_style_rules = [
                (level.name.lower(), style_str) for level, style_str in LEVEL_STYLES.items()
            ]

        style_rules = list(layout_styles.items()) + level_style_rules
        style = Style(style_rules)

        # Create exit key bindings
        exit_kb = self._create_exit_bindings()

        # Merge layout key bindings with exit bindings
        all_bindings = merge_key_bindings([self._layout.get_key_bindings(), exit_kb])

        # Create Application
        self._app = Application(
            layout=self._layout.layout,
            key_bindings=all_bindings,
            style=style,
            full_screen=True,
            mouse_support=True,
        )

        # Run the application with background consumer
        try:
            self._app.run(pre_run=self._start_background_tasks)
        finally:
            self._cleanup()

    def _create_exit_bindings(self) -> KeyBindings:
        """Create key bindings for exiting tail mode.

        Returns:
            KeyBindings with Ctrl+C handler
        """
        kb = KeyBindings()

        @kb.add("c-c")
        def exit_app(event: object) -> None:
            """Exit to REPL on Ctrl+C."""
            self.stop()

        _ = exit_app  # Registered via decorator
        return kb

    def _start_background_tasks(self) -> None:
        """Start background tasks before the app runs.

        Called by Application.run() as pre_run callback.
        Starts the LogTailer and the entry consumer coroutine.
        """
        if self._tailer:
            self._tailer.start()

        # Schedule the consumer coroutine
        loop = asyncio.get_event_loop()
        self._consumer_task = loop.create_task(self._consume_entries())

    async def _consume_entries(self) -> None:
        """Background coroutine that consumes entries from the tailer.

        Runs until self._running becomes False. Polls the tailer queue
        using run_in_executor to avoid blocking the event loop.
        """
        while self._running and self._tailer:
            tailer = self._tailer  # Capture for lambda
            try:
                # Poll for entry in executor to avoid blocking
                entry = await asyncio.get_event_loop().run_in_executor(
                    None, lambda t=tailer: t.get_entry(timeout=0.05)
                )

                if entry is not None:
                    # Format and add to buffer (append sets matches_filter)
                    formatted = format_entry_compact(entry)
                    formatted_entry = FormattedLogEntry(entry=entry, formatted=formatted)
                    self._buffer.append(formatted_entry)  # type: ignore[union-attr]

                    # Only count errors/warnings/stats if entry passes filters
                    if formatted_entry.matches_filter:
                        if self._status:
                            self._status.update_from_entry(entry)
                        if self._state:
                            self._state.error_stats.add(entry)
                            self._state.connection_stats.add(entry)

                    # Update status line count (use filtered_count, not total)
                    if self._status:
                        self._status.set_total_lines(self._buffer.filtered_count)  # type: ignore[union-attr]
                        self._status.set_follow_mode(
                            self._buffer.follow_mode,  # type: ignore[union-attr]
                            self._buffer.new_since_pause,  # type: ignore[union-attr]
                        )

                    # Trigger UI refresh - this is thread-safe
                    if self._app:
                        self._app.invalidate()

            except Exception:
                # Don't crash on individual entry errors
                pass

            # Small yield to keep UI responsive
            await asyncio.sleep(0.01)

    def _on_raw_entry(self, entry: LogEntry) -> None:
        """Callback for raw entries from tailer (before filtering).

        Note: Error/warning counting and stats are now handled in _consume_entries
        AFTER filtering, so counts match what's actually displayed.
        This callback is kept for potential future use (e.g., rate limiting alerts).

        Args:
            entry: The raw log entry
        """
        # Counting moved to _consume_entries to respect filters
        pass

    def stop(self) -> None:
        """Stop the tail mode application.

        Called by exit commands (stop, exit, q) or Ctrl+C.

        Side effects:
            - Stops background entry consumer
            - Stops LogTailer
            - Exits Application event loop
        """
        self._running = False

        if self._app:
            self._app.exit()

    def _cleanup(self) -> None:
        """Clean up resources after application exits."""
        self._running = False

        # Cancel consumer task
        if self._consumer_task and not self._consumer_task.done():
            self._consumer_task.cancel()

        # Stop tailer
        if self._tailer:
            self._tailer.stop()
            self._tailer = None

        # Clear references
        self._app = None
        self._layout = None
        self._buffer = None
        self._status = None

    def _get_log_content(self) -> FormattedText:
        """Callback to get log content for display.

        Returns:
            FormattedText with visible log entries
        """
        if self._buffer is None:
            return FormattedText([("", "")])

        # Get approximate visible height
        height = self._layout.get_visible_height() if self._layout else 20
        return self._buffer.get_visible_lines(height)

    def _get_status_content(self) -> FormattedText:
        """Callback to get status bar content.

        Returns:
            FormattedText with status bar content
        """
        if self._status is None:
            return FormattedText([("", "Loading...")])

        return self._status.format()

    def _on_command(self, command_text: str) -> None:
        """Handle a command entered in the input line.

        Args:
            command_text: The command text entered by the user
        """
        from pgtail_py.cli_tail import handle_tail_command

        # Parse command
        parts = command_text.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        # Handle the command
        handle_tail_command(
            cmd=cmd,
            args=args,
            buffer=self._buffer,  # type: ignore[arg-type]
            status=self._status,  # type: ignore[arg-type]
            state=self._state,  # type: ignore[arg-type]
            tailer=self._tailer,  # type: ignore[arg-type]
            stop_callback=self.stop,
        )

        # Invalidate to show any changes
        if self._app:
            self._app.invalidate()

    def _on_scroll_up(self, lines: int) -> None:
        """Handle scroll up event.

        Args:
            lines: Number of lines to scroll
        """
        if self._buffer:
            self._buffer.scroll_up(lines)
            if self._status:
                self._status.set_follow_mode(
                    self._buffer.follow_mode,
                    self._buffer.new_since_pause,
                )
            if self._app:
                self._app.invalidate()

    def _on_scroll_down(self, lines: int) -> None:
        """Handle scroll down event.

        Args:
            lines: Number of lines to scroll
        """
        if self._buffer:
            self._buffer.scroll_down(lines)
            if self._status:
                self._status.set_follow_mode(
                    self._buffer.follow_mode,
                    self._buffer.new_since_pause,
                )
            if self._app:
                self._app.invalidate()

    def _on_scroll_to_top(self) -> None:
        """Handle scroll to top event."""
        if self._buffer:
            self._buffer.scroll_to_top()
            if self._status:
                self._status.set_follow_mode(
                    self._buffer.follow_mode,
                    self._buffer.new_since_pause,
                )
            if self._app:
                self._app.invalidate()

    def _on_resume_follow(self) -> None:
        """Handle resume follow event."""
        if self._buffer:
            self._buffer.resume_follow()
            if self._status:
                self._status.set_follow_mode(True, 0)
            if self._app:
                self._app.invalidate()

    def _on_redraw(self) -> None:
        """Handle redraw request (Ctrl+L)."""
        if self._app:
            self._app.invalidate()

    def _get_debug_info(self) -> dict[str, object]:
        """Get debug information for the debug overlay.

        Returns:
            Dict with buffer state, filter info, and other diagnostics
        """
        info: dict[str, object] = {}

        # Buffer state
        if self._buffer:
            info["total_entries"] = self._buffer.total_entries
            info["filtered_count"] = self._buffer.filtered_count
            info["visual_lines"] = self._buffer.total_visual_lines
            info["scroll_offset"] = self._buffer._scroll_offset
            info["follow_mode"] = self._buffer.follow_mode
            info["new_since_pause"] = self._buffer.new_since_pause
            info["max_size"] = self._buffer.max_size
            # Debug: count entries that would be visible
            height = self._layout.get_visible_height() if self._layout else 20
            info["display_height"] = height

        # Filter state from AppState
        if self._state:
            if self._state.active_levels:
                info["active_levels"] = ",".join(
                    level.name for level in sorted(self._state.active_levels, key=lambda x: x.value)
                )
            else:
                info["active_levels"] = None

            if self._state.time_filter and self._state.time_filter.is_active():
                info["time_filter"] = self._state.time_filter.format_description()
            else:
                info["time_filter"] = None

            if self._state.regex_state and self._state.regex_state.has_filters():
                patterns = [f.pattern for f in self._state.regex_state.includes]
                info["regex_filter"] = ", ".join(patterns) if patterns else None
            else:
                info["regex_filter"] = None

        return info
