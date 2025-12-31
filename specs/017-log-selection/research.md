# Research: Log Entry Selection and Copy

**Feature Branch**: `017-log-selection`
**Date**: 2025-12-31
**Source**: Textual codebase at `/Users/brandon/src/textual`

## Overview

This research document captures findings from analyzing Textual's Log widget, selection system, clipboard APIs, and scrolling mechanisms to inform the implementation of log entry selection in pgtail's tail mode.

---

## 1. Textual Log Widget

**Decision**: Use Textual's `Log` widget as the base class for TailLog

**Rationale**: The Log widget provides all required functionality out of the box:
- Built-in selection via `ALLOW_SELECT = True`
- Auto-scroll with `auto_scroll` reactive property
- Max lines pruning with `max_lines` reactive property
- Line-based content management with `write_line()` and `write_lines()`
- Selection extraction via `get_selection()` method

**Alternatives considered**:
- `RichLog`: Uses Rich renderables but has more overhead for simple text
- Custom `ScrollView` subclass: Would require reimplementing selection and rendering

**Source**: `/Users/brandon/src/textual/src/textual/widgets/_log.py`

### Key Log Widget Properties

| Property | Type | Purpose |
|----------|------|---------|
| `max_lines` | `var[int \| None]` | Maximum lines to retain (pruning older) |
| `auto_scroll` | `var[bool]` | Auto-scroll to new content when True |
| `lines` | `Sequence[str]` | Read-only access to raw line content |
| `line_count` | `int` | Number of lines (excludes trailing empty) |

### Key Log Widget Methods

| Method | Signature | Purpose |
|--------|-----------|---------|
| `write` | `(data: str, scroll_end: bool \| None) -> Self` | Write arbitrary text, handles line splits |
| `write_line` | `(line: str, scroll_end: bool \| None) -> Self` | Write single line |
| `write_lines` | `(lines: Iterable[str], scroll_end: bool \| None) -> Self` | Batch write lines |
| `clear` | `() -> Self` | Clear all content |
| `get_selection` | `(selection: Selection) -> tuple[str, str] \| None` | Extract selected text |

### Auto-Scroll Behavior

The Log widget's `write_lines()` method already implements the exact auto-scroll behavior we need:

```python
# From _log.py lines 241-248
if (
    auto_scroll
    and not self.is_vertical_scrollbar_grabbed
    and is_vertical_scroll_end
):
    self.scroll_end(animate=False, immediate=True, x_axis=False)
else:
    self.refresh()
```

**Behavior**:
1. Check `auto_scroll` setting (can be overridden per-write)
2. Don't scroll if user is grabbing scrollbar
3. Only scroll if already at bottom (`is_vertical_scroll_end`)
4. Otherwise just refresh display (user reviewing history)

---

## 2. Selection System

**Decision**: Use Textual's built-in three-level selection hierarchy

**Rationale**: Selection is already fully implemented at App, Screen, and Widget levels. The Log widget has `ALLOW_SELECT = True` and `allow_select` property returning `True`.

**Source**: `/Users/brandon/src/textual/src/textual/selection.py`

### Selection Class

The `Selection` is a `NamedTuple` with `start` and `end` `Offset` values:

```python
class Selection(NamedTuple):
    start: Offset | None  # None means start of content
    end: Offset | None    # None means end of content
```

### Key Selection Methods

| Method | Purpose |
|--------|---------|
| `Selection.from_offsets(offset1, offset2)` | Create from two offsets (auto-orders) |
| `selection.extract(text)` | Extract selected text from full content |
| `selection.get_span(y)` | Get start/end x-offsets for a given line |

### SELECT_ALL Constant

```python
SELECT_ALL = Selection(None, None)  # Selects everything
```

### Selection Flow

1. Mouse drag creates Selection with start/end Offsets
2. Screen stores selections per widget in `screen.selections` dict
3. Widget's `get_selection()` is called to extract text
4. `selection.extract(text)` handles multi-line extraction

---

## 3. Clipboard Integration

**Decision**: Use Textual's `app.copy_to_clipboard()` with pyperclip fallback

**Rationale**: OSC 52 is the modern standard but doesn't work on macOS Terminal.app. pyperclip provides pbcopy/xclip fallback for full coverage.

**Source**: `/Users/brandon/src/textual/src/textual/app.py:1671-1687`

### OSC 52 Implementation

```python
def copy_to_clipboard(self, text: str) -> None:
    self._clipboard = text  # In-memory fallback
    if self._driver is None:
        return
    import base64
    base64_text = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    self._driver.write(f"\x1b]52;c;{base64_text}\a")
```

### Terminal Compatibility

