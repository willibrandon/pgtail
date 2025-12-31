# Feature: Log Entry Selection and Copy

## Problem

When tailing logs in pgtail's status bar mode, users cannot easily copy log entries:
- No way to select text within the log output area
- Shift-click selection in terminal is awkward and imprecise
- Multi-line log entries (stack traces, DETAIL fields) are hard to capture
- Need to exit tail mode and re-run with `--stream` to get copyable output
- DBAs troubleshooting need to share exact log content with developers

The current prompt_toolkit-based `FormattedTextControl` is display-only with no selection support. Multiple attempts to add selection via `BufferControl` have failed.

## Proposed Solution

Replace the tail mode UI with **Textual** (`/Users/brandon/src/textual`), a modern Python TUI framework with built-in selection and clipboard support.

Textual provides:
- **Log widget**: Built-in selection via `ALLOW_SELECT = True` - already works
- **Mouse selection**: Click and drag to select text - native support
- **Clipboard integration**: `app.copy_to_clipboard()` via OSC 52 escape sequence
- **Auto-scroll**: `auto_scroll=True` for follow mode
- **Max lines**: `max_lines=N` for buffer management
- **Rich rendering**: Full Rich text styling support
- **Custom key bindings**: Easy to add vim-style navigation

## Reference Implementation

### Textual Log Widget (`/Users/brandon/src/textual/src/textual/widgets/_log.py`)

The Log widget already has everything needed:

```python
class Log(ScrollView, can_focus=True):
    ALLOW_SELECT = True  # <-- Built-in selection!

    max_lines: var[int | None] = var[Optional[int]](None)
    auto_scroll: var[bool] = var(True)

    def get_selection(self, selection: Selection) -> tuple[str, str] | None:
        """Get the text under the selection."""
        text = "\n".join(self._lines)
        return selection.extract(text), "\n"

    def write(self, data: str, scroll_end: bool | None = None) -> Self:
        """Write text to log, handles line continuations."""
        # Splits on \r\n, \r, \n via line_split()
        # Respects auto_scroll and is_vertical_scroll_end
        ...

    def write_line(self, line: str, scroll_end: bool | None = None) -> Self:
        """Convenience for single line."""
        return self.write_lines([line], scroll_end)

    def write_lines(self, lines: Iterable[str], scroll_end: bool | None = None) -> Self:
        """Batch writes with optimization."""
        # Only scrolls if auto_scroll=True AND not scrollbar_grabbed AND was_at_end
        ...
```

### Textual Clipboard (`/Users/brandon/src/textual/src/textual/app.py:1671`)

```python
def copy_to_clipboard(self, text: str) -> None:
    """Copy text to the clipboard via OSC 52."""
    self._clipboard = text  # In-memory fallback always available
    if self._driver is None:
        return
    import base64
    base64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    self._driver.write(f"\x1b]52;c;{base64_text}\a")
```

### Textual Screen Copy Action (`/Users/brandon/src/textual/src/textual/screen.py:954`)

```python
def action_copy_text(self) -> None:
    """Copy selected text to clipboard."""
    selection = self.get_selected_text()
    if selection is None:
        raise SkipAction()
    self.app.copy_to_clipboard(selection)
```

### Selection System (Three-Level Hierarchy)

Selection requires all three levels to be enabled:

```python
# Level 1: App level
class App:
    ALLOW_SELECT: ClassVar[bool] = True

# Level 2: Screen level
class Screen:
    @property
    def allow_select(self) -> bool:
        return self.ALLOW_SELECT

# Level 3: Widget level
class Widget:
    ALLOW_SELECT: ClassVar[bool] = True

    @property
    def allow_select(self) -> bool:
        return self.ALLOW_SELECT and not self.is_container
```

## User Scenarios

