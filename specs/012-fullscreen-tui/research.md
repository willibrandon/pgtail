# Research: Full Screen TUI Mode

**Feature**: 012-fullscreen-tui
**Date**: 2025-12-17

## Research Questions

### Q1: How to implement full-screen mode with prompt_toolkit?

**Decision**: Use `Application(full_screen=True)` with `HSplit` layout containing log view and status bar.

**Rationale**: The prompt_toolkit `Application` class supports `full_screen=True` which takes over the entire terminal. Combined with `HSplit` for vertical stacking, we can create a layout with:
- Main log view (flexible height)
- Search toolbar (conditional, height=1)
- Status bar (fixed height=1)

**Alternatives considered**:
- Custom curses implementation - Rejected: prompt_toolkit is already a dependency and handles cross-platform terminal differences
- External TUI library (textual, rich) - Rejected: Would add new dependency, violating constitution principle VI

**Reference**: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/pager.py`

### Q2: How to display scrollable log content?

**Decision**: Use `TextArea` widget in read-only mode with custom content feeding, or custom `UIControl` with `FormattedTextControl`.

**Rationale**: Two viable approaches:

1. **TextArea (Simpler)**: Built-in scrollbar, search integration via `SearchToolbar`, handles vim navigation out-of-box
   - Pros: Less code, built-in search highlighting, line numbers
   - Cons: Designed for editable text; must set `read_only=True`

2. **Custom UIControl (More Control)**: Direct control over rendering, can optimize for append-only log buffer
   - Pros: Can implement efficient circular buffer rendering, custom highlighting
   - Cons: More code, must implement scroll/search manually

**Selected**: Start with `TextArea` for faster implementation; can optimize later if performance is insufficient.

**Reference**: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/pager.py` uses `TextArea(read_only=True, scrollbar=True)`

### Q3: How to implement vim-style keybindings?

**Decision**: Use `KeyBindings` class with custom bindings for j/k/g/G/Ctrl+D/Ctrl+U, plus `enable_page_navigation_bindings=True` on Application.

**Rationale**: prompt_toolkit provides:
- `enable_page_navigation_bindings=True` - Built-in Page Up/Down, Home/End support
- `KeyBindings` class - For custom mappings (j/k, g/G, etc.)
- Filter-based activation - Bindings can be conditional on app state

**Key binding implementation**:
```python
kb = KeyBindings()

@kb.add('j')
@kb.add('down')
def scroll_down(event):
    # Move cursor down one line
    pass

@kb.add('k')
@kb.add('up')
def scroll_up(event):
    # Move cursor up one line
    pass

@kb.add('g')
def go_top(event):
    event.current_buffer.cursor_position = 0

@kb.add('G')
def go_bottom(event):
    event.current_buffer.cursor_position = len(event.current_buffer.text)

@kb.add('c-d')
def page_down(event):
    # Half page down
    pass

@kb.add('c-u')
def page_up(event):
    # Half page up
    pass
```

**Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/key_binding/`

### Q4: How to implement search with highlighting?

**Decision**: Use `SearchToolbar` widget integrated with `TextArea`.

**Rationale**: The `SearchToolbar` widget provides:
- `/` to start forward search (built-in with `start_search`)
- `?` for backward search
- `n`/`N` for next/previous match
- Automatic highlighting of matches in connected `TextArea`
- Escape to cancel search

**Implementation**:
```python
from prompt_toolkit.widgets import SearchToolbar, TextArea

search_toolbar = SearchToolbar()
text_area = TextArea(
    read_only=True,
    scrollbar=True,
    search_field=search_toolbar,
)
```

**Reference**: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/pager.py`

### Q5: How to handle live log updates during browsing?

**Decision**: Use `Application.invalidate()` to trigger redraws, with separate follow/browse mode state.

**Rationale**:
- Background thread (existing `LogTailer`) pushes entries to buffer
- In follow mode: auto-scroll to bottom after each update
- In browse mode: maintain current scroll position, buffer silently grows
- `app.invalidate()` signals need to redraw without blocking

**State management**:
```python
class FullscreenState:
    follow_mode: bool = True  # True = auto-scroll, False = browse
    buffer: collections.deque[str]  # maxlen=10000
    scroll_position: int = 0
```

