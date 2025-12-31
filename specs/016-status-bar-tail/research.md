# Research: Status Bar Tail Mode

**Feature Branch**: `016-status-bar-tail`
**Date**: 2025-12-30

## Summary

This document consolidates research findings for implementing the split-screen status bar tail mode. The key architectural decision is to use prompt_toolkit's `Application` with `HSplit` layout for the three-pane interface, leveraging existing patterns from the pgtail codebase.

---

## Research Topics

### 1. Split-Screen Layout Architecture

**Decision**: Use `HSplit` with three sections - log area (flexible), status bar (fixed 1 line), input line (fixed 1 line)

**Rationale**:
- HSplit is the standard prompt_toolkit pattern for vertical stacking
- Supports both fixed and flexible height dimensions
- Automatic height distribution handles terminal resize

**Alternatives Considered**:
- Full-screen `TextArea` with status line: Rejected - less control over status bar styling and input handling
- Custom `Container` subclass: Rejected - unnecessary complexity when HSplit meets requirements

**Implementation Pattern**:
```python
from prompt_toolkit.layout import HSplit, Window, Layout
from prompt_toolkit.layout.controls import FormattedTextControl, BufferControl
from prompt_toolkit.layout.dimension import Dimension

root = HSplit([
    Window(content=log_control, wrap_lines=True),           # Flexible height
    Window(content=status_control, height=Dimension.exact(1)),  # Fixed 1 line
    Window(content=input_control, height=Dimension.exact(1)),   # Fixed 1 line
])
```

---

### 2. Deque Buffer with Scroll Position

**Decision**: Custom `TailBuffer` class with deque-based storage and explicit scroll position tracking

**Rationale**:
- `deque(maxlen=10000)` provides O(1) append with automatic eviction
- Separate scroll position allows FOLLOW vs PAUSED mode
- Filter-aware view layer shows only matching entries

**Key Behaviors**:
- Append: Add formatted entry to buffer, evict oldest if at capacity
- Scroll position adjustment: When entries evicted, decrement scroll offset to keep same content visible
- Follow mode: Scroll position always at end
- Paused mode: Fixed scroll offset, track "+N new" count

**Data Structure**:
```python
@dataclass
class TailBuffer:
    _entries: deque[FormattedLogEntry]  # maxlen=10000
    _scroll_offset: int                  # 0 = oldest visible, negative = from end
    _follow_mode: bool                   # True = auto-scroll, False = paused
    _new_since_pause: int               # Count for "+N new" display

    def append(entry: FormattedLogEntry) -> None
    def get_visible_range(height: int) -> list[FormattedLogEntry]
    def scroll_up(lines: int) -> None
    def scroll_down(lines: int) -> None
    def resume_follow() -> None
```

---

### 3. Thread-Safe UI Updates

**Decision**: Use `Application.invalidate()` from background tailer thread

**Rationale**:
- `invalidate()` is documented as thread-safe (uses `call_soon_threadsafe` internally)
- Existing LogTailer already uses background thread with queue
- Minimal change to existing architecture

**Implementation Pattern**:
```python
# In TailApp, background task consumes from tailer queue
async def _consume_entries():
    while self._running:
        entry = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._tailer.get_entry(timeout=0.05)
        )
        if entry:
            formatted = format_entry(entry)
            self._buffer.append(formatted)
            self._status.update_counts(entry)
            self._app.invalidate()  # Thread-safe redraw trigger
```

**Key Insight**: The existing `LogTailer.get_entry(timeout)` pattern with short timeout remains correct. The Application event loop polls for new entries and triggers redraws.

---

### 4. Mouse Scroll Wheel Support

**Decision**: Enable `mouse_support=True` on Application, handle scroll events in log window

**Rationale**:
- prompt_toolkit has built-in scroll wheel handling via `Window._mouse_handler`
- `MouseEventType.SCROLL_UP` and `SCROLL_DOWN` events are automatic
- Custom handler can switch from FOLLOW to PAUSED mode on scroll

**Implementation Pattern**:
```python
def log_mouse_handler(mouse_event: MouseEvent) -> NotImplementedOrNone:
    if mouse_event.event_type == MouseEventType.SCROLL_UP:
        self._buffer.scroll_up(3)  # 3 lines per wheel tick
        return None
    elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
        self._buffer.scroll_down(3)
        return None
    return NotImplemented

log_window = Window(
    content=log_control,
    wrap_lines=True,
)
# Set handler after creation
log_window.mouse_handler = log_mouse_handler
```

---

### 5. Keyboard Navigation

**Decision**: Custom key bindings on Application for navigation within log area

**Rationale**:
- Default key bindings go to focused control (input line)
- Need custom bindings for Up/Down/PgUp/PgDn/Home/End in log area
- Use conditional key bindings based on focus

**Key Bindings**:
| Key | Action | Notes |
|-----|--------|-------|
| Up | Scroll up 1 line | Enters PAUSED mode |
| Down | Scroll down 1 line | - |
| Page Up | Scroll up 1 page | - |
| Page Down | Scroll down 1 page | - |
| Home | Scroll to buffer start | - |
| End | Resume FOLLOW mode | Jump to latest |
| Ctrl+L | Redraw screen | - |
| Ctrl+C | Exit to REPL | - |

