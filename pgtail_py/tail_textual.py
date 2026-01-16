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
import re
import shlex
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Input, Rule, Static

from pgtail_py.filter import LogLevel
from pgtail_py.multi_tailer import GlobPattern, MultiFileTailer
from pgtail_py.regex_filter import FilterState
from pgtail_py.stdin_reader import StdinReader
from pgtail_py.tail_input import TailInput
from pgtail_py.tail_log import TailLog
from pgtail_py.tail_rich import format_entry_compact
from pgtail_py.tail_status import TailStatus
from pgtail_py.tailer import LogTailer
from pgtail_py.time_filter import TimeFilter

logger = logging.getLogger(__name__)

# Regex patterns for detecting PostgreSQL version and port from log content (T015, T087)
# Matches: "starting PostgreSQL 17.0 on x86_64..."
VERSION_PATTERN = re.compile(r"starting PostgreSQL (\d+)(?:\.(\d+))?", re.IGNORECASE)

# Matches: "listening on IPv4 address "0.0.0.0", port 5432"
PORT_PATTERN = re.compile(r"listening on .*port (\d+)")

# Matches: "listening on Unix socket "/tmp/.s.PGSQL.5432""
PORT_SOCKET_PATTERN = re.compile(r"\.s\.PGSQL\.(\d+)")

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.instance import Instance
    from pgtail_py.parser import LogEntry