### Scenario 1: Select and Copy Error Details
DBA sees an error, needs to send exact message to developer:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 17:27:45.102 [78324] ERROR  23505: duplicate key value violates unique  │
│   DETAIL: Key (email)=(foo@bar.com) already exists.                     │
│   STATEMENT: INSERT INTO users (email, name) VALUES ($1, $2)            │
│ ████████████████████████████████████████████████  <- SELECTED           │
│ 17:27:45.200 [78324] LOG    : statement: SELECT * FROM accounts...      │
├─────────────────────────────────────────────────────────────────────────┤
│ FOLLOW | E:1 W:0 | 847 lines                                            │
├─────────────────────────────────────────────────────────────────────────┤
│ tail>                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```
User drags mouse to select text, releases. Text copied to system clipboard automatically.

### Scenario 2: Keyboard Copy
After selecting with mouse, press `Ctrl+C` to explicitly copy.

### Scenario 3: Select All
Press `Ctrl+A` to select all visible log content for bulk copy.

### Scenario 4: Vim-Style Navigation
Power user navigates logs efficiently:
- Press `j`/`k` to scroll line by line
- Press `Ctrl+D`/`Ctrl+U` for half-page jumps
- Press `G` to jump to bottom and resume follow mode
- Press `g` to jump to top to review old entries

### Scenario 5: Vim Visual Mode Selection
User selects text without mouse:
- Press `v` to enter visual mode at current line
- Navigate with `j`/`k` to extend selection
- Press `y` to yank (copy) to clipboard
- Press `Escape` to cancel selection

## Keyboard Shortcuts

### Navigation (Vim-Style + Standard)

| Key | Action |
|-----|--------|
| `j` / `Down` | Scroll down one line |
| `k` / `Up` | Scroll up one line |
| `Ctrl+D` | Scroll down half page |
| `Ctrl+U` | Scroll up half page |
| `Ctrl+F` / `PageDown` | Scroll down full page |
| `Ctrl+B` / `PageUp` | Scroll up full page |
| `g` / `Home` | Jump to top |
| `G` / `End` | Jump to bottom (resume FOLLOW mode) |

### Selection and Copy

| Key | Action |
|-----|--------|
| Mouse drag | Select text |
| `v` | Enter visual mode (keyboard selection) |
| `V` | Enter visual line mode (select full lines) |
| `y` | Yank (copy) selection to clipboard |
| `Ctrl+C` | Copy selection to clipboard |
| `Ctrl+A` | Select all |
| `Escape` | Clear selection / exit visual mode |

### Application

| Key | Action |
|-----|--------|
| `q` | Quit tail mode |
| `Tab` | Switch focus between log and input |
| `/` | Focus command input |

## Architecture

### Current State (prompt_toolkit)
```
TailBuffer (deque of FormattedLogEntry)
    ↓
get_visible_lines() → FormattedText
    ↓
ScrollableFormattedTextControl (display only, NO selection)
    ↓
prompt_toolkit Application
```

### Proposed State (Textual)
```
TailBuffer (deque of FormattedLogEntry)
    ↓
format_as_rich_text() → Rich Text objects
    ↓
TailLog widget (custom Log subclass with vim bindings)
    ↓
Textual Application (built-in clipboard via OSC 52)
```

## Technical Design

### New Files

```
pgtail_py/
├── tail_textual.py      # TailApp - main Textual application
├── tail_log.py          # TailLog - custom Log subclass with vim bindings
├── tail_input.py        # TailInput - command input handler
└── tail_rich.py         # Rich text formatting for log entries
```

### Modified Files

```
pgtail_py/
├── cli.py               # Switch to Textual app for tail mode
├── tail_buffer.py       # Add format_as_rich_text() method
└── pyproject.toml       # Add textual dependency
```

### Custom Log Widget with Vim Bindings

```python
from textual.binding import Binding
from textual.widgets import Log


