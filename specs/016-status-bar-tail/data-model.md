# Data Model: Status Bar Tail Mode

**Feature Branch**: `016-status-bar-tail`
**Date**: 2025-12-30

## Entity Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         TailApp                              │
│  - Coordinates all components                                │
│  - Owns Application event loop                               │
│  - Manages background entry consumer                         │
└─────────────────────────────────────────────────────────────┘
         │ owns                  │ owns              │ owns
         ▼                       ▼                   ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TailBuffer    │    │   TailStatus    │    │   TailLayout    │
│ - Ring buffer   │    │ - Error count   │    │ - HSplit root   │
│ - Scroll pos    │    │ - Warning count │    │ - Log window    │
│ - Filter view   │    │ - Filter state  │    │ - Status bar    │
└─────────────────┘    │ - Instance info │    │ - Input line    │
         │             │ - Mode (follow) │    └─────────────────┘
         │             └─────────────────┘
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FormattedLogEntry                          │
│  - LogEntry (original data)                                  │
│  - FormattedText (pre-styled output)                         │
│  - matches_filter (cached filter result)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Entities

### FormattedLogEntry

Pre-processed log entry ready for display.

| Field | Type | Description |
|-------|------|-------------|
| entry | LogEntry \| None | Original parsed log entry (None for command output) |
| formatted | FormattedText | Pre-styled output with colors |
| matches_filter | bool | Whether entry passes current filter criteria |

**Relationships**:
- Stored in TailBuffer._entries deque
- LogEntry reference enables re-filtering without re-parsing

**Validation Rules**:
- If entry is None, matches_filter must be True (always show command output)

---

### TailBuffer

Deque-based buffer storing formatted log entries with scroll position management.

| Field | Type | Description |
|-------|------|-------------|
| _entries | deque[FormattedLogEntry] | Fixed-size deque (maxlen=10000) |
| _max_size | int | Buffer capacity (default 10000) |
| _scroll_offset | int | Lines from bottom (0 = at end) |
| _follow_mode | bool | True = auto-scroll to new entries |
| _new_since_pause | int | Count of entries added while paused |
| _filter_funcs | list[Callable] | Active filter predicates |

**State Transitions**:
```
                 scroll_up/scroll_down
   ┌───────────────────────────────────────────┐
   │                                           │
   ▼                                           │
┌─────────┐                              ┌──────────┐
│ FOLLOW  │ ────── scroll event ───────► │  PAUSED  │
│         │                              │          │
│ offset=0│                              │ offset>0 │
│ new=0   │                              │ new++    │
└─────────┘ ◄────── resume_follow ────── └──────────┘
                   (End key)
```

**Key Operations**:
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| append | entry: FormattedLogEntry | None | Add entry, evict oldest if at capacity |
| get_visible_lines | height: int | list[FormattedText] | Return visible entries based on scroll and filter |
| scroll_up | lines: int | None | Scroll up, enter PAUSED mode |
| scroll_down | lines: int | None | Scroll down, resume FOLLOW if at bottom |
| resume_follow | None | None | Jump to end, enter FOLLOW mode |
| refilter | None | None | Re-evaluate all entries against current filters |
| update_filters | filters: list[Callable] | None | Set new filter predicates and refilter |

**Scroll Position Adjustment on Eviction**:
When oldest entry evicted while in PAUSED mode:
- If scroll_offset references evicted content: decrement offset
- If all viewed content evicted: force resume_follow()

---

### TailStatus

State container for status bar display.

| Field | Type | Description |
|-------|------|-------------|
| error_count | int | Total ERROR entries seen |
| warning_count | int | Total WARNING entries seen |
| total_lines | int | Total entries in buffer |
| follow_mode | bool | True if following, False if paused |
| new_since_pause | int | Entries added while paused |
| active_levels | set[LogLevel] | Currently filtered log levels |
| regex_pattern | str \| None | Active regex filter pattern |
| time_filter | TimeFilter \| None | Active time range filter |
| slow_threshold | int \| None | Slow query threshold in ms |
| pg_version | str | PostgreSQL version (e.g., "17") |
| pg_port | int | PostgreSQL port |

**Derived Display**:
| Condition | Status Bar Shows |
|-----------|------------------|
| follow_mode=True | `FOLLOW` |
| follow_mode=False | `PAUSED +N new` |
| active_levels != all | `levels:ERROR,WARNING` |
| regex_pattern set | `filter:/pattern/` |
| slow_threshold set | `slow:>Nms` |
| time_filter set | `since:5m` or `between:...` |

