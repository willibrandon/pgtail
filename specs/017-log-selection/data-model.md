# Data Model: Log Entry Selection and Copy

**Feature Branch**: `017-log-selection`
**Date**: 2025-12-31

## Overview

This document defines the component relationships and data structures for the Textual-based tail mode implementation. The architecture replaces the prompt_toolkit layout with Textual widgets while preserving the existing data flow from LogTailer through TailBuffer.

---

## Component Hierarchy

```
TailApp (Textual Application)
├── TailLog (Log widget subclass)
│   ├── _lines: list[str]        # Raw line content
│   ├── _visual_mode: bool       # Visual mode state
│   ├── _visual_anchor: int      # Selection anchor line
│   └── Selection                # Current text selection
├── StatusBar (Static widget)
│   └── TailStatus               # Existing status state
├── TailInput (Input widget subclass, pgtail_py/tail_input.py)
│   └── Buffer                   # Command text buffer
└── LogConsumer (background worker)
    └── LogTailer                # Existing log streaming
```

---

## Entities

### TailApp

Main Textual Application coordinating all components.

| Attribute | Type | Description |
|-----------|------|-------------|
| `_max_lines` | `int` | Buffer limit (default 10,000) |
| `_tailer` | `LogTailer \| None` | Log streaming component |
| `_state` | `AppState` | pgtail filter/config state |
| `_instance` | `Instance` | PostgreSQL instance info |
| `_running` | `bool` | Application running flag |

**Lifecycle**:
1. `__init__`: Create with max_lines setting
2. `compose()`: Yield TailLog, StatusBar, CommandInput
3. `on_mount()`: Start log consumer worker
4. `on_unmount()`: Stop tailer and cleanup

### TailLog

Custom Log widget with vim bindings and visual mode selection.

| Attribute | Type | Description |
|-----------|------|-------------|
| `_visual_mode` | `bool` | True if in visual mode |
| `_visual_line_mode` | `bool` | True if selecting full lines |
| `_visual_anchor_line` | `int \| None` | Line where selection started |

**Inherited from Log**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_lines` | `list[str]` | Raw line content |
| `max_lines` | `var[int \| None]` | Max lines to retain |
| `auto_scroll` | `var[bool]` | Auto-scroll behavior |

**States**:
```
┌──────────┐    v      ┌─────────────────┐
│  NORMAL  │───────────│  VISUAL_CHAR    │
└──────────┘           └─────────────────┘
     │                        │
     │ V                      │ y / Escape
     ▼                        ▼
┌─────────────────┐    ┌──────────┐
│  VISUAL_LINE    │───────────────│  NORMAL  │
└─────────────────┘  y / Escape   └──────────┘
```

### Selection

Textual's built-in selection model (from `textual.selection`).

| Attribute | Type | Description |
|-----------|------|-------------|
| `start` | `Offset \| None` | Start position (None = beginning) |
| `end` | `Offset \| None` | End position (None = end) |

**Methods**:
- `extract(text: str) -> str`: Get selected text
- `get_span(y: int) -> tuple[int, int] | None`: Get x-range for line

### TailStatus

Existing status bar state (unchanged, reused).

| Attribute | Type | Description |
|-----------|------|-------------|
| `follow_mode` | `bool` | True if auto-scrolling |
| `new_since_pause` | `int` | New entries since scroll pause |
| `error_count` | `int` | Filtered error count |
| `warning_count` | `int` | Filtered warning count |
| `total_lines` | `int` | Filtered line count |
| `level_filter` | `set[LogLevel] \| None` | Active level filter |
| `regex_filter` | `str \| None` | Active regex pattern |
| `time_filter` | `str \| None` | Active time filter description |
| `slow_threshold` | `int \| None` | Slow query threshold ms |
| `instance_version` | `str` | PostgreSQL version |
| `instance_port` | `int` | PostgreSQL port |

### FormattedLogEntry

Existing wrapper for log entries with formatted output (modified for Rich).

| Attribute | Type | Description |
|-----------|------|-------------|
| `entry` | `LogEntry` | Parsed log entry |
| `formatted` | `str` | Plain text for Log widget |
| `rich_text` | `Text` | Rich Text for styling |
| `matches_filter` | `bool` | True if passes active filters |

### LogEntry

Existing parsed log entry (unchanged).

| Attribute | Type | Description |
|-----------|------|-------------|
| `timestamp` | `datetime \| None` | Entry timestamp |
| `pid` | `int \| None` | Backend process ID |
| `level` | `LogLevel` | Log severity level |
| `sql_state` | `str \| None` | SQLSTATE error code |
| `message` | `str` | Log message content |
| `detail` | `str \| None` | DETAIL field |
| `hint` | `str \| None` | HINT field |
| `context` | `str \| None` | CONTEXT field |
| `statement` | `str \| None` | STATEMENT field |

---

## Data Flow

### Log Entry Ingestion

```
LogTailer.queue → Worker.consume → format_entry → Log.write_line
                                        │
                                        ▼
                              StatusBar.update_from_entry
