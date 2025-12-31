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
        return selection.extract(text), "\n"
```

### Textual Clipboard (`/Users/brandon/src/textual/src/textual/app.py:1671`)

```python
def copy_to_clipboard(self, text: str) -> None:
    """Copy text to the clipboard via OSC 52."""
    import base64
    base64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    self._driver.write(f"\x1b]52;c;{base64_text}\a")
```

### Textual Screen Copy Action (`/Users/brandon/src/textual/src/textual/screen.py:954`)

```python
def action_copy_text(self) -> None:
    """Copy selected text to clipboard."""
    selection = self.get_selected_text()
    if selection is not None:
        self.app.copy_to_clipboard(selection)
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
After selecting with mouse, press `ctrl+c` to explicitly copy.

### Scenario 3: Select All
Press `ctrl+a` to select all visible log content for bulk copy.

## Keyboard Shortcuts

Textual provides these bindings automatically:

| Key | Action |
|-----|--------|
| Mouse drag | Select text |
| `Ctrl+C` | Copy selection to clipboard |
| `Ctrl+A` | Select all |
| `Up/Down` | Scroll |
| `PageUp/PageDown` | Page scroll |
| `Home/End` | Jump to top/bottom |

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
Textual Log widget (ALLOW_SELECT = True, built-in selection)
    ↓
Textual Application (built-in clipboard via OSC 52)
```

## Technical Design

### New Files

```
pgtail_py/
├── tail_textual.py      # Textual-based tail mode app
└── tail_widgets.py      # Custom widgets (status bar, input)
```

### Modified Files

```
pgtail_py/
├── cli.py               # Switch to Textual app for tail mode
├── tail_buffer.py       # Add format_as_rich_text() method
└── pyproject.toml       # Add textual dependency
```

### Minimal Textual Tail App

```python
from textual.app import App, ComposeResult
from textual.widgets import Log, Input, Footer
from textual.containers import Vertical

class TailApp(App):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Vertical(
            Log(max_lines=10000, auto_scroll=True, id="log"),
            Input(placeholder="tail>", id="input"),
        )
        yield Footer()

    def add_log_entry(self, text: str) -> None:
        """Add a log entry (called from async log consumer)."""
        self.query_one("#log", Log).write_line(text)
```

### Log Entry Formatting

```python
from rich.text import Text

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
        LogLevel.ERROR: "bold red",
        LogLevel.FATAL: "bold red reverse",
        LogLevel.WARNING: "yellow",
        LogLevel.LOG: "green",
    }
    text.append(entry.level.name, style=level_styles.get(entry.level, ""))
    text.append(": ")

    # Message (with SQL highlighting if detected)
    text.append(entry.message)

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

### Fallback for macOS Terminal.app

Add pyperclip as optional fallback:

```python
def copy_with_fallback(self, text: str) -> None:
    """Copy to clipboard with pyperclip fallback."""
    # Try OSC 52 first
    self.copy_to_clipboard(text)

    # Also try pyperclip for terminals that don't support OSC 52
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
    "pyperclip>=1.8.0",  # Optional clipboard fallback
]
```

## Edge Cases

1. **Live updates during selection**: Textual Log handles this - selection preserved
2. **Large selection**: OSC 52 has limits (~100KB), pyperclip fallback helps
3. **Filter changes**: Clear selection when content changes (via widget refresh)
4. **Focus management**: Textual handles focus between Log and Input widgets

## Success Criteria

1. Mouse drag selects text in log area
2. Selected text copies to system clipboard
3. `Ctrl+C` explicitly copies selection
4. Auto-scroll continues when not selecting
5. SQL highlighting and level colors preserved
6. Works on iTerm2, Kitty, WezTerm, Windows Terminal
7. Graceful fallback on macOS Terminal.app (via pyperclip)

## Out of Scope

- Vim-style visual mode (v, V) - use mouse selection instead
- Block/column selection
- Selection persistence across filter changes
