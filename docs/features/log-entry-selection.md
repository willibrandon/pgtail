# Feature: Log Entry Selection and Copy

## Problem

When tailing logs in pgtail's status bar mode, users cannot easily copy log entries:
- No way to select text within the log output area
- Shift-click selection in terminal is awkward and imprecise
- Multi-line log entries (stack traces, DETAIL fields) are hard to capture
- Need to exit tail mode and re-run with `--stream` to get copyable output
- DBAs troubleshooting need to share exact log content with developers

The current `FormattedTextControl` is display-only with no selection support.

## Proposed Solution

Replace the log display control with a read-only `BufferControl` (following pypager's architecture) to gain native text selection:

- **Native selection**: Shift+arrows, mouse drag, vim visual mode all work automatically
- **System clipboard**: Copy selected text directly to system clipboard
- **Entry-level operations**: Select entire log entries with a single keystroke
- **Preserved styling**: SQL highlighting and log level colors maintained via custom Lexer

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
│ FOLLOW | E:1 W:0 | 847 lines | SEL: 3 lines                             │
├─────────────────────────────────────────────────────────────────────────┤
│ tail>                                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```
User presses `y` to yank. Text copied to system clipboard. Paste into Slack/email.

### Scenario 2: Quick Entry Copy with V
Developer wants to copy current log entry without precise selection:
```
> [cursor on any line of the entry]
Press V → entire entry selected (all related lines)
Press y → copied to clipboard
```
Status shows "Copied 4 lines to clipboard"

### Scenario 3: Character Selection with Shift+Arrows
User needs just the SQL statement portion:
```
│   STATEMENT: INSERT INTO users (email, name) VALUES ($1, $2)            │
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ selected
```
Shift+Right extends character by character. Shift+End to end of line.

### Scenario 4: Mouse Drag Selection
Click and drag to select arbitrary text region. Works like any text editor.

### Scenario 5: Select All Visible
Press `Ctrl+A` to select all visible log content for bulk copy.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Shift+←/→` | Extend selection by character |
| `Shift+↑/↓` | Extend selection by line |
| `Shift+Home/End` | Extend selection to line boundary |
| `Ctrl+Shift+Home/End` | Extend selection to buffer boundary |
| `v` | Start character selection (vim) |
| `V` | Select entire current log entry |
| `y` | Yank (copy) selection to clipboard |
| `Escape` | Cancel selection |
| `Ctrl+A` | Select all visible content |
| `Tab` | Toggle focus between log area and command input |

## Architecture

### Current State (FormattedTextControl)
```
TailBuffer (deque of FormattedLogEntry)
    ↓
get_visible_lines() → FormattedText
    ↓
ScrollableFormattedTextControl (display only, no selection)
    ↓
Window render
```

### Proposed State (BufferControl)
```
TailBuffer (deque of FormattedLogEntry)
    ↓
get_plain_text() → str (for Buffer)
get_line_styles() → list[StyleAndTextTuples] (for Lexer)
    ↓
Buffer (read_only=True) + TailBufferLexer
    ↓
BufferControl (native selection support)
    ↓
Window render
```

### Reference Implementations

The following projects are cloned locally and should be referenced during spec, planning, and implementation phases:

#### pypager (`/Users/brandon/src/pypager/`)
Uses the exact Buffer + BufferControl pattern needed for selection:
- `Buffer(read_only=True)` for content storage
- `BufferControl` with custom `input_processors` for display
- `line_tokens[]` stores pre-formatted styling per line
- Custom `_EscapeProcessor` applies styling during render
- Streaming via `_after_render()` callback with daemon threads
- `forward_forever` flag for tail-like auto-follow

Key files:
- `pypager/pager.py:46` - `self.buffer = Buffer(read_only=True)`
- `pypager/layout.py:295-306` - BufferControl setup with lexer
- `pypager/source.py` - Streaming input patterns

#### pgcli (`/Users/brandon/src/pgcli/`)
Production-grade PostgreSQL CLI with prompt_toolkit integration:
- Buffer management patterns for SQL editing
- Clipboard integration in real-world usage
- Key binding organization and focus management

Key files:
- `pgcli/main.py` - Application setup and key bindings
- `pgcli/pgcompleter.py` - Completer patterns

#### litecli (`/Users/brandon/src/litecli/`)
Similar architecture to pgcli, useful for cross-referencing:
- Simpler codebase, easier to trace patterns
- Same prompt_toolkit patterns as pgcli
- Selection and clipboard handling

Key files:
- `litecli/main.py` - Application and buffer setup
- `litecli/clitoolbar.py` - Status bar patterns

## Technical Design

### New Files

```
pgtail_py/
├── tail_lexer.py        # TailBufferLexer - applies stored styling
```

### Modified Files

```
pgtail_py/
├── tail_buffer.py       # Add get_plain_text(), get_line_styles()
├── tail_layout.py       # Replace FormattedTextControl with BufferControl
├── tail_app.py          # Wire clipboard, update buffer sync
└── tail_status.py       # Add selection indicator to status bar
```

### TailBufferLexer

```python
from prompt_toolkit.lexers import Lexer

class TailBufferLexer(Lexer):
    """Maps Buffer lines to pre-computed FormattedLogEntry styling."""

    def __init__(self, tail_buffer: TailBuffer) -> None:
        self._tail_buffer = tail_buffer

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        # Cache line styles at lex time
        line_styles = self._tail_buffer.get_line_styles()

        def get_line(lineno: int) -> StyleAndTextTuples:
            if lineno < len(line_styles):
                return line_styles[lineno]
            return [("", "")]

        return get_line
```

### TailBuffer Additions

```python
def get_plain_text(self) -> str:
    """Return buffer content as plain text for Buffer.document."""
    lines = []
    for entry in self._get_filtered_entries():
        text = fragment_list_to_text(entry.formatted)
        lines.append(text)
    return "\n".join(lines)

def get_line_styles(self) -> list[StyleAndTextTuples]:
    """Return per-line styling for TailBufferLexer."""
    all_styles = []
    for entry in self._get_filtered_entries():
        entry_lines = self._split_formatted_by_lines(entry.formatted)
        all_styles.extend(entry_lines)
    return all_styles

def get_entry_at_line(self, line_number: int) -> FormattedLogEntry | None:
    """Get entry containing given line (for V command)."""
    # Line-to-entry mapping for entry-level selection
    ...
```

### Layout Changes

```python
# Before (tail_layout.py)
log_control = ScrollableFormattedTextControl(
    text=self._log_content_callback,
    ...
)

# After
self._log_buffer = Buffer(
    document=Document("", 0),
    multiline=True,
    read_only=True,
    name="log_buffer",
)

log_control = BufferControl(
    buffer=self._log_buffer,
    lexer=TailBufferLexer(self._tail_buffer),
    focusable=True,
    include_default_input_processors=True,  # HighlightSelectionProcessor
)
```

### Clipboard Integration

```python
# In TailApp.start()
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.clipboard.in_memory import InMemoryClipboard

try:
    import pyperclip
    clipboard = PyperclipClipboard()
except ImportError:
    clipboard = InMemoryClipboard()  # Fallback

self._app = Application(
    ...
    clipboard=clipboard,
)
```

### Key Bindings

```python
from prompt_toolkit.filters import has_selection

log_focused = Condition(lambda: get_app().layout.current_buffer == self._log_buffer)

@kb.add("y", filter=log_focused & has_selection)
def copy_selection(event):
    data = self._log_buffer.copy_selection()
    event.app.clipboard.set_data(data)
    # Status feedback
    self._status.show_message(f"Copied {len(data.text.splitlines())} lines")

@kb.add("V", filter=log_focused)
def select_entry(event):
    # Find entry boundaries and select
    ...

@kb.add("tab")
def toggle_focus(event):
    if get_app().layout.current_buffer == self._log_buffer:
        get_app().layout.focus(self._input_buffer)
    else:
        get_app().layout.focus(self._log_buffer)
```

## Edge Cases

1. **Live updates during selection**: New entries append but don't disrupt selection
2. **Selection scrolls off buffer**: Clear selection, show notification
3. **Filter changes**: Clear selection when content reorganizes
4. **Large selection**: Limit to 100KB to prevent clipboard issues
5. **Multi-line entries**: V-select grabs all lines of logical entry
6. **Focus management**: Tab switches between log and command input

## Dependencies

- `pyperclip` (optional) - System clipboard integration
- prompt_toolkit's built-in `SelectionState`, `ClipboardData`, `has_selection` filter

## Success Criteria

1. Shift+arrows selects text in log area
2. Mouse drag selects text in log area
3. `y` copies selection to system clipboard (macOS pbpaste works)
4. `V` selects entire log entry at cursor
5. Status bar shows selection indicator ("SEL: 3 lines")
6. Tab toggles focus between log and input
7. Escape clears selection
8. SQL highlighting and level colors preserved during selection
9. Live updates don't break existing selection
10. Works on macOS, Linux, Windows

## Out of Scope

- Block/column selection (vim Ctrl+V)
- Search and select (use filter command instead)
- Selection persistence across filter changes
- Custom clipboard format (always plain text)
