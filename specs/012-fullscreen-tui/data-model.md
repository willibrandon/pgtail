# Data Model: Full Screen TUI Mode

**Feature**: 012-fullscreen-tui
**Date**: 2025-12-17

## Entities

### LogBuffer

Circular buffer storing formatted log entries for scrollback.

```
LogBuffer
├── lines: deque[str]           # Formatted log lines (maxlen=10000)
├── maxlen: int                 # Maximum buffer size (default 10000)
└── Methods
    ├── append(line: str)       # Add line, evicts oldest if full
    ├── get_text() -> str       # Join all lines for TextArea
    ├── clear()                 # Empty the buffer
    └── __len__() -> int        # Current line count
```

**Lifecycle**:
- Created: When first log entry arrives during session
- Updated: On each new log entry (via tailer callback)
- Persisted: In `AppState.fullscreen_buffer` across mode switches
- Destroyed: When pgtail session ends

**Constraints**:
- Maximum 10,000 lines (FIFO eviction)
- Memory bounded by line count, not bytes
- Thread-safe for append (single writer from tailer thread)

### FullscreenState

Runtime state for the fullscreen TUI mode.

```
FullscreenState
├── follow_mode: bool           # True=auto-scroll, False=browse
├── search_active: bool         # True when search prompt visible
├── search_pattern: str | None  # Current search pattern
├── search_direction: SearchDirection  # FORWARD or BACKWARD
└── Methods
    ├── toggle_follow()         # Switch between follow/browse
    ├── enter_search(dir)       # Start search in direction
    ├── exit_search()           # Cancel/complete search
    └── is_following() -> bool  # Check if in follow mode
```

**State Transitions**:

```
┌─────────────┐  Escape/scroll  ┌─────────────┐
│  FOLLOW     │ ──────────────► │  BROWSE     │
│  (auto)     │                 │  (manual)   │
└─────────────┘ ◄────────────── └─────────────┘
                   f/Escape

        │                              │
        │ / or ?                       │ / or ?
        ▼                              ▼
┌─────────────────────────────────────────────┐
│              SEARCH_ACTIVE                   │
│  (search prompt visible, typing pattern)     │
└─────────────────────────────────────────────┘
        │ Enter (execute) or Escape (cancel)
        ▼
    Return to previous mode (FOLLOW or BROWSE)
```

### DisplayMode (Enum)

Mode enum for follow vs browse behavior.

```
DisplayMode
├── FOLLOW    # Auto-scroll to latest entries
└── BROWSE    # Manual scroll, position maintained
```

### ViewPosition

Tracks scroll position within the buffer.

```
ViewPosition
├── line_offset: int            # First visible line index
├── cursor_row: int             # Cursor row relative to buffer
└── Methods
    ├── scroll_to(line: int)    # Jump to specific line
    ├── scroll_by(delta: int)   # Relative scroll
    ├── go_top()                # Jump to line 0
    └── go_bottom()             # Jump to last line
```

## Relationships

```
AppState (existing)
├── fullscreen_buffer: LogBuffer | None     # NEW - shared buffer
├── tailer: LogTailer | None                # Existing
└── ... (other existing fields)

LogTailer (existing)
├── on_entry: Callable[[LogEntry], None]    # Existing callback
└── Feeds entries to:
    ├── REPL display (existing)
    └── LogBuffer (NEW - via callback)

FullscreenApp
├── state: FullscreenState
├── buffer: LogBuffer                       # Reference from AppState
├── text_area: TextArea                     # prompt_toolkit widget
├── search_toolbar: SearchToolbar           # prompt_toolkit widget
└── status_bar: Window                      # prompt_toolkit widget
```

## Data Flow

```
                    ┌──────────────┐
                    │   Log File   │
                    └──────┬───────┘
                           │ poll
                           ▼
                    ┌──────────────┐
                    │  LogTailer   │
                    │  (existing)  │
                    └──────┬───────┘
                           │ on_entry callback
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
       ┌──────────┐ ┌──────────┐ ┌──────────────┐
       │ErrorStats│ │ConnStats │ │  LogBuffer   │
       │(existing)│ │(existing)│ │   (NEW)      │
       └──────────┘ └──────────┘ └──────┬───────┘
                                        │ get_text()
                                        ▼
                                 ┌──────────────┐
                                 │  TextArea    │
                                 │  (display)   │
                                 └──────────────┘
```

## Integration Points

### With Existing AppState

```python
@dataclass
class AppState:
    # ... existing fields ...
    fullscreen_buffer: LogBuffer | None = None  # NEW

    def get_or_create_buffer(self) -> LogBuffer:
        if self.fullscreen_buffer is None:
            self.fullscreen_buffer = LogBuffer()
        return self.fullscreen_buffer
```

### With Existing LogTailer

The tailer's `on_entry` callback chain is extended:

```python
def create_entry_callback(state: AppState) -> Callable[[LogEntry], None]:
    def on_entry(entry: LogEntry) -> None:
        # Existing callbacks
        state.error_stats.record(entry)
        state.connection_stats.record(entry)
        state.notification_manager.check(entry)

        # NEW: Feed to fullscreen buffer
        buffer = state.get_or_create_buffer()
        formatted = format_entry(entry, state.display_state)
        buffer.append(formatted)

    return on_entry
```

## Validation Rules

| Field | Rule | Error |
|-------|------|-------|
| LogBuffer.maxlen | Must be > 0 | ValueError |
| LogBuffer.lines | Each line non-null | N/A (enforced by deque) |
| FullscreenState.search_pattern | Valid regex if set | Display "Invalid pattern" |
| ViewPosition.line_offset | 0 <= offset < buffer_len | Clamp to valid range |

## Thread Safety

| Component | Access Pattern | Safety Mechanism |
|-----------|----------------|------------------|
| LogBuffer | Single writer (tailer), single reader (UI) | Producer-consumer safe |
| FullscreenState | UI thread only | Single-threaded |
| TextArea.text | Set from UI thread only | prompt_toolkit handles |

Note: The `deque.append()` operation is atomic in CPython due to GIL, making LogBuffer safe for the producer-consumer pattern without explicit locks.
