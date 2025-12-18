"""REPL loop and application state for pgtail."""

import contextlib
import threading
from dataclasses import dataclass, field
from pathlib import Path

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings

from pgtail_py.cli_config import (
    config_command,
    enable_logging_command,
    set_command,
    unset_command,
)
from pgtail_py.cli_connections import connections_command
from pgtail_py.cli_core import (
    clear_command,
    display_command,
    help_command,
    list_command,
    output_command,
    refresh_command,
    stop_command,
    tail_command,
)
from pgtail_py.cli_errors import errors_command
from pgtail_py.cli_export import export_command, pipe_command
from pgtail_py.cli_filter import filter_command, highlight_command, levels_command
from pgtail_py.cli_slow import slow_command, stats_command
from pgtail_py.cli_time import between_command, since_command, until_command
from pgtail_py.cli_utils import run_shell, warn
from pgtail_py.colors import (
    LOG_STYLE,
    format_log_entry_with_highlights,
    format_slow_query_entry,
)
from pgtail_py.commands import PgtailCompleter
from pgtail_py.config import (
    ConfigSchema,
    ensure_history_dir,
    get_history_path,
    load_config,
)
from pgtail_py.connection_stats import ConnectionStats
from pgtail_py.detector import detect_all
from pgtail_py.display import DisplayState, OutputFormat, format_entry
from pgtail_py.error_stats import ErrorStats
from pgtail_py.field_filter import FieldFilterState
from pgtail_py.filter import LogLevel
from pgtail_py.instance import Instance
from pgtail_py.notifier import create_notifier
from pgtail_py.notify import NotificationConfig, NotificationManager, NotificationRule, QuietHours
from pgtail_py.regex_filter import FilterState
from pgtail_py.slow_query import DurationStats, SlowQueryConfig, extract_duration
from pgtail_py.tailer import LogTailer
from pgtail_py.terminal import enable_vt100_mode
from pgtail_py.time_filter import TimeFilter


@dataclass
class AppState:
    """Runtime state for the REPL session.

    Attributes:
        instances: List of detected PostgreSQL instances
        current_instance: Currently selected instance for tailing
        active_levels: Set of log levels to display (all by default)
        regex_state: Regex pattern filter state
        field_filter: Field-based filter state for structured logs
        time_filter: Time-based filter state
        slow_query_config: Configuration for slow query highlighting
        duration_stats: Session-scoped query duration statistics
        error_stats: Session-scoped error statistics
        connection_stats: Session-scoped connection statistics
        notification_manager: Desktop notification coordinator
        tailing: Whether actively tailing a log file
        history_path: Path to command history file
        tailer: Active log tailer instance
        stop_event: Event to signal tail stop
        shell_mode: Whether in shell mode (next input runs as shell command)
        config: Loaded configuration from config file
        display_state: Display and output format settings
    """

    instances: list[Instance] = field(default_factory=list)
    current_instance: Instance | None = None
    active_levels: set[LogLevel] | None = field(default_factory=LogLevel.all_levels)
    regex_state: FilterState = field(default_factory=FilterState.empty)
    field_filter: FieldFilterState = field(default_factory=FieldFilterState)
    time_filter: TimeFilter = field(default_factory=TimeFilter.empty)
    slow_query_config: SlowQueryConfig = field(default_factory=SlowQueryConfig)
    duration_stats: DurationStats = field(default_factory=DurationStats)
    error_stats: ErrorStats = field(default_factory=ErrorStats)
    connection_stats: ConnectionStats = field(default_factory=ConnectionStats)
    notification_manager: NotificationManager | None = None
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)
    tailer: LogTailer | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    shell_mode: bool = False
    config: ConfigSchema = field(default_factory=ConfigSchema)
    display_state: DisplayState = field(default_factory=DisplayState)

    def __post_init__(self) -> None:
        """Load config and apply settings after initialization."""
        self.config = load_config(warn_func=warn)
        self._apply_config()
        self._init_notification_manager()

    def _apply_config(self) -> None:
        """Apply configuration settings to state."""
        # Apply default.levels if configured
        if self.config.default.levels:
            valid_levels: set[LogLevel] = set()
            for level_name in self.config.default.levels:
                with contextlib.suppress(ValueError):
                    valid_levels.add(LogLevel.from_string(level_name))
            if valid_levels:
                self.active_levels = valid_levels

        # Apply slow.* thresholds
        self.slow_query_config = SlowQueryConfig(
            enabled=True,
            warning_ms=self.config.slow.warn,
            slow_ms=self.config.slow.error,
            critical_ms=self.config.slow.critical,
        )

    def _init_notification_manager(self) -> None:
        """Initialize notification manager from config."""
        notifier = create_notifier()
        notify_config = NotificationConfig(enabled=self.config.notifications.enabled)

        # Apply level rules from config
        if self.config.notifications.levels:
            levels: set[LogLevel] = set()
            for level_name in self.config.notifications.levels:
                with contextlib.suppress(ValueError):
                    levels.add(LogLevel.from_string(level_name))
            if levels:
                notify_config.add_rule(NotificationRule.level_rule(levels))

        # Apply pattern rules from config
        for pattern_str in self.config.notifications.patterns:
            case_sensitive = True
            regex_str = pattern_str
            # Parse /pattern/ or /pattern/i syntax
            if pattern_str.startswith("/"):
                if pattern_str.endswith("/i"):
                    regex_str = pattern_str[1:-2]
                    case_sensitive = False
                elif pattern_str.endswith("/"):
                    regex_str = pattern_str[1:-1]
            with contextlib.suppress(Exception):
                notify_config.add_rule(NotificationRule.pattern_rule(regex_str, case_sensitive))

        # Apply error rate threshold
        if self.config.notifications.error_rate:
            notify_config.add_rule(NotificationRule.error_rate_rule(self.config.notifications.error_rate))

        # Apply slow query threshold
        if self.config.notifications.slow_query_ms:
            notify_config.add_rule(NotificationRule.slow_query_rule(self.config.notifications.slow_query_ms))

        # Apply quiet hours
        if self.config.notifications.quiet_hours:
            with contextlib.suppress(ValueError):
                notify_config.quiet_hours = QuietHours.from_string(self.config.notifications.quiet_hours)

        self.notification_manager = NotificationManager(
            notifier=notifier,
            config=notify_config,
            error_stats=self.error_stats,
        )


