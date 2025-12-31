# Contract: Clipboard Integration

**Component**: `pgtail_py/tail_log.py` (methods)
**Type**: Utility functions
**Date**: 2025-12-31

## Overview

Clipboard integration provides cross-platform copy-to-clipboard functionality with graceful degradation.

---

## Interface

### _copy_with_fallback

```python
def _copy_with_fallback(self, text: str) -> bool:
    """Copy text to clipboard with fallback mechanisms.

    Primary mechanism: OSC 52 escape sequence via Textual
    Fallback mechanism: pyperclip (pbcopy/xclip/xsel)

    Args:
        text: Text to copy to clipboard

    Returns:
        True if copy succeeded via any mechanism, False otherwise
    """
```

---

## Implementation

```python
def _copy_with_fallback(self, text: str) -> bool:
    """Copy text to clipboard with fallback mechanisms."""
    success = False

    # Primary: OSC 52 via Textual
    try:
        self.app.copy_to_clipboard(text)
        success = True
    except Exception:
        pass

    # Fallback: pyperclip
    try:
        import pyperclip
        pyperclip.copy(text)
        success = True
    except ImportError:
        # pyperclip not installed
        pass
    except Exception:
        # pyperclip failed (no clipboard mechanism available)
        pass

    return success
```

---

## Terminal Compatibility Matrix

| Terminal | OSC 52 | pyperclip | Result |
|----------|--------|-----------|--------|
| iTerm2 | ✅ | ✅ | Both work |
| Ghostty | ✅ | ✅ | Both work |
| Kitty | ✅ | ✅ | Both work |
| WezTerm | ✅ | ✅ | Both work |
| Windows Terminal | ✅ | ✅ | Both work |
| macOS Terminal.app | ❌ | ✅ | pyperclip only |
| Linux xterm | ⚠️ | ✅ | Needs config |
| tmux | ⚠️ | ✅ | Needs `set-clipboard on` |
| SSH session | ❌ | ❌ | Neither works |

---

## Behavior Contracts

### B1: Primary Copy (OSC 52)

**Precondition**: Terminal supports OSC 52
**Trigger**: `_copy_with_fallback()` called
**Postcondition**:
- OSC 52 escape sequence written to terminal
- Text in system clipboard
- Returns `True`

### B2: Fallback Copy (pyperclip)

**Precondition**: OSC 52 fails or unsupported, pyperclip installed
**Trigger**: `_copy_with_fallback()` called
**Postcondition**:
- `pyperclip.copy()` invoked
- Text in system clipboard via pbcopy/xclip
- Returns `True`

### B3: Graceful Degradation

**Precondition**: Both mechanisms fail or unavailable
**Trigger**: `_copy_with_fallback()` called
**Postcondition**:
- No exception raised
- Returns `False`
- Text NOT in clipboard (user unaware)

### B4: Large Text Handling

**Precondition**: Text exceeds 100KB
**Trigger**: `_copy_with_fallback()` called
**Postcondition**:
- OSC 52 may truncate (terminal limit)
- pyperclip handles full text
- Returns `True` if pyperclip succeeds

---

## OSC 52 Format

```
ESC ] 52 ; c ; <base64-encoded-text> BEL
```

Where:
- `ESC` = `\x1b`
- `BEL` = `\a` (or `\x07`)
- `c` = clipboard selection (system clipboard)
- Text is UTF-8 encoded, then base64 encoded

### Example

```python
import base64

text = "Hello, World!"
encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
escape_sequence = f"\x1b]52;c;{encoded}\a"
# Result: "\x1b]52;c;SGVsbG8sIFdvcmxkIQ==\a"
```

---

## pyperclip Backends

pyperclip automatically selects the appropriate backend:

| Platform | Backend |
|----------|---------|
| macOS | `pbcopy` / `pbpaste` |
| Linux (X11) | `xclip` or `xsel` |
| Linux (Wayland) | `wl-copy` / `wl-paste` |
| Windows | `pywin32` or `ctypes` |
| WSL | Windows clipboard via `/mnt/c/...` |

---

## Error Handling

| Error Case | Behavior |
|------------|----------|
| No terminal driver | OSC 52 skipped, try pyperclip |
| pyperclip not installed | Log debug, continue without fallback |
| xclip not installed | pyperclip raises, caught and ignored |
| Permission denied | pyperclip raises, caught and ignored |
| Empty text | No-op, return True immediately |

---

## Dependencies

```toml
# pyproject.toml
dependencies = [
    "pyperclip>=1.8.0",  # Clipboard fallback
]
```

**Note**: pyperclip is a soft dependency. If not installed, the fallback silently skips.