```

1. `LogTailer` produces `LogEntry` objects to async queue
2. `_consume_entries` worker polls queue in background thread
3. `format_entry_as_rich()` converts to Rich Text, then to plain string
4. `TailLog.write_line()` adds to display buffer
5. `TailStatus.update_from_entry()` updates error/warning counts

### Selection Flow

```
Mouse drag → Screen.selections[widget] → Log.get_selection() → clipboard
    │
    ▼
Ctrl+C → action_copy_text → get_selected_text → copy_to_clipboard
```

1. Mouse events create/update `Selection` in `screen.selections`
2. `Ctrl+C` or mouse-up triggers copy action
3. `Log.get_selection()` extracts text from `_lines`
4. `app.copy_to_clipboard()` sends OSC 52 + pyperclip fallback

### Visual Mode Flow

```
'v' key → _visual_mode=True → anchor current line
    │
    ▼
j/k keys → scroll + update selection
    │
    ▼
'y' key → get_selection → copy → exit visual mode
```

1. `v` enters visual mode, sets anchor line
2. Navigation updates selection based on anchor and current line
3. `y` yanks selection to clipboard, clears selection, exits mode

---

## Validation Rules

### Buffer Limits

- `max_lines` MUST be <= 10,000 (prevent memory bloat)
- `max_lines` MUST be >= 100 (provide useful history)
- Old lines MUST be pruned when limit exceeded (FIFO)

### Selection Constraints

- Selection MUST NOT extend beyond buffer bounds
- Selection MUST be cleared when buffer content changes (filter update)
- Visual mode MUST exit on focus loss

### Clipboard

- OSC 52 payload MUST be base64-encoded UTF-8
- pyperclip fallback MUST catch all exceptions (graceful degradation)
- Empty selection MUST NOT trigger clipboard operation

---

## State Transitions

### TailApp States

```
STOPPED ──start()──> RUNNING ──stop()──> STOPPED
              │
              └──error──> STOPPED (with cleanup)
```

### Follow Mode States

```
FOLLOW ──scroll_up()──> SCROLLED ──scroll_to_bottom()──> FOLLOW
         │                  │
         │                  └──new entries──> SCROLLED (count increases)
         │
         └──new entries──> auto-scroll (position at end)
```

### Visual Mode States

```
NORMAL ──'v'──> VISUAL_CHAR ──'Escape'──> NORMAL
   │                │
   │                └──'y'──> (copy) ──> NORMAL
   │
   └──'V'──> VISUAL_LINE ──'Escape'──> NORMAL
                  │
                  └──'y'──> (copy) ──> NORMAL
```

---

## Relationships

```
TailApp 1──1 TailLog         (composition)
TailApp 1──1 StatusBar       (composition)
TailApp 1──1 CommandInput    (composition)
TailApp 1──1 LogTailer       (aggregation, existing)
TailApp 1──1 AppState        (aggregation, existing)

TailLog 1──* FormattedLogEntry  (via _lines)
TailLog 0..1──1 Selection       (via screen.selections)

TailStatus 1──1 Instance     (aggregation, existing)

FormattedLogEntry 1──1 LogEntry  (composition, existing)
```