| Terminal | OSC 52 Support |
|----------|----------------|
| iTerm2 | ✅ Yes |
| Ghostty | ✅ Yes |
| Kitty | ✅ Yes |
| WezTerm | ✅ Yes |
| Windows Terminal | ✅ Yes |
| macOS Terminal.app | ❌ No |
| Linux xterm | ✅ Yes (if enabled) |
| tmux | ✅ Yes (`set-clipboard on`) |

### Fallback Strategy

```python
def _copy_with_fallback(self, text: str) -> None:
    # Primary: OSC 52
    self.app.copy_to_clipboard(text)

    # Fallback: pyperclip (uses pbcopy on macOS, xclip/xsel on Linux)
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass  # Silent degradation
```

---

## 4. Scrolling APIs

**Decision**: Use inherited `ScrollView` methods for all navigation

**Rationale**: The Log widget inherits from `ScrollView` which provides comprehensive scrolling. No custom implementation needed.

**Source**: `/Users/brandon/src/textual/src/textual/widget.py`

### Available Scroll Methods

| Method | Purpose | Notes |
|--------|---------|-------|
| `scroll_up(lines=1)` | Scroll up N lines | |
| `scroll_down(lines=1)` | Scroll down N lines | |
| `scroll_page_up()` | Scroll up one page | |
| `scroll_page_down()` | Scroll down one page | |
| `scroll_home()` | Jump to top | |
| `scroll_end()` | Jump to bottom | |
| `scroll_relative(x=0, y=0)` | Scroll by relative amount | For half-page |

### Scroll Position Properties

| Property | Purpose |
|----------|---------|
| `scroll_offset` | Current (x, y) scroll position |
| `is_vertical_scroll_end` | True if at bottom |
| `is_vertical_scrollbar_grabbed` | True if user dragging scrollbar |
| `scrollable_content_region.height` | Viewport height (for half-page calc) |

### Half-Page Scroll Implementation

```python
def action_half_page_down(self) -> None:
    self.scroll_relative(y=self.scrollable_content_region.height // 2)

def action_half_page_up(self) -> None:
    self.scroll_relative(y=-self.scrollable_content_region.height // 2)
```

---

## 5. Key Bindings

**Decision**: Define BINDINGS class variable with vim keys and standard shortcuts

**Rationale**: Textual's binding system is declarative and supports multiple keys per action. Comma-separated keys in a single binding share the action.

**Source**: Various widgets in `/Users/brandon/src/textual/src/textual/widgets/`

### Binding Syntax

```python
from textual.binding import Binding

BINDINGS = [
    Binding("j", "scroll_down", "Down", show=False),
    Binding("k", "scroll_up", "Up", show=False),
    Binding("ctrl+d", "half_page_down", "Half page down", show=False),
    Binding("ctrl+u", "half_page_up", "Half page up", show=False),
    Binding("g", "scroll_home", "Top", show=False),
    Binding("shift+g", "scroll_end", "Bottom", show=False),
    Binding("v", "visual_mode", "Visual mode", show=False),
    Binding("y", "yank", "Yank", show=False),
    Binding("escape", "clear_selection", "Clear", show=False),
]
```

### Key Naming Conventions

- Modifiers: `ctrl+`, `shift+`, `alt+`
- Special keys: `escape`, `enter`, `tab`, `space`
- Arrow keys: `up`, `down`, `left`, `right`
- Page keys: `pageup`, `pagedown`, `home`, `end`

---

## 6. Visual Mode Implementation

**Decision**: Implement custom visual mode state machine in TailLog widget

**Rationale**: Textual's selection is mouse-driven. Vim visual mode requires tracking selection anchor and extending on navigation. This is widget-specific logic.

### State Machine

```
NORMAL → [v] → VISUAL_CHAR
NORMAL → [V] → VISUAL_LINE
VISUAL_* → [j/k] → extend selection
VISUAL_* → [y] → yank to clipboard, return to NORMAL
VISUAL_* → [Escape] → clear selection, return to NORMAL
```

### Implementation Approach

```python
class TailLog(Log):
    _visual_mode: bool = False
    _visual_line_mode: bool = False
    _visual_anchor_line: int | None = None

    def action_visual_mode(self) -> None:
        self._visual_mode = True
        self._visual_line_mode = False
        self._visual_anchor_line = self._get_current_line()
        self._update_selection()

    def action_visual_line_mode(self) -> None:
        self._visual_mode = True
        self._visual_line_mode = True
        self._visual_anchor_line = self._get_current_line()
        self._update_selection()

    def _get_current_line(self) -> int:
        # Line at viewport top (or center for better UX)
        return self.scroll_offset.y + (self.scrollable_content_region.height // 2)

    def _update_selection(self) -> None:
        if not self._visual_mode or self._visual_anchor_line is None:
            return
        current = self._get_current_line()
        start_line = min(self._visual_anchor_line, current)
        end_line = max(self._visual_anchor_line, current)

        from textual.geometry import Offset
        from textual.selection import Selection

        if self._visual_line_mode:
            start = Offset(0, start_line)
            end = Offset(-1, end_line)  # -1 = end of line
        else:
            start = Offset(0, start_line)
            end = Offset(-1, end_line)

        self.screen.selections[self] = Selection(start, end)
        self.refresh()
```

