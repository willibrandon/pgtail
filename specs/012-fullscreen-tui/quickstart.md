# Developer Quickstart: Full Screen TUI Mode

**Feature**: 012-fullscreen-tui
**Date**: 2025-12-17

## Overview

This feature adds a full-screen terminal UI mode to pgtail for scrollable log viewing with vim-style navigation.

## Quick Reference

### User Commands

```
fullscreen    Enter fullscreen TUI mode (alias: fs)
```

### Keybindings in Fullscreen Mode

| Key | Action |
|-----|--------|
| `j` / `↓` | Scroll down one line |
| `k` / `↑` | Scroll up one line |
| `Ctrl+D` | Scroll down half page |
| `Ctrl+U` | Scroll up half page |
| `g` | Jump to top (first line) |
| `G` | Jump to bottom (last line) |
| `Escape` | Toggle follow/browse mode (or cancel search) |
| `f` | Enter follow mode (auto-scroll) |
| `/` | Start forward search |
| `?` | Start backward search |
| `n` | Next search match |
| `N` | Previous search match |
| `q` | Exit fullscreen, return to REPL |

## Architecture

### Module Structure

```
pgtail_py/
├── cli_fullscreen.py          # Command handler
└── fullscreen/
    ├── __init__.py            # Package exports
    ├── app.py                 # Application setup
    ├── buffer.py              # LogBuffer (circular buffer)
    ├── keybindings.py         # Vim-style key bindings
    ├── layout.py              # HSplit layout
    ├── state.py               # FullscreenState, DisplayMode
    └── controls.py            # Custom UI controls (if needed)
```

### Key Classes

1. **LogBuffer** (`buffer.py`)
   - Circular buffer using `collections.deque(maxlen=10000)`
   - Stores formatted log lines
   - Provides `get_text()` for TextArea content

2. **FullscreenState** (`state.py`)
   - Manages follow/browse mode
   - Tracks search state
   - Session-scoped (not persisted)

3. **Layout** (`layout.py`)
   - `TextArea` for scrollable log display
   - `SearchToolbar` for `/` and `?` search
   - Status bar showing mode/position

### Data Flow

```
LogTailer.on_entry()
    │
    ├──► ErrorStats.record()      (existing)
    ├──► ConnectionStats.record() (existing)
    ├──► NotificationManager.check() (existing)
    │
    └──► LogBuffer.append()       (NEW)
              │
              └──► TextArea.text = buffer.get_text()
                        │
                        └──► Screen render
```

## Implementation Guide

### Step 1: Create LogBuffer

```python
# pgtail_py/fullscreen/buffer.py
from collections import deque

class LogBuffer:
    def __init__(self, maxlen: int = 10000) -> None:
        if maxlen <= 0:
            raise ValueError("maxlen must be positive")
        self._lines: deque[str] = deque(maxlen=maxlen)

    def append(self, line: str) -> None:
        self._lines.append(line)

    def get_text(self) -> str:
        return '\n'.join(self._lines)

    def clear(self) -> None:
        self._lines.clear()

    def __len__(self) -> int:
        return len(self._lines)
```

### Step 2: Create Fullscreen State

```python
# pgtail_py/fullscreen/state.py
from enum import Enum, auto

class DisplayMode(Enum):
    FOLLOW = auto()
    BROWSE = auto()

class FullscreenState:
    def __init__(self) -> None:
        self._mode = DisplayMode.FOLLOW
        self._search_active = False

    @property
    def is_following(self) -> bool:
        return self._mode == DisplayMode.FOLLOW

    def toggle_follow(self) -> None:
        if not self._search_active:
            self._mode = (DisplayMode.BROWSE
                         if self._mode == DisplayMode.FOLLOW
                         else DisplayMode.FOLLOW)

    def enter_browse(self) -> None:
        self._mode = DisplayMode.BROWSE
```

### Step 3: Create Layout

```python
# pgtail_py/fullscreen/layout.py
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import SearchToolbar, TextArea

def create_layout(buffer, state):
    search_toolbar = SearchToolbar()

    text_area = TextArea(
        text=buffer.get_text(),
        read_only=True,
        scrollbar=True,
        search_field=search_toolbar,
    )

    def get_status_text():
        mode = "FOLLOW" if state.is_following else "BROWSE"
        return f" {mode} | {len(buffer)} lines "

    status_bar = Window(
        content=FormattedTextControl(get_status_text),
        height=D.exact(1),
        style="reverse",
    )

    root = HSplit([text_area, search_toolbar, status_bar])
    return Layout(root, focused_element=text_area), text_area, search_toolbar
```