def handle_command(state: AppState, line: str) -> bool:
    """Process a command line and execute the appropriate handler.

    Args:
        state: Current application state.
        line: The command line to process.

    Returns:
        True to continue the REPL loop, False to exit.
    """
    line = line.strip()

    # Handle empty input
    if not line:
        state.shell_mode = False
        return True

    # Handle shell mode
    if state.shell_mode:
        state.shell_mode = False
        run_shell(line)
        return True

    # Handle ! prefix for shell commands
    if line.startswith("!"):
        cmd_line = line[1:].strip()
        if cmd_line:
            # !command - run immediately
            run_shell(cmd_line)
        else:
            # ! alone - enter shell mode
            state.shell_mode = True
        return True

    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in ("quit", "exit", "q"):
        # Stop tailing before exit
        if state.tailing:
            stop_command(state)
        return False
    elif cmd == "list":
        list_command(state)
    elif cmd == "help":
        help_command()
    elif cmd == "clear":
        clear_command()
    elif cmd == "refresh":
        refresh_command(state)
    elif cmd == "tail":
        tail_command(state, args)
    elif cmd == "levels":
        levels_command(state, args)
    elif cmd == "filter":
        filter_command(state, args)
    elif cmd == "highlight":
        highlight_command(state, args)
    elif cmd == "slow":
        slow_command(state, args)
    elif cmd == "stats":
        stats_command(state)
    elif cmd == "errors":
        errors_command(state, args)
    elif cmd == "connections":
        connections_command(state, args)
    elif cmd == "set":
        set_command(state, args)
    elif cmd == "unset":
        unset_command(state, args)
    elif cmd == "config":
        config_command(state, args)
    elif cmd == "stop":
        stop_command(state)
    elif cmd == "enable-logging":
        enable_logging_command(state, args)
    elif cmd == "export":
        export_command(state, args)
    elif cmd == "pipe":
        pipe_command(state, args)
    elif cmd == "since":
        since_command(state, args)
    elif cmd == "between":
        between_command(state, args)
    elif cmd == "until":
        until_command(state, args)
    elif cmd == "display":
        display_command(state, args)
    elif cmd == "output":
        output_command(state, args)
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands.")

    return True


def _get_prompt(state: AppState) -> HTML:
    """Get the prompt string based on current state."""
    if state.shell_mode:
        return HTML("<style fg='#ff6688'>!</style> ")
    if state.tailing and state.current_instance:
        return HTML(
            f"<style fg='#00aa00'>tailing</style> <style fg='#00aaaa'>[{state.current_instance.id}]</style><style fg='#666666'>&gt;</style> "
        )
    return HTML("<style fg='#00aa00'>pgtail</style><style fg='#666666'>&gt;</style> ")


