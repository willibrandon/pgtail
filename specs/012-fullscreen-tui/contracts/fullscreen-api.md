# Internal API Contract: Fullscreen Module

**Feature**: 012-fullscreen-tui
**Date**: 2025-12-17

## Module: `pgtail_py/fullscreen/buffer.py`

### Class: LogBuffer

```python
class LogBuffer:
    """Circular buffer for storing formatted log lines.

    Thread-safe for single-writer (tailer) / single-reader (UI) pattern.
    Uses collections.deque with maxlen for automatic FIFO eviction.
    """

    def __init__(self, maxlen: int = 10000) -> None:
        """Initialize buffer with maximum line capacity.

        Args:
            maxlen: Maximum number of lines to retain (default 10000)

        Raises:
            ValueError: If maxlen <= 0
        """
        ...

    def append(self, line: str) -> None:
        """Add a formatted log line to the buffer.

        If buffer is at capacity, oldest line is automatically evicted.
        Thread-safe via GIL (single atomic append).

        Args:
            line: Formatted log line (should not contain newline)
        """
        ...

    def get_text(self) -> str:
        """Get all lines joined as single string for TextArea.

        Returns:
            All lines joined with newlines
        """
        ...

    def get_lines(self) -> list[str]:
        """Get copy of all lines as list.

        Returns:
            List of lines in chronological order
        """
        ...

    def clear(self) -> None:
        """Remove all lines from buffer."""
        ...

    def __len__(self) -> int:
        """Return current number of lines in buffer."""
        ...

    @property
    def maxlen(self) -> int:
        """Maximum buffer capacity."""
        ...
```

## Module: `pgtail_py/fullscreen/state.py`

### Enum: DisplayMode

```python
from enum import Enum, auto

class DisplayMode(Enum):
    """Fullscreen display mode."""
    FOLLOW = auto()  # Auto-scroll to latest
    BROWSE = auto()  # Manual navigation
```

### Class: FullscreenState

```python
from prompt_toolkit.search import SearchDirection

class FullscreenState:
    """Runtime state for fullscreen TUI mode.

    Manages follow/browse mode toggling and search state.
    All state is session-scoped (not persisted).
    """

    def __init__(self) -> None:
        """Initialize with follow mode enabled."""
        ...

    @property
    def mode(self) -> DisplayMode:
        """Current display mode (FOLLOW or BROWSE)."""
        ...

    @property
    def is_following(self) -> bool:
        """True if in follow mode (auto-scroll)."""
        ...

    @property
    def search_active(self) -> bool:
        """True if search prompt is currently visible."""
        ...

    @property
    def search_pattern(self) -> str | None:
        """Current search pattern, or None if no active search."""
        ...

    def toggle_follow(self) -> None:
        """Toggle between FOLLOW and BROWSE modes.

        If search is active, this is a no-op.
        """
        ...

    def enter_browse(self) -> None:
        """Switch to browse mode (e.g., on manual scroll)."""
        ...

    def enter_follow(self) -> None:
        """Switch to follow mode and scroll to bottom."""
        ...

    def set_search_active(self, active: bool) -> None:
        """Set search prompt visibility state."""
        ...
```

## Module: `pgtail_py/fullscreen/app.py`

### Function: create_fullscreen_app

```python
from prompt_toolkit.application import Application
from pgtail_py.fullscreen.buffer import LogBuffer
from pgtail_py.fullscreen.state import FullscreenState

def create_fullscreen_app(
    buffer: LogBuffer,
    state: FullscreenState,
    on_exit: Callable[[], None] | None = None,
) -> Application:
    """Create prompt_toolkit Application for fullscreen mode.

    Args:
        buffer: LogBuffer to display (shared with REPL mode)
        state: FullscreenState for mode management
        on_exit: Optional callback when exiting fullscreen

    Returns:
        Configured Application ready to run
    """
    ...
```

### Function: run_fullscreen