### Step 4: Create Key Bindings

```python
# pgtail_py/fullscreen/keybindings.py
from prompt_toolkit.key_binding import KeyBindings

def create_keybindings(state, text_area):
    kb = KeyBindings()

    @kb.add('q')
    def exit_fullscreen(event):
        event.app.exit()

    @kb.add('escape')
    def toggle_mode(event):
        state.toggle_follow()
        event.app.invalidate()

    @kb.add('g')
    def go_top(event):
        state.enter_browse()
        event.current_buffer.cursor_position = 0

    @kb.add('G')
    def go_bottom(event):
        state.enter_browse()
        event.current_buffer.cursor_position = len(event.current_buffer.text)

    return kb
```

### Step 5: Create Application

```python
# pgtail_py/fullscreen/app.py
from prompt_toolkit.application import Application

def create_fullscreen_app(buffer, state):
    layout, text_area, search_toolbar = create_layout(buffer, state)
    kb = create_keybindings(state, text_area)

    return Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=True,
        enable_page_navigation_bindings=True,
    )

def run_fullscreen(buffer, state):
    app = create_fullscreen_app(buffer, state)
    app.run()
```

### Step 6: Command Handler

```python
# pgtail_py/cli_fullscreen.py
from pgtail_py.fullscreen.app import run_fullscreen

def fullscreen_command(args: str, state: AppState) -> None:
    if not state.tailing or state.tailer is None:
        warn("No active tail. Use 'tail <id>' first.")
        return

    buffer = state.get_or_create_buffer()
    fs_state = state.get_or_create_fullscreen_state()
    run_fullscreen(buffer, fs_state)
```

### Step 7: Wire Up Buffer Feeding

In `cli.py`, extend the tailer callback:

```python
def _create_on_entry_callback(state: AppState):
    def on_entry(entry: LogEntry) -> None:
        # Existing callbacks...
        state.error_stats.record(entry)

        # NEW: Feed to fullscreen buffer
        buffer = state.get_or_create_buffer()
        formatted = format_entry(entry, state.display_state)
        buffer.append(formatted)

    return on_entry
```

## Testing

### Unit Tests

```python
# tests/unit/fullscreen/test_buffer.py
def test_buffer_append():
    buf = LogBuffer(maxlen=3)
    buf.append("line1")
    buf.append("line2")
    buf.append("line3")
    buf.append("line4")  # Evicts line1
    assert len(buf) == 3
    assert "line1" not in buf.get_text()
    assert "line4" in buf.get_text()

def test_buffer_get_text():
    buf = LogBuffer()
    buf.append("a")
    buf.append("b")
    assert buf.get_text() == "a\nb"
```

### Integration Tests

```python
# tests/integration/test_fullscreen.py
def test_fullscreen_preserves_buffer(app_state, tailer):
    # Start tail, generate entries
    tailer.start()
    time.sleep(0.5)

    # Enter and exit fullscreen
    buffer_before = len(app_state.fullscreen_buffer)
    # (simulate fullscreen enter/exit)

    # Buffer should be preserved
    assert len(app_state.fullscreen_buffer) == buffer_before
```

## Common Patterns

### Updating TextArea Content

When buffer updates during fullscreen:

```python
async def update_display(app, buffer, text_area, state):
    while True:
        await asyncio.sleep(0.1)
        new_text = buffer.get_text()
        if text_area.text != new_text:
            text_area.text = new_text
            if state.is_following:
                # Auto-scroll to bottom
                text_area.buffer.cursor_position = len(new_text)
            app.invalidate()
```

### Handling Mode Transitions

```python
@kb.add('j')
@kb.add('down')
def scroll_down(event):
    state.enter_browse()  # Manual scroll exits follow mode
    # ... scroll logic
```

## Debugging Tips

1. **Test fullscreen in isolation**: Create a minimal script that just runs the fullscreen app with mock data

2. **Use refresh_interval**: Set `Application(refresh_interval=0.5)` for easier debugging of auto-updates

3. **Check terminal compatibility**: Some terminals (especially in IDEs) have limited fullscreen support

4. **Buffer threading**: Remember buffer is fed from tailer thread; TextArea updates must be on UI thread
