# Quickstart: Log Entry Selection and Copy

**Feature Branch**: `017-log-selection`
**Date**: 2025-12-31

## Prerequisites

- Python 3.10+
- pgtail development environment set up
- Textual reference available at `../textual/`

## Setup

### 1. Switch to Feature Branch

```bash
cd /Users/brandon/src/pgtail
git checkout 017-log-selection
```

### 2. Add Dependencies

Update `pyproject.toml`:

```toml
dependencies = [
    "prompt_toolkit>=3.0.0",
    "psutil>=5.9.0",
    "tomlkit>=0.12.0",
    "pygments>=2.0",
    "textual>=0.89.0",     # NEW: TUI framework
    "pyperclip>=1.8.0",    # NEW: Clipboard fallback
]
```

### 3. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e ".[dev]"
```

### 4. Verify Textual Installation

```bash
python -c "from textual import __version__; print(f'Textual version: {__version__}')"
```

Expected output: `Textual version: 0.89.0` (or higher)

---

## Project Structure

After implementation, the following files will be created/modified:

```
pgtail_py/
├── tail_textual.py      # NEW: TailApp Textual Application
├── tail_log.py          # NEW: TailLog widget (Log subclass)
├── tail_input.py        # NEW: TailInput widget (optional)
├── tail_rich.py         # NEW: Rich text formatting
├── tail_app.py          # MODIFY: Add deprecation warning
├── tail_layout.py       # MODIFY: Add deprecation warning
├── tail_buffer.py       # MODIFY: Add format_as_rich_text()
├── tail_status.py       # MODIFY: Add format_plain()
├── cli.py               # MODIFY: Import new TailApp
├── cli_tail.py          # MODIFY: Add log_widget parameter
└── display.py           # MODIFY: Add Rich output

tests/
├── test_tail_textual.py # NEW
├── test_tail_log.py     # NEW
├── test_tail_rich.py    # NEW
└── test_tail_visual.py  # NEW
```

---

## Development Workflow

### Run Existing Tests

Ensure no regressions before starting:

```bash
make test
```

### Run Linter

```bash
make lint
```

### Manual Testing

Start pgtail and enter tail mode:

```bash
# From source
python -m pgtail_py

# In pgtail REPL
pgtail> list
pgtail> tail 1
```

---

## Implementation Order

### Phase 1: Core Widget (P1 - Mouse Selection)

1. Create `tail_log.py` with basic TailLog widget
2. Create `tail_textual.py` with TailApp shell
3. Wire up log entry display (no formatting yet)
4. Verify mouse selection works

### Phase 2: Navigation (P2)

1. Add vim key bindings to TailLog
2. Implement half-page scroll methods
3. Verify navigation with existing buffer

### Phase 3: Clipboard (P1 + P3)

1. Implement `_copy_with_fallback()`
2. Add yank action
3. Test on multiple terminals

### Phase 4: Visual Mode (P3)

1. Add visual mode state machine
2. Implement selection extension on navigation
3. Test keyboard-only selection

### Phase 5: Integration (P2)

1. Adapt command handlers for Textual
2. Preserve existing filter commands
3. Update status bar rendering
4. Full integration testing

### Phase 6: Polish

1. Add deprecation warnings to old modules
2. Update CLAUDE.md with new architecture
3. Write tests for new functionality

---

## Key Code Patterns

### Creating a Textual Log Widget

```python
from textual.widgets import Log
from textual.binding import Binding

class TailLog(Log):
    ALLOW_SELECT = True

    BINDINGS = [
        Binding("j", "scroll_down", show=False),
        Binding("k", "scroll_up", show=False),
    ]

    def action_scroll_down(self) -> None:
        self.scroll_down()

    def action_scroll_up(self) -> None:
        self.scroll_up()
```

### Creating a Textual App

```python
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

class TailApp(App):
    def compose(self) -> ComposeResult:
        yield TailLog(id="log")
        yield Static(id="status")
        yield Input(id="input")

    def on_mount(self) -> None:
        self.query_one("#log").focus()
```

### Background Log Consumer

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
                self.call_from_thread(self._add_entry, entry)
            await asyncio.sleep(0.01)
```

### Clipboard with Fallback

```python
def _copy_with_fallback(self, text: str) -> bool:
    self.app.copy_to_clipboard(text)  # OSC 52
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False
```

---

## Testing

### Run All Tests

```bash
make test
```

### Run Specific Test File

```bash
pytest tests/test_tail_textual.py -v
```

### Test with Coverage

```bash
pytest --cov=pgtail_py tests/
```

### Manual Terminal Tests

Test clipboard in different terminals:

1. **iTerm2**: Should work with OSC 52
2. **Terminal.app**: Should work via pyperclip/pbcopy
3. **Kitty/WezTerm**: Should work with OSC 52

---

## Debugging Tips

### Textual Developer Console

Press `Ctrl+D` in a running Textual app to open developer console:

```python
# In developer console
self.query_one("#log").line_count
self.query_one("#log").scroll_offset
```

### Check Clipboard Content (macOS)

```bash
pbpaste
```

### Check Terminal OSC 52 Support

```bash
printf '\e]52;c;%s\a' "$(echo -n "test" | base64)"
pbpaste  # Should show "test"
```

---

## References

- [Textual Documentation](https://textual.textualize.io/)
- [Textual Log Widget](https://textual.textualize.io/widgets/log/)
- [Textual Key Bindings](https://textual.textualize.io/guide/input/#key-bindings)
- [OSC 52 Specification](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html#h3-Operating-System-Commands)
- [pyperclip Documentation](https://pyperclip.readthedocs.io/)
