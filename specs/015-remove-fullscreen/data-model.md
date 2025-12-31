# Data Model: Remove Fullscreen TUI

**Feature**: 015-remove-fullscreen

## Not Applicable

This is a removal feature with no new data models.

## Entities Being Removed

The following entities will be deleted (not modified):

### LogBuffer (pgtail_py/fullscreen/buffer.py)

Circular buffer for storing log entries in fullscreen mode.

```python
class LogBuffer:
    """Circular buffer for fullscreen log display."""
    # ~200 lines - DELETE
```

### FullscreenState (pgtail_py/fullscreen/state.py)

State management for fullscreen TUI mode.

```python
class FullscreenState:
    """State for fullscreen mode (follow/browse mode)."""
    # ~100 lines - DELETE
```

### DisplayMode (pgtail_py/fullscreen/state.py)

Enum for fullscreen display modes (FOLLOW, BROWSE).

```python
class DisplayMode(Enum):
    """Fullscreen display modes."""
    FOLLOW = "follow"
    BROWSE = "browse"
    # DELETE
```

### LogLineLexer (pgtail_py/fullscreen/lexer.py)

Pygments lexer for PostgreSQL log lines with SQL highlighting in TextArea.

```python
class LogLineLexer(RegexLexer):
    """Pygments lexer for PostgreSQL log lines."""
    # ~270 lines - DELETE
```

## Fields Being Removed from AppState

The following fields will be removed from `pgtail_py/cli.py:AppState`:

```python
# REMOVE these fields:
fullscreen_buffer: LogBuffer | None = None
fullscreen_state: FullscreenState | None = None
```
