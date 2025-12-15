"""REPL loop and command handlers for pgtail."""

import os
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory

from pgtail_py.colors import print_log_entry
from pgtail_py.config import ensure_history_dir, get_history_path
from pgtail_py.detector import detect_all
from pgtail_py.filter import LogLevel
from pgtail_py.instance import Instance
from pgtail_py.tailer import LogTailer


@dataclass
class AppState:
    """Runtime state for the REPL session.

    Attributes:
        instances: List of detected PostgreSQL instances
        current_instance: Currently selected instance for tailing
        active_levels: Set of log levels to display (all by default)
        tailing: Whether actively tailing a log file
        history_path: Path to command history file
        tailer: Active log tailer instance
        stop_event: Event to signal tail stop
    """

    instances: list[Instance] = field(default_factory=list)
    current_instance: Instance | None = None
    active_levels: set[LogLevel] = field(default_factory=LogLevel.all_levels)
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)
    tailer: LogTailer | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)


def _shorten_path(path: Path) -> str:
    """Replace home directory with ~ for display."""
    home = Path.home()
    path_str = str(path)
    home_str = str(home)
    if path_str.startswith(home_str):
        return "~" + path_str[len(home_str):]
    return path_str


def format_instances_table(instances: list[Instance]) -> str:
    """Format instances as an aligned table.

    Args:
        instances: List of instances to format.

    Returns:
        Formatted table string matching Go version format.
    """
    if not instances:
        return """No PostgreSQL instances found.

Suggestions:
  - Start a PostgreSQL instance
  - Set PGDATA environment variable to your data directory
  - Run 'refresh' after starting PostgreSQL
  - Check ~/.pgrx/ for pgrx development instances"""

    # Header matches Go version: #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
    lines = ["  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY"]
    for inst in instances:
        data_dir = _shorten_path(inst.data_dir)
        source = inst.source.value  # process, pgrx, pgdata, known
        lines.append(
            f"  {inst.id}  {inst.version:<8} {inst.port_str:<6} {inst.status_str:<8} "
            f"{inst.log_status:<4} {source:<7} {data_dir}"
        )

    return "\n".join(lines)


def list_command(state: AppState) -> None:
    """Handle the 'list' command - show detected instances."""
    print(format_instances_table(state.instances))


def help_command() -> None:
    """Handle the 'help' command - show available commands."""
    help_text = """
Available commands:
  list              Show detected PostgreSQL instances
  tail <id|path>    Tail logs for an instance (by ID or data directory path)
  levels [LEVEL...] Set log level filter (e.g., 'levels ERROR WARNING')
                    With no args, shows current filter settings
                    Use 'levels ALL' to show all levels
  stop              Stop current tail and return to prompt
  refresh           Re-scan for PostgreSQL instances
  enable-logging <id>  Enable logging_collector for an instance
  clear             Clear the screen
  help              Show this help message
  quit / exit       Exit pgtail

Keyboard shortcuts:
  Tab       Autocomplete commands and arguments
  Up/Down   Navigate command history
  Ctrl+C    Stop current tail
  Ctrl+D    Exit pgtail
"""
    print(help_text.strip())


def clear_command() -> None:
    """Handle the 'clear' command - clear terminal screen."""
    os.system("cls" if sys.platform == "win32" else "clear")


def refresh_command(state: AppState) -> None:
    """Handle the 'refresh' command - re-scan for instances."""
    print("Scanning for PostgreSQL instances...")
    state.instances = detect_all()
    count = len(state.instances)
    if count == 0:
        print("No PostgreSQL instances found.")
    elif count == 1:
        print("Found 1 PostgreSQL instance.")
    else:
        print(f"Found {count} PostgreSQL instances.")


def _find_instance(state: AppState, arg: str) -> Instance | None:
    """Find an instance by ID or path.

    Args:
        state: Current application state.
        arg: Instance ID (number) or data directory path.

    Returns:
        Instance if found, None otherwise.
    """
    # Try as numeric ID first
    try:
        instance_id = int(arg)
        for inst in state.instances:
            if inst.id == instance_id:
                return inst
        return None
    except ValueError:
        pass

    # Try as path
    path = Path(arg).resolve()
    for inst in state.instances:
        if inst.data_dir.resolve() == path:
            return inst

    return None


def tail_command(state: AppState, args: list[str]) -> None:
    """Handle the 'tail' command - tail logs for an instance.

    Args:
        state: Current application state.
        args: Command arguments (instance ID or path).
    """
    if not args:
        # If no arg given, use first instance or show error
        if not state.instances:
            print("No instances detected. Run 'refresh' to scan.")
            return
        if len(state.instances) == 1:
            instance = state.instances[0]
        else:
            print("Multiple instances found. Specify an ID:")
            print("  tail <id>")
            print()
            list_command(state)
            return
    else:
        instance = _find_instance(state, args[0])
        if instance is None:
            print(f"Instance not found: {args[0]}")
            print()
            print("Available instances:")
            for inst in state.instances:
                print(f"  {inst.id}: {inst.data_dir}")
            return

    if not instance.log_path:
        print(f"Logging not enabled for instance {instance.id}")
        print(f"Data directory: {instance.data_dir}")
        print()
        print("Enable logging with: enable-logging {instance.id}")
        return

    if not instance.log_path.exists():
        print(f"Log file not found: {instance.log_path}")
        return

    # Start tailing
    state.current_instance = instance
    state.tailing = True
    state.stop_event.clear()

    print(f"Tailing {instance.log_path}")
    print("Press Ctrl+C to stop")
    print()

    state.tailer = LogTailer(instance.log_path, state.active_levels)
    state.tailer.start()


def stop_command(state: AppState) -> None:
    """Handle the 'stop' command - stop tailing."""
    if not state.tailing:
        print("Not currently tailing.")
        return

    if state.tailer:
        state.tailer.stop()
        state.tailer = None

    state.tailing = False
    state.stop_event.set()
    state.current_instance = None
    print("Stopped tailing.")


def handle_command(state: AppState, line: str) -> bool:
    """Process a command line and execute the appropriate handler.

    Args:
        state: Current application state.
        line: The command line to process.

    Returns:
        True to continue the REPL loop, False to exit.
    """
    parts = line.strip().split()
    if not parts:
        return True

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
        print("Levels command not yet implemented. Coming in Phase 5.")
    elif cmd == "stop":
        stop_command(state)
    elif cmd == "enable-logging":
        print("Enable-logging command not yet implemented. Coming in Phase 7.")
    else:
        print(f"Unknown command: {cmd}")
        print("Type 'help' for available commands.")

    return True


def _get_prompt(state: AppState) -> HTML:
    """Get the prompt string based on current state."""
    if state.tailing and state.current_instance:
        return HTML(f"<style fg='#00aa00'>tailing</style> <style fg='#00aaaa'>[{state.current_instance.id}]</style><style fg='#666666'>&gt;</style> ")
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
        print_log_entry(entry)


def main() -> None:
    """Main entry point for pgtail."""
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

    # Set up prompt session with history
    history_path = ensure_history_dir()
    session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
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

            line = session.prompt(_get_prompt(state))
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