@dataclass
class DetectedInstanceInfo:
    """PostgreSQL instance info detected from log content.

    Used when tailing arbitrary files to extract version/port
    from PostgreSQL startup messages.
    """

    version: str | None = None  # e.g., "17" or "17.0"
    port: int | None = None  # e.g., 5432


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

    /* Separator lines - override Rule default margin */
    Rule {
        margin: 0;
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
        instance: Instance | None,
        log_path: Path | None,
        max_lines: int = 10000,
        *,
        filename: str | None = None,
        multi_file_paths: list[Path] | None = None,
        glob_pattern: str | None = None,
        stdin_mode: bool = False,
        stdin_data: str | None = None,
    ) -> None:
        """Initialize TailApp.

        Args:
            state: pgtail AppState with filter settings.
            instance: PostgreSQL instance being tailed, or None for file-only mode.
            log_path: Path to the log file (primary file for single-file mode), or None for stdin.
            max_lines: Maximum lines to buffer (default 10,000).
            filename: Display name for status bar when instance is None.
            multi_file_paths: List of paths for multi-file tailing (T075).
            glob_pattern: Glob pattern for dynamic file watching (T089).
            stdin_mode: True to read from stdin pipe instead of file (T080).
            stdin_data: Pre-buffered stdin data (read before Textual starts) (T080).
        """
        super().__init__()
        self._state: AppState = state
        self._instance: Instance | None = instance
        self._log_path: Path | None = log_path
        self._max_lines: int = max_lines
        self._tailer: LogTailer | None = None
        self._multi_tailer: MultiFileTailer | None = None  # T075: Multi-file support
        self._stdin_reader: StdinReader | None = None  # T080: Stdin pipe support
        self._status: TailStatus | None = None
        self._running: bool = False
        # Store all entries for filter-based rebuilding
        self._entries: list[LogEntry] = []
        # Anchor stores initial filter state for reset behavior
        self._anchor: FilterAnchor | None = None
        # Explicit pause flag - prevents auto-follow when user issues pause command
        self._paused: bool = False
        # File-only mode support (T011, T012)
        self._filename: str | None = filename or (
            log_path.name if instance is None and log_path else None
        )
        self._instance_detected: bool = False  # True when version/port detected from content
        self._detection_entries_scanned: int = 0  # Track entries scanned for detection
        # Track file unavailability for status bar updates (T052)
        self._last_file_unavailable: bool = False
        # Multi-file tailing support (T075, T089)
        self._multi_file_paths: list[Path] | None = multi_file_paths
        self._glob_pattern: str | None = glob_pattern
        self._is_multi_file: bool = multi_file_paths is not None and len(multi_file_paths) > 1
        # T080: Stdin mode flag and pre-buffered data
        self._stdin_mode: bool = stdin_mode
        self._stdin_data: str | None = stdin_data

    @property
    def status(self) -> TailStatus | None:
        """Get the status object (for testing)."""
        return self._status

    @classmethod
    def run_tail_mode(
        cls,
        state: AppState,
        instance: Instance | None,
        log_path: Path | None,
        *,
        filename: str | None = None,
        multi_file_paths: list[Path] | None = None,
        glob_pattern: str | None = None,
        stdin_mode: bool = False,
        stdin_data: str | None = None,
    ) -> None:
        """Run tail mode (blocking).

        This is the main entry point called from cli.py.

        Args:
            state: pgtail AppState with filter settings.
            instance: PostgreSQL instance being tailed, or None for file-only mode.
            log_path: Path to the log file (primary file), or None for stdin mode.
            filename: Display name for status bar when instance is None.
            multi_file_paths: List of paths for multi-file tailing (T075).
            glob_pattern: Glob pattern for dynamic file watching (T089).
            stdin_mode: True to read from stdin pipe instead of file (T080).
            stdin_data: Pre-buffered stdin data (read before Textual starts) (T080).
        """
        app = cls(
            state=state,
            instance=instance,
            log_path=log_path,
            filename=filename,
            multi_file_paths=multi_file_paths,
            glob_pattern=glob_pattern,
            stdin_mode=stdin_mode,
            stdin_data=stdin_data,
        )
        app.run()

    def compose(self) -> ComposeResult:
        """Compose the application layout.

        Layout (top to bottom):
        - Static: Header with keybinding hints
        - Rule: Separator line (full width)
        - TailLog: Log display area (flexible height)
        - Rule: Separator line (full width)
        - TailInput: Command input line (tail> prompt)
        - Rule: Separator line (full width)
        - Static: Status bar (FOLLOW/PAUSED, counts, filters)

        Yields:
            Widgets in layout order.
        """
        yield Static(id="header")
        yield Rule()
        yield TailLog(max_lines=self._max_lines, auto_scroll=True, id="log")
        yield Rule()
        yield TailInput()
        yield Rule()
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

        # T013: Handle instance=None case for file-only tailing
        if self._instance is not None:
            # Standard instance tailing
            self._status.set_instance_info(
                version=self._instance.version or "",
                port=self._instance.port or 5432,
            )
        elif self._filename:
            # File-only mode - show filename in status bar
            self._status.set_file_source(self._filename)

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

        # Create tailer - handle single-file, multi-file, stdin, and instance modes
        data_dir = self._instance.data_dir if self._instance else None

        if self._stdin_mode:
            # T080, T081, T082: Stdin pipe input mode
            # Use pre-buffered data via StringIO (stdin was read before Textual started)
            import io

            stdin_stream = io.StringIO(self._stdin_data or "")
            self._stdin_reader = StdinReader(
                active_levels=self._state.active_levels,
                regex_state=self._state.regex_state,
                time_filter=self._state.time_filter,
                field_filter=self._state.field_filter,
                on_entry=self._on_raw_entry,
                on_eof=self._on_stdin_eof,
                stdin=stdin_stream,
            )
            # Expose for export/pipe commands
            self._state.tailer = None  # Stdin doesn't use LogTailer
        elif self._is_multi_file and self._multi_file_paths:
            # T075, T089: Multi-file tailing with timestamp interleaving
            glob_obj = GlobPattern.from_path(self._glob_pattern) if self._glob_pattern else None
            self._multi_tailer = MultiFileTailer(
                paths=self._multi_file_paths,
                glob_pattern=glob_obj,
                active_levels=self._state.active_levels,
                regex_state=self._state.regex_state,
                time_filter=self._state.time_filter,
                field_filter=self._state.field_filter,
                on_entry=self._on_raw_entry,
            )
            # Expose for export/pipe commands
            self._state.tailer = None  # Multi-file doesn't use LogTailer
        else:
            # Single-file mode
            self._tailer = LogTailer(
                log_path=self._log_path,
                active_levels=self._state.active_levels,
                regex_state=self._state.regex_state,
                time_filter=self._state.time_filter,
                field_filter=self._state.field_filter,
                on_entry=self._on_raw_entry,
                data_dir=data_dir,
                log_directory=self._log_path.parent if self._log_path else None,
            )
            # Expose tailer on state for export/pipe commands to access buffer
            self._state.tailer = self._tailer

        # Start tailer and consumer
        self._running = True
        if self._stdin_reader:
            self._stdin_reader.start()
        elif self._multi_tailer:
            self._multi_tailer.start()
        else:
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
        if self._multi_tailer:
            self._multi_tailer.stop()
        if self._stdin_reader:
            self._stdin_reader.stop()

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

    def _on_stdin_eof(self) -> None:
        """Callback when EOF is reached on stdin.

        T082: Handle EOF gracefully. For pre-buffered stdin data, we don't
        auto-exit - the user can browse the data and quit with 'q'.
        Uses call_from_thread to safely schedule the UI update on the main thread.
        """
        # Schedule UI update on the main thread
        self.call_from_thread(self._handle_stdin_eof)

    def _handle_stdin_eof(self) -> None:
        """Handle stdin EOF on the main thread.

        Shows a message indicating all stdin data has been loaded.
        Does NOT auto-exit - user can browse data and quit with 'q'.
        """
        # Show completion message in log
        log_widget = self.query_one("#log", TailLog)
        lines_read = self._stdin_reader.lines_read if self._stdin_reader else 0
        log_widget.write_line(
            f"[dim]--- stdin complete ({lines_read} lines loaded) - press 'q' to quit ---[/]"
        )

    @work(exclusive=True)
    async def _start_consumer(self) -> None:
        """Background worker consuming log entries.

        Runs until self._running becomes False. Polls the tailer queue
        using run_in_executor to avoid blocking the event loop.

        Optimized to process entries in batches - loops until queue is
        empty before yielding, avoiding unnecessary sleeps when entries
        are available.

        Supports single-file LogTailer, multi-file MultiFileTailer, and stdin StdinReader.
        """
        loop = asyncio.get_running_loop()

        # Determine which tailer to use
        active_tailer = self._stdin_reader or self._multi_tailer or self._tailer
        if active_tailer is None:
            return

        while self._running and active_tailer:
            tailer = active_tailer  # Capture for lambda
            entries_processed = 0

            # T082: For stdin mode, EOF just means all data is loaded
            # The consumer continues running so user can interact with the UI
            # (EOF callback shows a message, but doesn't exit)

            try:
                # Process all available entries in a batch before yielding
                while self._running:
                    entry: LogEntry | None = await loop.run_in_executor(
                        None, lambda t=tailer: t.get_entry(timeout=0.01)
                    )

                    if entry is None:
                        # Queue is empty, break inner loop
                        break

                    self._add_entry(entry)
                    entries_processed += 1

                    # Yield periodically during large batches to keep UI responsive
                    if entries_processed % 50 == 0:
                        await asyncio.sleep(0)

            except asyncio.CancelledError:
                # Task was cancelled, stop cleanly
                break
            except Exception:
                # Log error but don't crash on individual entry errors
                logger.debug("Error processing log entry", exc_info=True)

            # Only sleep when queue was empty (no entries processed this cycle)
            if entries_processed == 0:
                await asyncio.sleep(0.01)
                # Check for file unavailability status changes (T052)
                self._check_file_unavailable()
            else:
                # Brief yield after processing batch to let UI update
                await asyncio.sleep(0)

    def _check_file_unavailable(self) -> None:
        """Check if file unavailability status has changed and update status bar.

        Called periodically from the consumer loop to detect when the log file
        is deleted or becomes inaccessible. Updates the status bar to show
        "(unavailable)" indicator when file is missing. (T052)

        For multi-file mode, shows unavailable if any file is unavailable.
        """
        if self._status is None:
            return

        if self._multi_tailer:
            # Multi-file mode: check if any files are unavailable
            current_unavailable = len(self._multi_tailer.files_unavailable) > 0
        elif self._tailer:
            # Single-file mode
            current_unavailable = self._tailer.file_unavailable
        else:
            return

        if current_unavailable != self._last_file_unavailable:
            self._last_file_unavailable = current_unavailable
            self._status.set_file_unavailable(current_unavailable)
            self._update_status()

    def _on_raw_entry(self, entry: LogEntry) -> None:
        """Callback for raw entries from tailer (before filtering).

        Handles notifications, error stats, and connection stats tracking
        for ALL entries, matching stream mode behavior in cli_core.py.

        Args:
            entry: The raw log entry.
        """
        # Track error/connection stats for all entries (before filtering)
        self._state.error_stats.add(entry)
        self._state.connection_stats.add(entry)

        # Check notification rules
        if self._state.notification_manager:
            self._state.notification_manager.check(entry)

    def _detect_instance_info(self, entry: LogEntry) -> DetectedInstanceInfo | None:
        """Detect PostgreSQL version and port from log entry content.

        Scans log messages for PostgreSQL startup patterns that reveal
        version and port information. Only scans the first 50 entries
        for performance.

        Args:
            entry: Log entry to scan.

        Returns:
            DetectedInstanceInfo if version or port found, None otherwise.
        """
        message = entry.message

        result = DetectedInstanceInfo()
        found = False

        # Check for version pattern: "starting PostgreSQL 17.0 on..."
        version_match = VERSION_PATTERN.search(message)
        if version_match:
            major = version_match.group(1)
            minor = version_match.group(2)
            result.version = f"{major}.{minor}" if minor else major
            found = True

        # Check for port pattern: "listening on ... port 5432"
        port_match = PORT_PATTERN.search(message)
        if port_match:
            result.port = int(port_match.group(1))
            found = True

        # Check for Unix socket port pattern: ".s.PGSQL.5432"
        if result.port is None:
            socket_match = PORT_SOCKET_PATTERN.search(message)
            if socket_match:
                result.port = int(socket_match.group(1))
                found = True

        return result if found else None

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

        # T016: Detect instance info from log content (file-only mode)
        # Only scan first 50 entries and only if no instance provided
        if (
            self._instance is None
            and not self._instance_detected
            and self._detection_entries_scanned < 50
        ):
            self._detection_entries_scanned += 1
            detected = self._detect_instance_info(entry)
            if detected and (detected.version or detected.port) and self._status:
                self._status.set_detected_instance_info(detected.version, detected.port)
                # If we found version, we can mark detection as complete
                if detected.version:
                    self._instance_detected = True
                self._update_status()

        # Note: Global stats (error_stats, connection_stats) and notifications
        # are handled in _on_raw_entry() which is called for ALL entries before
        # filtering, matching stream mode behavior.

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

        # Format entry with current theme and highlighting config
        formatted = format_entry_compact(
            entry,
            theme=self._state.theme_manager.current_theme,
            highlighting_config=self._state.highlighting_config,
        )

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

    def _handle_export_command(self, args: list[str], log_widget: TailLog) -> None:
        """Handle export command in tail mode.

        Exports currently displayed entries to a file.

        Args:
            args: Command arguments [path, --format <fmt>, --highlighted]
            log_widget: TailLog widget for feedback
        """
        from pgtail_py.export import ExportFormat, export_to_file

        if not args:
            log_widget.write_line(
                "[bold red]✗[/] Usage: export <path> [--format text|json|csv] [--highlighted]"
            )
            return

        # Parse arguments
        path_str: str | None = None
        fmt = ExportFormat.TEXT
        preserve_markup = False

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--format" and i + 1 < len(args):
                try:
                    fmt = ExportFormat.from_string(args[i + 1])
                except ValueError as e:
                    log_widget.write_line(f"[bold red]✗[/] {e}")
                    return
                i += 2
            elif arg == "--highlighted":
                preserve_markup = True
                i += 1
            elif not arg.startswith("-"):
                path_str = arg
                i += 1
            else:
                log_widget.write_line(f"[bold red]✗[/] Unknown option: {arg}")
                return

        if not path_str:
            log_widget.write_line("[bold red]✗[/] No output path specified")
            return

        # Expand ~ and resolve path
        path = Path(path_str).expanduser().resolve()

        # Get entries that match current filters
        filtered_entries = [e for e in self._entries if self._entry_matches_filters(e)]

        if not filtered_entries:
            log_widget.write_line("[yellow]⚠[/] No entries to export (buffer empty or all filtered)")
            return

        # Export
        try:
            if preserve_markup and fmt == ExportFormat.TEXT:
                # For --highlighted in tail mode, export the Rich-formatted lines
                # (same as what's displayed in the log widget)
                from pgtail_py.export import ensure_parent_dirs

                ensure_parent_dirs(path)
                count = 0
                with open(path, "w", encoding="utf-8") as f:
                    for entry in filtered_entries:
                        formatted = format_entry_compact(
                            entry,
                            theme=self._state.theme_manager.current_theme,
                            highlighting_config=self._state.highlighting_config,
                        )
                        f.write(formatted + "\n")
                        count += 1
            else:
                # Standard export (strips markup for clean text/JSON/CSV)
                count = export_to_file(
                    filtered_entries,
                    path,
                    fmt,
                    append=False,
                    preserve_markup=False,  # Never preserve raw markup for standard export
                )
            log_widget.write_line(
                f"[bold green]✓[/] Exported {count} entries to [cyan]{path}[/]"
            )
        except OSError as e:
            log_widget.write_line(f"[bold red]✗[/] Export failed: {e}")

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
                formatted = format_entry_compact(
                    entry,
                    theme=self._state.theme_manager.current_theme,
                    highlighting_config=self._state.highlighting_config,
                )
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

        # Use shlex to properly handle quoted arguments
        try:
            parts = shlex.split(command_text.strip())
        except ValueError:
            # Unclosed quote or other parse error - fall back to simple split
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
                    log_widget.write_line(
                        f"[bold green]✓[/] Switched to theme [bold cyan]{theme_name}[/]"
                    )
                else:
                    # Show error - theme not found
                    available = ", ".join(sorted(self._state.theme_manager._themes.keys()))
                    log_widget.write_line(
                        f"[bold red]✗[/] Unknown theme [bold yellow]{theme_name}[/]. Available: {available}"
                    )
            self._update_status()
            return

        # Handle export command - needs access to self._entries
        if cmd == "export":
            self._handle_export_command(args, log_widget)
            return

        # Check if this is a help request (don't rebuild log for help)
        is_help_request = args and args[0].lower() in ("help", "?")

        # Track if this is a filter command that needs log rebuild
        filter_commands = {"level", "filter", "since", "until", "between"}
        needs_rebuild = cmd in filter_commands and not is_help_request

        # Highlight commands that modify state need rebuild + cache reset
        highlight_modifies = {"enable", "disable", "add", "remove", "on", "off"}
        needs_highlight_rebuild = (
            cmd == "highlight"
            and args
            and args[0].lower() in highlight_modifies
            and not is_help_request
        )

        # Set commands that modify highlighting duration thresholds need rebuild
        needs_set_highlight_rebuild = (
            cmd == "set"
            and len(args) >= 2
            and args[0].startswith("highlighting.duration.")
            and not is_help_request
        )

        # For commands that need rebuild, don't pass log_widget
        # (message would be erased by rebuild). We'll show feedback after.
        effective_log_widget = (
            None if (needs_highlight_rebuild or needs_set_highlight_rebuild) else log_widget
        )

        handle_tail_command(
            cmd=cmd,
            args=args,
            buffer=None,  # Not used - replaced by log_widget
            status=self._status,
            state=self._state,
            tailer=self._tailer,
            stop_callback=self._stop_tailing,
            log_widget=effective_log_widget,
        )

        # Rebuild log with new filters applied to stored entries
        if needs_rebuild:
            self._rebuild_log()

        # Highlight changes need cache reset and rebuild to re-render with new styles
        if needs_highlight_rebuild:
            from pgtail_py.tail_rich import reset_highlighter_chain

            reset_highlighter_chain()
            self._rebuild_log()
            # Show feedback after rebuild so it's not erased
            subcommand = args[0].lower()
            if subcommand == "add" and len(args) >= 2:
                log_widget.write_line(f"[green]Added highlighter '{args[1]}'[/green]")
            elif subcommand == "remove" and len(args) >= 2:
                log_widget.write_line(f"[green]Removed highlighter '{args[1]}'[/green]")
            elif subcommand == "enable" and len(args) >= 2:
                log_widget.write_line(f"[green]Enabled highlighter '{args[1]}'[/green]")
            elif subcommand == "disable" and len(args) >= 2:
                log_widget.write_line(f"[green]Disabled highlighter '{args[1]}'[/green]")
            elif subcommand == "on":
                log_widget.write_line("[green]Highlighting enabled[/green]")
            elif subcommand == "off":
                log_widget.write_line("[yellow]Highlighting disabled[/yellow]")

        # Set highlighting.duration.* changes need cache reset and rebuild
        if needs_set_highlight_rebuild:
            from pgtail_py.tail_rich import reset_highlighter_chain

            reset_highlighter_chain()
            self._rebuild_log()
            # Show feedback after rebuild so it's not erased
            key = args[0]
            value = args[1] if len(args) > 1 else ""
            log_widget.write_line(
                f"[green]Set[/green] [cyan]{key}[/cyan] = [magenta]{value}[/magenta]"
            )

        self._update_status()