---

## 7. Rich Text Integration

**Decision**: Convert LogEntry to Rich Text objects for Textual rendering

**Rationale**: Textual uses Rich for styling. We need to translate existing prompt_toolkit FormattedText to Rich Text while preserving SQL highlighting and level colors.

### Color Mapping

| Log Level | Rich Style |
|-----------|------------|
| PANIC | `bold white on red` |
| FATAL | `bold red reverse` |
| ERROR | `bold red` |
| WARNING | `yellow` |
| NOTICE | `cyan` |
| LOG | `green` |
| INFO | `blue` |
| DEBUG | `dim` |

### SQL Highlighting

The existing `sql_highlighter.py` outputs prompt_toolkit FormattedText. Need adapter to output Rich Text:

```python
from rich.text import Text

def format_entry_as_rich(entry: LogEntry) -> Text:
    text = Text()

    # Timestamp (dim)
    if entry.timestamp:
        text.append(entry.timestamp.strftime("%H:%M:%S.%f")[:-3], style="dim")
        text.append(" ")

    # PID (dim)
    if entry.pid:
        text.append(f"[{entry.pid}]", style="dim")
        text.append(" ")

    # Level with color
    level_style = LEVEL_STYLES.get(entry.level, "")
    text.append(entry.level.name.ljust(7), style=level_style)
    text.append(" ")

    # SQLSTATE
    if entry.sql_state:
        text.append(entry.sql_state, style="cyan")
        text.append(": ")

    # Message (with SQL highlighting if detected)
    text.append(entry.message)

    # Secondary fields
    for field in ("detail", "hint", "context", "statement"):
        value = getattr(entry, field, None)
        if value:
            text.append(f"\n  {field.upper()}: ", style="dim bold")
            text.append(value, style="dim")

    return text
```

---

## 8. Application Structure

**Decision**: TailApp as Textual App subclass with TailLog, Input, and Footer widgets

**Rationale**: Standard Textual app pattern. Footer provides key binding hints. Input handles command entry.

### Layout

```
┌─────────────────────────────────────────────┐
│                  TailLog                    │  (takes 1fr)
│                                             │
├─────────────────────────────────────────────┤
│  Status bar (Static widget)                 │  (1 line)
├─────────────────────────────────────────────┤
│  tail>                                      │  (Input, 1 line)
└─────────────────────────────────────────────┘
```

### CSS

```css
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
```

---

## 9. Async Integration

**Decision**: Use Textual workers for log consumption

**Rationale**: Textual's `@work` decorator handles threading. Can use `call_from_thread` to safely update UI.

**Source**: Log widget already uses `@work(thread=True)` for size updates

### Pattern

```python
from textual import work

class TailApp(App):
    @work(exclusive=True)
    async def _consume_entries(self) -> None:
        while self._running:
            entry = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._tailer.get_entry(timeout=0.05)
            )
            if entry:
                formatted = format_entry_as_rich(entry)
                self.call_from_thread(self._add_entry, formatted)
            await asyncio.sleep(0.01)

    def _add_entry(self, text: Text) -> None:
        log = self.query_one("#log", TailLog)
        log.write_line(str(text))
```

---

## 10. Testing Strategy

**Decision**: Use Textual's pilot testing framework

**Rationale**: Textual provides `App.run_test()` for headless testing with simulated input.

### Example Test

```python
import pytest
from textual.pilot import Pilot

async def test_vim_navigation():
    app = TailApp()
    async with app.run_test() as pilot:
        # Add some entries
        app.add_log_entry("Line 1")
        app.add_log_entry("Line 2")
        app.add_log_entry("Line 3")

        # Press 'k' to scroll up
        await pilot.press("k")

        # Verify scroll position changed
        log = app.query_one("#log", TailLog)
        assert log.scroll_offset.y > 0
```

---

## Summary

All required functionality exists in Textual. The implementation requires:

1. **TailLog widget**: Log subclass with vim bindings and visual mode
2. **TailApp**: App subclass coordinating log, status, input, and tailer
3. **Rich formatting**: Adapter from LogEntry to Rich Text
4. **Clipboard fallback**: pyperclip for Terminal.app users
5. **Command handlers**: Adapt existing cli_tail.py handlers

No custom low-level selection or scrolling code needed - Textual provides all primitives.