**Implementation Pattern**:
```python
kb = KeyBindings()

@kb.add('pageup')
def _(event):
    buffer.scroll_up(buffer.visible_height)

@kb.add('pagedown')
def _(event):
    buffer.scroll_down(buffer.visible_height)

@kb.add('end')
def _(event):
    buffer.resume_follow()

@kb.add('c-l')
def _(event):
    event.app.invalidate()
```

---

### 6. Terminal Resize Handling

**Decision**: Rely on prompt_toolkit's automatic resize handling

**Rationale**:
- Application installs SIGWINCH handler automatically
- Invalidates layout on resize, triggers full redraw
- Layout recalculates dimensions automatically

**Implementation**:
- No custom code needed for basic resize
- TailBuffer.get_visible_range() called with current height on each render
- Scroll position remains valid after resize (clipped if necessary)

**Minimum Terminal Size Warning**:
```python
def get_status_text() -> FormattedText:
    width, height = get_app().output.get_size()
    if width < 40 or height < 10:
        return [('class:warning', 'Terminal too small (min: 40x10)')]
    # ... normal status
```

---

### 7. Filter Re-application on Buffer

**Decision**: Maintain two views - raw buffer (all entries) and filtered view (matching entries)

**Rationale**:
- FR-016a requires re-filtering existing buffer when filter changes
- Storing pre-formatted entries means filter must check original LogEntry
- Need both raw entries and their formatted output

**Data Structure**:
```python
@dataclass
class FormattedLogEntry:
    entry: LogEntry           # Original for filtering
    formatted: FormattedText  # Pre-styled output
    matches_filter: bool      # Cached filter result

@dataclass
class TailBuffer:
    _entries: deque[FormattedLogEntry]
    _filter_state: FilterState  # Current active filters

    def refilter(self) -> None:
        """Re-evaluate all entries against current filters."""
        for e in self._entries:
            e.matches_filter = self._passes_filter(e.entry)

    def get_visible_range(height: int) -> list[FormattedText]:
        """Return only entries where matches_filter=True."""
        visible = [e.formatted for e in self._entries if e.matches_filter]
        # Apply scroll offset to filtered view
        ...
```

---

### 8. Inline Command Output

**Decision**: Insert command output as special entries with separator styling

**Rationale**:
- FR-010 requires inline display with visual separators
- Keeps log flow continuous without modal interruption
- Output scrolls away naturally as new logs arrive

**Implementation**:
```python
SEPARATOR_STYLE = [('class:separator', '·' * 40)]

def insert_command_output(buffer: TailBuffer, output: FormattedText) -> None:
    buffer.append(FormattedLogEntry(
        entry=None,  # Not a real log entry
        formatted=SEPARATOR_STYLE,
        matches_filter=True,  # Always show separators
    ))
    buffer.append(FormattedLogEntry(
        entry=None,
        formatted=output,
        matches_filter=True,
    ))
    buffer.append(FormattedLogEntry(
        entry=None,
        formatted=SEPARATOR_STYLE,
        matches_filter=True,
    ))
```

---

### 9. Status Bar Content

**Decision**: Single-line status with sections separated by `|`

**Format**: `FOLLOW | E:5 W:12 | 1,234 lines | levels:ERROR,WARNING | filter:/deadlock/ | slow:>100ms | PG17:5432`

**Sections**:
1. Mode: `FOLLOW` or `PAUSED +N new`
2. Counts: `E:N W:N` (error/warning since start)
3. Total: `N lines` (buffer size)
4. Active filters (only shown when non-default)
5. Instance info: `PGversion:port`

**Styling**:
```python
def format_status(status: TailStatus) -> FormattedText:
    parts = []

    # Mode
    if status.follow_mode:
        parts.append(('class:status.follow', 'FOLLOW'))
    else:
        parts.append(('class:status.paused', f'PAUSED +{status.new_count} new'))

    parts.append(('class:status.sep', ' | '))

    # Counts
    parts.append(('class:status.error', f'E:{status.error_count}'))
    parts.append(('class:status.sep', ' '))
    parts.append(('class:status.warning', f'W:{status.warning_count}'))

    # ... etc

    return FormattedText(parts)
```

---

### 10. Exit Handling

**Decision**: Multiple exit methods all route to same cleanup

**Exit Methods**:
- `stop`, `exit`, `q` commands
- Ctrl+C keyboard interrupt
- (All return to pgtail REPL, don't exit program)

**Cleanup Sequence**:
1. Set `_running = False`
2. Stop background entry consumer
3. Stop LogTailer
4. Exit Application event loop
5. Return control to main REPL

**Implementation**:
```python
async def _handle_exit(self):
    self._running = False
    self._tailer.stop()
    self._app.exit()
```

---

## Dependencies

No new dependencies required. All functionality uses existing:
- `prompt_toolkit >=3.0.0` (already required)
- Python stdlib `collections.deque`, `asyncio`, `dataclasses`

---

## References

- prompt_toolkit source: `/Users/brandon/src/python-prompt-toolkit/`
- Split-screen example: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/split-screen.py`
- Scrollable panes example: `/Users/brandon/src/python-prompt-toolkit/examples/full-screen/scrollable-panes/`
- Existing pgtail modules: `cli.py`, `tailer.py`, `display.py`, `colors.py`