```python
def run_fullscreen(
    buffer: LogBuffer,
    state: FullscreenState,
) -> None:
    """Run fullscreen mode (blocking).

    Creates and runs the fullscreen Application. Returns when
    user presses 'q' to exit.

    Args:
        buffer: LogBuffer to display
        state: FullscreenState for mode management
    """
    ...
```

## Module: `pgtail_py/fullscreen/keybindings.py`

### Function: create_keybindings

```python
from prompt_toolkit.key_binding import KeyBindings
from pgtail_py.fullscreen.state import FullscreenState

def create_keybindings(state: FullscreenState) -> KeyBindings:
    """Create vim-style key bindings for fullscreen mode.

    Bindings:
    - j/Down: Scroll down one line
    - k/Up: Scroll up one line
    - Ctrl+D: Half page down
    - Ctrl+U: Half page up
    - g: Jump to top
    - G: Jump to bottom
    - Escape: Toggle follow/browse (or cancel search if active)
    - f: Enter follow mode
    - /: Start forward search
    - ?: Start backward search
    - n: Next search match
    - N: Previous search match
    - q: Exit fullscreen mode

    Args:
        state: FullscreenState for mode toggling

    Returns:
        Configured KeyBindings
    """
    ...
```

## Module: `pgtail_py/fullscreen/layout.py`

### Function: create_layout

```python
from prompt_toolkit.layout import Layout
from prompt_toolkit.widgets import TextArea, SearchToolbar
from pgtail_py.fullscreen.buffer import LogBuffer
from pgtail_py.fullscreen.state import FullscreenState

def create_layout(
    buffer: LogBuffer,
    state: FullscreenState,
) -> tuple[Layout, TextArea, SearchToolbar]:
    """Create fullscreen layout with log view, search bar, and status bar.

    Layout structure:
    ┌─────────────────────────────────┐
    │         Log View                │ (flexible height)
    │    (TextArea, scrollable)       │
    ├─────────────────────────────────┤
    │ Search: /pattern                │ (conditional, height=1)
    ├─────────────────────────────────┤
    │ FOLLOW | 1234 lines | 1000/1234 │ (fixed height=1)
    └─────────────────────────────────┘

    Args:
        buffer: LogBuffer for content
        state: FullscreenState for status display

    Returns:
        Tuple of (Layout, TextArea, SearchToolbar) for reference
    """
    ...
```

## Module: `pgtail_py/cli_fullscreen.py`

### Function: fullscreen_command

```python
from pgtail_py.cli import AppState

def fullscreen_command(args: str, state: AppState) -> None:
    """Handle 'fullscreen' / 'fs' command.

    Enters fullscreen TUI mode if a tail is active. Preserves
    buffer across mode switches.

    Args:
        args: Command arguments (unused)
        state: Application state

    Behavior:
    - If no active tail: Print error message
    - If active tail: Enter fullscreen mode
    - On 'q' exit: Return to REPL with buffer preserved
    """
    ...
```

## Integration with AppState

### Extended AppState

```python
@dataclass
class AppState:
    # ... existing fields ...
    fullscreen_buffer: LogBuffer | None = None
    fullscreen_state: FullscreenState | None = None

    def get_or_create_buffer(self) -> LogBuffer:
        """Get existing buffer or create new one."""
        if self.fullscreen_buffer is None:
            self.fullscreen_buffer = LogBuffer()
        return self.fullscreen_buffer

    def get_or_create_fullscreen_state(self) -> FullscreenState:
        """Get existing fullscreen state or create new one."""
        if self.fullscreen_state is None:
            self.fullscreen_state = FullscreenState()
        return self.fullscreen_state
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `fullscreen` with no active tail | Print "No active tail. Use 'tail <id>' first." |
| Invalid search regex | Display "Invalid pattern: <error>" in status bar |
| Terminal doesn't support fullscreen | Graceful fallback, print warning, continue in REPL |
| Scroll past buffer bounds | Clamp to valid range (0 to len-1) |