**Update Triggers**:
- New entry received → update counts
- Filter command → update filter display
- Scroll event → update mode display
- Buffer overflow → update total_lines

---

### TailLayout

HSplit-based layout builder for the three-pane interface.

| Field | Type | Description |
|-------|------|-------------|
| _root | HSplit | Top-level container |
| _log_window | Window | Scrollable log display area |
| _status_window | Window | Fixed-height status bar |
| _input_window | Window | Fixed-height command input |
| _log_control | FormattedTextControl | Log content renderer |
| _status_control | FormattedTextControl | Status content renderer |
| _input_buffer | Buffer | Editable input text |

**Layout Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│                    Log Output Area                          │
│  (Window, flexible height, wrap_lines=True)                 │
│                                                             │
│  FormattedTextControl with callback to TailBuffer           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ FOLLOW | E:5 W:12 | 1,234 lines | levels:ALL | PG17:5432   │ (height=1)
├─────────────────────────────────────────────────────────────┤
│ tail> _                                                     │ (height=1)
└─────────────────────────────────────────────────────────────┘
```

**Dynamic Content Callbacks**:
```python
# Log area content
def get_log_text() -> FormattedText:
    return buffer.get_visible_lines(get_visible_height())

# Status bar content
def get_status_text() -> FormattedText:
    return status.format()
```

---

### TailApp

Main application coordinator.

| Field | Type | Description |
|-------|------|-------------|
| _app | Application | prompt_toolkit Application instance |
| _layout | TailLayout | Layout manager |
| _buffer | TailBuffer | Log storage |
| _status | TailStatus | Status bar state |
| _tailer | LogTailer | Background log streaming |
| _running | bool | Application running flag |
| _state | AppState | Reference to pgtail AppState |

**Lifecycle**:
```
  start()
     │
     ▼
┌─────────────────┐
│  _start_tailer  │ ──► LogTailer.start()
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ _start_consumer │ ──► Background task: poll queue, update buffer
└─────────────────┘
     │
     ▼
┌─────────────────┐
│  _app.run()     │ ──► Blocks until exit
└─────────────────┘
     │
     ▼ (on exit)
┌─────────────────┐
│  _cleanup       │ ──► Stop tailer, stop consumer
└─────────────────┘
     │
     ▼
  Returns to REPL
```

**Event Handlers**:
| Event | Handler | Action |
|-------|---------|--------|
| New log entry | _on_entry | Update buffer, status, invalidate |
| Command submitted | _on_command | Parse, execute, show inline output |
| Scroll key | _on_scroll | Update buffer scroll, invalidate |
| Ctrl+C | _on_exit | Trigger cleanup and exit |
| Terminal resize | (automatic) | Layout redraws at new size |

---

### ScrollPosition (embedded in TailBuffer)

Tracks view position within buffer.

| Concept | Value Range | Meaning |
|---------|-------------|---------|
| offset=0 | - | Viewing latest entries (follow mode ready) |
| offset>0 | 1 to filtered_count | Lines scrolled up from bottom |
| visible_height | - | Number of lines that fit in log window |

**Calculation**:
```python
# Visible range within filtered entries
filtered = [e for e in entries if e.matches_filter]
end_idx = len(filtered) - offset
start_idx = max(0, end_idx - visible_height)
visible = filtered[start_idx:end_idx]
```

---

## Relationships Summary

| From | To | Relationship | Cardinality |
|------|----|--------------|-------------|
| TailApp | TailBuffer | owns | 1:1 |
| TailApp | TailStatus | owns | 1:1 |
| TailApp | TailLayout | owns | 1:1 |
| TailApp | LogTailer | owns | 1:1 |
| TailApp | AppState | references | 1:1 |
| TailBuffer | FormattedLogEntry | contains | 1:N (max 10000) |
| FormattedLogEntry | LogEntry | wraps | 1:1 or 0:1 |
| TailLayout | Window | contains | 1:3 |
| TailStatus | LogLevel | references | N:M |

---

## Invariants

1. **Buffer Size**: `len(buffer._entries) <= buffer._max_size`
2. **Scroll Bounds**: `0 <= scroll_offset <= len(filtered_entries)`
3. **Follow Mode**: `follow_mode=True` implies `scroll_offset=0` and `new_since_pause=0`
4. **Paused Counts**: `new_since_pause >= 0`, increments only when `follow_mode=False`
5. **Filter Consistency**: After `refilter()`, all entries have accurate `matches_filter` values
6. **Status Accuracy**: `error_count` and `warning_count` reflect all entries ever seen (not just current buffer)