**Reference**: `/Users/brandon/src/python-prompt-toolkit/src/prompt_toolkit/application/application.py`

### Q6: How to preserve buffer across mode switches (REPL ↔ fullscreen)?

**Decision**: Store LogBuffer in `AppState` (existing dataclass), share between REPL and fullscreen modes.

**Rationale**:
- `AppState` already holds session-scoped state (filters, tailer, etc.)
- Add `fullscreen_buffer: LogBuffer` field
- When entering fullscreen: pass existing buffer to Application
- When exiting fullscreen: buffer persists in AppState
- Tailer's `on_entry` callback feeds both REPL output and buffer

**Implementation approach**:
```python
@dataclass
class AppState:
    # ... existing fields ...
    fullscreen_buffer: LogBuffer | None = None
```

### Q7: How to implement status bar with dynamic content?

**Decision**: Use `Window(FormattedTextControl(get_status_text))` with callable that returns formatted text.

**Rationale**: `FormattedTextControl` accepts a callable that's evaluated on each render, enabling dynamic content like:
- Current mode (FOLLOW/BROWSE)
- Line count and position
- Search status

**Implementation**:
```python
def get_status_text():
    mode = "FOLLOW" if state.follow_mode else "BROWSE"
    return [
        ("class:status.mode", f" {mode} "),
        ("class:status", f" {state.line_count} lines "),
        ("class:status.position", f" {state.current_line}/{state.total_lines} "),
    ]

status_bar = Window(
    content=FormattedTextControl(get_status_text),
    height=D.exact(1),
    style="class:status",
)
```

**Reference**: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/pager.py`

### Q8: How to handle mouse support?

**Decision**: Use `Application(mouse_support=True)` - prompt_toolkit handles scroll wheel and selection natively.

**Rationale**:
- Mouse support is optional and terminal-dependent
- prompt_toolkit's `TextArea` with `scrollbar=True` handles scroll wheel
- Text selection works via terminal's native selection (not captured by app)
- Falls back gracefully if terminal doesn't support mouse

**Note**: Mouse scroll in browse mode should auto-pause follow mode (same as keyboard scroll).

## Circular Buffer Implementation

**Decision**: Use `collections.deque(maxlen=10000)` for O(1) append and automatic eviction.

**Rationale**:
- Python's `deque` with `maxlen` automatically discards oldest items when full
- O(1) append operations for high throughput
- O(1) random access via indexing (for scroll position)
- Memory bounded by line count, not explicit cap

**Implementation**:
```python
from collections import deque

class LogBuffer:
    def __init__(self, maxlen: int = 10000):
        self._lines: deque[str] = deque(maxlen=maxlen)

    def append(self, line: str) -> None:
        self._lines.append(line)

    def get_text(self) -> str:
        return '\n'.join(self._lines)

    def __len__(self) -> int:
        return len(self._lines)
```

## Architecture Decision: TextArea vs Custom Control

After research, using `TextArea` is the recommended approach because:

1. **Built-in search**: `SearchToolbar` integration with highlighting
2. **Built-in vim bindings**: With `enable_page_navigation_bindings`
3. **Scrollbar support**: Native scrollbar rendering
4. **Less code**: ~50 lines vs ~200+ for custom implementation

**Trade-off**: TextArea stores text as single string, requiring `join` on buffer updates. For 10,000 lines at ~100 chars avg = 1MB string, this is acceptable. If performance becomes an issue, can switch to custom `UIControl` later.

## Summary

| Component | Solution | Library Support |
|-----------|----------|-----------------|
| Full-screen mode | `Application(full_screen=True)` | Native |
| Log display | `TextArea(read_only=True, scrollbar=True)` | Native |
| Search | `SearchToolbar` + TextArea integration | Native |
| Vim keys | `KeyBindings` + `enable_page_navigation_bindings` | Native |
| Status bar | `FormattedTextControl` with callable | Native |
| Mouse | `Application(mouse_support=True)` | Native |
| Buffer | `collections.deque(maxlen=10000)` | stdlib |
| Layout | `HSplit([text_area, search_toolbar, status_bar])` | Native |

All functionality can be implemented using existing prompt_toolkit features with no new dependencies.