def _process_tail_output(state: AppState) -> None:
    """Process pending tail output and print entries."""
    if not state.tailer:
        return

    # Process all available entries
    while True:
        entry = state.tailer.get_entry(timeout=0.01)
        if entry is None:
            break

        # Extract duration for slow query detection and stats collection
        duration_ms = extract_duration(entry.message)

        # Collect duration stats
        if duration_ms is not None:
            state.duration_stats.add(duration_ms)

        # JSON output mode - no colors or special formatting
        if state.display_state.output_format == OutputFormat.JSON:
            formatted = format_entry(entry, state.display_state)
            print(formatted)
            continue

        # Check for slow query highlighting first (slow query takes precedence)
        if state.slow_query_config.enabled and duration_ms is not None:
            slow_level = state.slow_query_config.get_level(duration_ms)
            if slow_level is not None:
                # Slow query highlighting completely replaces regex highlighting
                formatted = format_slow_query_entry(entry, slow_level)
                print_formatted_text(formatted, style=LOG_STYLE)
                continue

        # Fall back to regex highlighting (only in COMPACT mode)
        if state.regex_state.has_highlights():
            # Collect all highlight spans from all highlight patterns
            all_spans: list[tuple[int, int]] = []
            for h in state.regex_state.highlights:
                all_spans.extend(h.find_spans(entry.message))

            if all_spans:
                formatted = format_log_entry_with_highlights(entry, all_spans)
                print_formatted_text(formatted, style=LOG_STYLE)
                continue

        # Use display module formatting (compact, full, or custom mode)
        formatted = format_entry(entry, state.display_state)
        print_formatted_text(formatted, style=LOG_STYLE)


def _create_key_bindings(state: AppState) -> KeyBindings:
    """Create key bindings for the REPL.

    Args:
        state: Application state (captured in closure).

    Returns:
        KeyBindings instance with shell mode handling.
    """
    bindings = KeyBindings()

    @bindings.add("!")
    def handle_exclamation(event: object) -> None:
        """Handle ! key - enter shell mode if buffer is empty."""
        app = event.app  # type: ignore[attr-defined]
        buf = app.current_buffer
        if buf.text == "":
            state.shell_mode = True
            app.invalidate()  # Force prompt refresh
        else:
            buf.insert_text("!")

    @bindings.add("escape")
    def handle_escape(event: object) -> None:
        """Handle Escape key - exit shell mode."""
        state.shell_mode = False
        event.app.invalidate()  # type: ignore[attr-defined]

    @bindings.add("backspace")
    def handle_backspace(event: object) -> None:
        """Handle Backspace - exit shell mode if buffer empty."""
        app = event.app  # type: ignore[attr-defined]
        buf = app.current_buffer
        if state.shell_mode and buf.text == "":
            state.shell_mode = False
            app.invalidate()  # Force prompt refresh
        elif buf.text:
            buf.delete_before_cursor(1)

    return bindings


def main() -> None:
    """Main entry point for pgtail."""
    # Enable VT100 mode for colors on Windows
    enable_vt100_mode()

    print("pgtail - PostgreSQL log tailer")
    print()

    # Initialize state with detected instances
    state = AppState()
    state.instances = detect_all()

    # Show instance count on startup
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found. Use 'refresh' to scan again.")
    elif count == 1:
        print("Found 1 PostgreSQL instance. Type 'list' to see details.")
    else:
        print(f"Found {count} PostgreSQL instances. Type 'list' to see details.")

    print("Type 'help' for available commands, 'quit' to exit.")
    print()

    # Set up prompt session with history, key bindings, and completer
    history_path = ensure_history_dir()
    bindings = _create_key_bindings(state)
    completer = PgtailCompleter(get_instances=lambda: state.instances)
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        completer=completer,
    )

    # REPL loop
    while True:
        try:
            # When tailing, process output in a loop until Ctrl+C
            if state.tailing:
                try:
                    while state.tailing:
                        _process_tail_output(state)
                except KeyboardInterrupt:
                    # Ctrl+C stops tailing
                    print()
                    stop_command(state)
                    continue

            line = session.prompt(lambda: _get_prompt(state))
            if not handle_command(state, line):
                break
        except KeyboardInterrupt:
            # Ctrl+C - if tailing, stop; otherwise ignore
            print()
            if state.tailing:
                stop_command(state)
            continue
        except EOFError:
            # Ctrl+D - exit
            print()
            if state.tailing:
                stop_command(state)
            break

    print("Goodbye!")
