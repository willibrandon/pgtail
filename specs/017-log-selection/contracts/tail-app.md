# Contract: TailApp Application

**Component**: `pgtail_py/tail_textual.py`
**Type**: Textual Application
**Date**: 2025-12-31

## Overview

TailApp is the main Textual Application that coordinates log display, command input, status bar, and log streaming from the existing LogTailer.

---

## Interface

### Class Definition

```python
class TailApp(App[None]):
    """Textual-based tail mode with selection support."""

    ALLOW_SELECT: ClassVar[bool] = True

    CSS: ClassVar[str] = """
    TailLog {
        height: 1fr;
    }
    #status {
        height: 1;
        background: $surface-darken-1;
    }
    Input {
        dock: bottom;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "focus_input", "Command", show=False),
        Binding("tab", "toggle_focus", "Toggle focus", show=False),
    ]
```

### Constructor

```python
def __init__(
    self,
    state: AppState,
    instance: Instance,
    log_path: Path,
    max_lines: int = 10000,
) -> None:
    """Initialize TailApp.

    Args:
        state: pgtail AppState with filter settings
        instance: PostgreSQL instance being tailed
        log_path: Path to the log file
        max_lines: Maximum lines to buffer (default 10,000)
    """
```

### Class Method Entry Point

```python
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
        state: pgtail AppState with filter settings
        instance: PostgreSQL instance being tailed
        log_path: Path to the log file
    """
```

---

## Composition

### compose() Widgets

```python
def compose(self) -> ComposeResult:
    yield TailLog(max_lines=self._max_lines, auto_scroll=True, id="log")
    yield Static(id="status")
    yield Input(placeholder="tail> ", id="input")
```

### Widget IDs

| ID | Widget Type | Purpose |
|----|-------------|---------|
| `#log` | `TailLog` | Log display area |
| `#status` | `Static` | Status bar |
| `#input` | `Input` | Command input |

---

## Actions

| Action | Method | Trigger |
|--------|--------|---------|
| `quit` | `action_quit()` | `q` key |
| `focus_input` | `action_focus_input()` | `/` key |
| `toggle_focus` | `action_toggle_focus()` | `Tab` key |

### action_quit

```python
def action_quit(self) -> None:
    """Exit tail mode and return to REPL."""
    self._running = False
    self.exit()
```

### action_focus_input

```python
def action_focus_input(self) -> None:
    """Focus the command input."""
    self.query_one("#input", Input).focus()
```

### action_toggle_focus

```python
def action_toggle_focus(self) -> None:
    """Toggle focus between log and input."""
    input_widget = self.query_one("#input", Input)
    log_widget = self.query_one("#log", TailLog)
    if input_widget.has_focus:
        log_widget.focus()
    else:
        input_widget.focus()
```

---

## Event Handlers

### on_mount

```python
def on_mount(self) -> None:
    """Called when app is mounted."""
    # Start log tailer
    self._tailer.start()
    # Start background consumer
    self._start_consumer()
    # Set initial status
    self._update_status()
```

### on_unmount

```python
def on_unmount(self) -> None:
    """Called when app is unmounting."""
    self._running = False
    if self._tailer:
        self._tailer.stop()
```

### on_input_submitted

```python
@on(Input.Submitted)
def on_input_submitted(self, event: Input.Submitted) -> None:
    """Handle command input submission."""
    command = event.value.strip()
    event.input.value = ""
    if command:
        self._handle_command(command)
    # Return focus to log
    self.query_one("#log", TailLog).focus()
```

---

## Background Worker

### _start_consumer

```python
@work(exclusive=True)
async def _start_consumer(self) -> None:
    """Background worker consuming log entries."""
    while self._running:
        entry = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._tailer.get_entry(timeout=0.05)
        )
        if entry:
            self.call_from_thread(self._add_entry, entry)
        await asyncio.sleep(0.01)
```

### _add_entry

```python
def _add_entry(self, entry: LogEntry) -> None:
    """Add a log entry to the display (called from worker thread)."""
    log = self.query_one("#log", TailLog)

    # Format entry
    formatted = format_entry_compact(entry)

    # Add to log
    was_at_end = log.is_vertical_scroll_end
    log.write_line(formatted)

    # Update status counts
    if self._status:
        self._status.update_from_entry(entry)
        self._status.set_total_lines(log.line_count)
        self._status.set_follow_mode(was_at_end, 0 if was_at_end else self._status.new_since_pause + 1)
        self._update_status()

    # Update stats
    if self._state:
        self._state.error_stats.add(entry)
        self._state.connection_stats.add(entry)
```

---

## Command Handling

### _handle_command

```python
def _handle_command(self, command_text: str) -> None:
    """Handle a command entered in the input line."""
    from pgtail_py.cli_tail import handle_tail_command

    parts = command_text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower()
    args = parts[1:]

    handle_tail_command(
        cmd=cmd,
        args=args,
        buffer=None,  # Replaced by TailLog
        status=self._status,
        state=self._state,
        tailer=self._tailer,
        stop_callback=self.action_quit,
        log_widget=self.query_one("#log", TailLog),  # New parameter
    )

    self._update_status()
```

---

## Status Updates

### _update_status

```python
def _update_status(self) -> None:
    """Update the status bar display."""
    status_widget = self.query_one("#status", Static)
    if self._status:
        # Format status line
        status_text = self._status.format_plain()
        status_widget.update(status_text)
```

---

## Behavior Contracts

### B1: Application Startup

**Precondition**: Valid state, instance, and log_path provided
**Trigger**: `TailApp.run_tail_mode()` called
**Postcondition**:
- LogTailer created and started
- Background consumer worker running
- TailLog visible with initial empty state
- Status bar shows instance info
- Input focused by default

### B2: Log Entry Display

**Precondition**: App running, tailer producing entries
**Trigger**: Entry available in tailer queue
**Postcondition**:
- Entry formatted and added to TailLog
- Status bar counts updated
- ErrorStats/ConnectionStats updated
- Auto-scroll if was at bottom

### B3: Command Execution

**Precondition**: App running, user enters command
**Trigger**: Enter key in input
**Postcondition**:
- Command parsed and dispatched to handler
- Status bar updated
- Input cleared
- Focus returns to log

### B4: Focus Toggle

**Precondition**: App running
**Trigger**: Tab key
**Postcondition**: Focus alternates between log and input

### B5: Quit

**Precondition**: App running
**Trigger**: `q` key
**Postcondition**:
- `_running` set to False
- Tailer stopped
- Consumer worker cancelled
- App exits
- Control returns to REPL

---

## Error Handling

| Error Case | Behavior |
|------------|----------|
| Tailer fails to start | Log error, exit gracefully |
| Entry formatting fails | Skip entry, continue |
| Command handler raises | Log error, show in status |
| Worker exception | Log error, attempt restart |