class TailLog(Log):
    """Log widget with vim-style navigation and visual mode."""

    BINDINGS = [
        # Vim navigation
        Binding("j,down", "scroll_down", "Down", show=False),
        Binding("k,up", "scroll_up", "Up", show=False),
        Binding("g,home", "scroll_home", "Top", show=False),
        Binding("shift+g,end", "scroll_end", "Bottom", show=False),
        Binding("ctrl+d", "half_page_down", "Half page down", show=False),
        Binding("ctrl+u", "half_page_up", "Half page up", show=False),
        Binding("ctrl+f,pagedown", "page_down", "Page down", show=False),
        Binding("ctrl+b,pageup", "page_up", "Page up", show=False),
        # Visual mode
        Binding("v", "visual_mode", "Visual mode", show=False),
        Binding("shift+v", "visual_line_mode", "Visual line mode", show=False),
        Binding("y", "yank", "Yank selection", show=False),
        Binding("escape", "clear_selection", "Clear selection", show=False),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._visual_mode = False
        self._visual_start_line: int | None = None

    def action_half_page_down(self) -> None:
        """Scroll down by half the viewport height."""
        self.scroll_relative(y=self.scrollable_content_region.height // 2)

    def action_half_page_up(self) -> None:
        """Scroll up by half the viewport height."""
        self.scroll_relative(y=-self.scrollable_content_region.height // 2)

    def action_visual_mode(self) -> None:
        """Enter visual mode for keyboard selection."""
        self._visual_mode = True
        self._visual_start_line = self.scroll_offset.y
        self._update_visual_selection()

    def action_visual_line_mode(self) -> None:
        """Enter visual line mode (select full lines)."""
        self._visual_mode = True
        self._visual_start_line = self.scroll_offset.y
        self._update_visual_selection(full_lines=True)

    def action_yank(self) -> None:
        """Copy current selection to clipboard."""
        selection = self.screen.selections.get(self)
        if selection is not None:
            result = self.get_selection(selection)
            if result is not None:
                text, _ = result
                self._copy_with_fallback(text)
        self.action_clear_selection()

    def action_clear_selection(self) -> None:
        """Clear selection and exit visual mode."""
        self._visual_mode = False
        self._visual_start_line = None
        self.screen.clear_selection()

    def _copy_with_fallback(self, text: str) -> None:
        """Copy to clipboard with pyperclip fallback."""
        self.app.copy_to_clipboard(text)
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            pass

    def _update_visual_selection(self, full_lines: bool = False) -> None:
        """Update selection based on visual mode state."""
        if not self._visual_mode or self._visual_start_line is None:
            return
        from textual.geometry import Offset
        from textual.selection import Selection

        current_line = self.scroll_offset.y
        start_line = min(self._visual_start_line, current_line)
        end_line = max(self._visual_start_line, current_line)

        if full_lines:
            start = Offset(0, start_line)
            end = Offset(-1, end_line)  # -1 means end of line
        else:
            start = Offset(0, start_line)
            end = Offset(-1, end_line)

        self.screen.selections = {self: Selection(start, end)}
```

### Textual Tail App

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input, Footer
from textual.containers import Vertical
from textual import on

from .tail_log import TailLog


class TailApp(App):
    """Textual-based tail mode with selection support."""

    CSS = """
    TailLog {
        height: 1fr;
    }
    Input {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "focus_input", "Command", show=False),
    ]

    def __init__(self, max_lines: int = 10000):
        super().__init__()
        self._max_lines = max_lines

    def compose(self) -> ComposeResult:
        yield TailLog(max_lines=self._max_lines, auto_scroll=True, id="log")
        yield Input(placeholder="tail> ", id="input")
        yield Footer()

    def action_focus_input(self) -> None:
        """Focus the command input."""
        self.query_one("#input", Input).focus()

    @on(Input.Submitted)
    def handle_command(self, event: Input.Submitted) -> None:
        """Handle command input."""
        command = event.value.strip()
        event.input.value = ""
        if command:
            self.process_command(command)

    def process_command(self, command: str) -> None:
        """Process a tail mode command."""
        # Delegate to command handlers
        ...

    def add_log_entry(self, text: str) -> None:
        """Add a log entry (called from async log consumer)."""
        log = self.query_one("#log", TailLog)
        was_at_end = log.is_vertical_scroll_end
        log.write_line(text)
        # Only auto-scroll if was already at end (user hasn't scrolled up)
        if was_at_end:
            log.scroll_end(animate=False, x_axis=False)
```

### Log Entry Formatting

```python
from rich.text import Text

from .filter import LogLevel
from .parser import LogEntry


def format_entry_as_rich(entry: LogEntry) -> Text:
    """Convert LogEntry to Rich Text with styling."""
    text = Text()

    # Timestamp
    if entry.timestamp:
        text.append(entry.timestamp.strftime("%H:%M:%S.%f")[:-3], style="dim")
        text.append(" ")

    # PID
    if entry.pid:
        text.append(f"[{entry.pid}]", style="dim")
        text.append(" ")

    # Level with color
    level_styles = {
        LogLevel.PANIC: "bold white on red",
        LogLevel.FATAL: "bold red reverse",
        LogLevel.ERROR: "bold red",
        LogLevel.WARNING: "yellow",
        LogLevel.LOG: "green",
        LogLevel.INFO: "blue",
        LogLevel.DEBUG: "dim",
    }
    text.append(entry.level.name.ljust(7), style=level_styles.get(entry.level, ""))
    text.append(" ")

    # SQLSTATE code if present
    if entry.sql_state:
        text.append(entry.sql_state, style="cyan")
        text.append(": ")

    # Message (with SQL highlighting if detected)
    text.append(entry.message)

    # Secondary fields (DETAIL, HINT, CONTEXT, STATEMENT)
    for field_name in ("detail", "hint", "context", "statement"):
        field_value = getattr(entry, field_name, None)
        if field_value:
            text.append(f"\n  {field_name.upper()}: ", style="dim bold")
            text.append(field_value, style="dim")

    return text
```

## Terminal Compatibility

### Clipboard Support

Textual uses OSC 52 escape sequence for clipboard. Compatibility:

| Terminal | OSC 52 Support |
|----------|----------------|
| iTerm2 | ✅ Yes |
| Ghostty | ✅ Yes |
| Kitty | ✅ Yes |
| WezTerm | ✅ Yes |
| Windows Terminal | ✅ Yes |
| macOS Terminal.app | ❌ No |
| Linux xterm | ✅ Yes (if enabled) |
| tmux | ✅ Yes (with `set-clipboard on`) |

### Fallback for macOS Terminal.app

pyperclip provides native clipboard access as fallback:

```python
def _copy_with_fallback(self, text: str) -> None:
    """Copy to clipboard with pyperclip fallback."""
    # OSC 52 - works on modern terminals
    self.app.copy_to_clipboard(text)

    # pyperclip fallback - uses pbcopy on macOS, xclip/xsel on Linux
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass
```

## Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    "textual>=0.89.0",
    "pyperclip>=1.8.0",  # Clipboard fallback for Terminal.app
]
```

## Scroll Behavior

### Auto-Scroll Logic

Follow mode resumes only when user explicitly scrolls to bottom:

```python
def add_log_entry(self, text: str) -> None:
    log = self.query_one("#log", TailLog)

    # Check if at bottom BEFORE adding new content
    was_at_end = log.is_vertical_scroll_end

    # Add the entry
    log.write_line(text)

    # Only auto-scroll if was already at end
    # (user hasn't scrolled up to review history)
    if was_at_end:
        log.scroll_end(animate=False, x_axis=False)
```

### Available Scroll Methods

| Method | Purpose |
|--------|---------|
| `scroll_up()` / `scroll_down()` | Single line |
| `scroll_page_up()` / `scroll_page_down()` | Full page |
| `scroll_relative(y=N)` | N lines (positive=down, negative=up) |
| `scroll_home()` / `scroll_end()` | Jump to start/end |
| `is_vertical_scroll_end` | Check if at bottom |
| `scrollable_content_region.height` | Viewport height for half-page calc |

## Edge Cases

1. **Live updates during selection**: Textual Log handles this - selection preserved
2. **Large selection**: OSC 52 has limits (~100KB), pyperclip fallback helps
3. **Filter changes**: Clear selection when content changes (via widget refresh)
4. **Focus management**: Tab switches focus between Log and Input
5. **Visual mode during scroll**: Selection updates as user navigates with j/k
6. **Double-click**: Selects word (built-in Textual behavior)
7. **Triple-click**: Selects line (built-in Textual behavior)
8. **Scrollbar grab**: Auto-scroll paused while user drags scrollbar

## Success Criteria

1. Mouse drag selects text in log area
2. Selected text copies to system clipboard
3. `Ctrl+C` explicitly copies selection
4. Auto-scroll continues when not selecting
5. SQL highlighting and level colors preserved
6. Works on iTerm2, Kitty, WezTerm, Windows Terminal
7. Graceful fallback on macOS Terminal.app (via pyperclip)
8. Vim navigation works: j/k/g/G/Ctrl+D/Ctrl+U/Ctrl+F/Ctrl+B
9. Visual mode selection works: v/V/y/Escape
10. Half-page scroll works correctly (viewport height / 2)
