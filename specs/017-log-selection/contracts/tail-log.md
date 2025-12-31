# Contract: TailLog Widget

**Component**: `pgtail_py/tail_log.py`
**Type**: Textual Log widget subclass
**Date**: 2025-12-31

## Overview

TailLog extends Textual's Log widget with vim-style navigation and visual mode selection capabilities.

---

## Interface

### Class Definition

```python
class TailLog(Log):
    """Log widget with vim-style navigation and visual mode."""

    ALLOW_SELECT: ClassVar[bool] = True

    BINDINGS: ClassVar[list[BindingType]] = [
        # Vim navigation
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("shift+g", "scroll_end", "Bottom", show=False),
        Binding("ctrl+d", "half_page_down", "Half page down", show=False),
        Binding("ctrl+u", "half_page_up", "Half page up", show=False),
        Binding("ctrl+f", "page_down", "Page down", show=False),
        Binding("pagedown", "page_down", "Page down", show=False),
        Binding("ctrl+b", "page_up", "Page up", show=False),
        Binding("pageup", "page_up", "Page up", show=False),
        # Visual mode
        Binding("v", "visual_mode", "Visual mode", show=False),
        Binding("shift+v", "visual_line_mode", "Visual line mode", show=False),
        Binding("y", "yank", "Yank", show=False),
        Binding("escape", "clear_selection", "Clear", show=False),
        # Standard shortcuts
        Binding("ctrl+a", "select_all", "Select all", show=False),
        Binding("ctrl+c", "copy_selection", "Copy", show=False),
    ]
```

### Constructor

```python
def __init__(
    self,
    max_lines: int | None = 10000,
    auto_scroll: bool = True,
    *,
    name: str | None = None,
    id: str | None = None,
    classes: str | None = None,
) -> None:
    """Initialize TailLog widget.

    Args:
        max_lines: Maximum lines to retain (default 10,000)
        auto_scroll: Auto-scroll to new content (default True)
        name: Widget name
        id: Widget ID for CSS/queries
        classes: CSS classes
    """
```

### Actions

| Action | Method | Trigger Keys |
|--------|--------|--------------|
| `scroll_down` | `action_scroll_down()` | `j`, `down` |
| `scroll_up` | `action_scroll_up()` | `k`, `up` |
| `scroll_home` | `action_scroll_home()` | `g`, `home` |
| `scroll_end` | `action_scroll_end()` | `G`, `end` |
| `half_page_down` | `action_half_page_down()` | `Ctrl+D` |
| `half_page_up` | `action_half_page_up()` | `Ctrl+U` |
| `page_down` | `action_page_down()` | `Ctrl+F`, `PageDown` |
| `page_up` | `action_page_up()` | `Ctrl+B`, `PageUp` |
| `visual_mode` | `action_visual_mode()` | `v` |
| `visual_line_mode` | `action_visual_line_mode()` | `V` |
| `yank` | `action_yank()` | `y` |
| `clear_selection` | `action_clear_selection()` | `Escape` |
| `select_all` | `action_select_all()` | `Ctrl+A` |
| `copy_selection` | `action_copy_selection()` | `Ctrl+C` |

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `visual_mode` | `bool` | True if in visual mode |
| `visual_line_mode` | `bool` | True if selecting full lines |

---

## Behavior Contracts

### B1: Scroll Down

**Precondition**: Widget has focus and content exists
**Trigger**: `j` key or `down` arrow
**Postcondition**: Scroll position increases by 1 line (clamped to max)

### B2: Scroll Up

**Precondition**: Widget has focus and scroll_offset.y > 0
**Trigger**: `k` key or `up` arrow
**Postcondition**: Scroll position decreases by 1 line (clamped to 0)

### B3: Half Page Scroll

**Precondition**: Widget has focus
**Trigger**: `Ctrl+D` (down) or `Ctrl+U` (up)
**Postcondition**: Scroll position changes by `viewport_height // 2`

### B4: Enter Visual Mode

**Precondition**: Widget has focus, not in visual mode
**Trigger**: `v` key
**Postcondition**:
- `_visual_mode = True`
- `_visual_line_mode = False`
- `_visual_anchor_line` set to current viewport center line
- Selection created from anchor to anchor (single line)

### B5: Enter Visual Line Mode

**Precondition**: Widget has focus
**Trigger**: `V` key
**Postcondition**:
- `_visual_mode = True`
- `_visual_line_mode = True`
- Selection spans full lines from anchor to current

### B6: Extend Selection in Visual Mode

**Precondition**: Visual mode active
**Trigger**: `j` or `k` key
**Postcondition**:
- Viewport scrolls
- Selection extends from anchor to new current line
- Selection visually updates

### B7: Yank Selection

**Precondition**: Visual mode active or mouse selection exists
**Trigger**: `y` key
**Postcondition**:
- Selected text copied to clipboard (OSC 52 + pyperclip)
- Selection cleared
- Visual mode exited
- Mode returns to NORMAL

### B8: Clear Selection

**Precondition**: Selection exists or visual mode active
**Trigger**: `Escape` key
**Postcondition**:
- Selection cleared from screen.selections
- `_visual_mode = False`
- `_visual_anchor_line = None`

### B9: Select All

**Precondition**: Widget has focus
**Trigger**: `Ctrl+A`
**Postcondition**: Selection covers all content (SELECT_ALL)

### B10: Copy Selection

**Precondition**: Selection exists
**Trigger**: `Ctrl+C`
**Postcondition**: Selected text copied to clipboard, selection preserved

---

## Events

### Emitted Events

| Event | When |
|-------|------|
| `TailLog.VisualModeChanged` | Visual mode entered/exited |
| `TailLog.SelectionCopied` | Text copied to clipboard |

### Event Definitions

```python
class VisualModeChanged(Message):
    """Emitted when visual mode state changes."""
    def __init__(self, active: bool, line_mode: bool) -> None:
        self.active = active
        self.line_mode = line_mode
        super().__init__()

class SelectionCopied(Message):
    """Emitted when selection is copied to clipboard."""
    def __init__(self, text: str, char_count: int) -> None:
        self.text = text
        self.char_count = char_count
        super().__init__()
```

---

## Error Handling

| Error Case | Behavior |
|------------|----------|
| Scroll beyond bounds | Clamp to valid range (0 to max_scroll_y) |
| Yank with no selection | No-op, no error |
| Clipboard write fails | Log warning, silent degradation |
| Visual mode at buffer edge | Selection stops at boundary |
