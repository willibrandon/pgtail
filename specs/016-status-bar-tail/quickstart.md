# Quickstart: Status Bar Tail Mode

**Feature Branch**: `016-status-bar-tail`
**Date**: 2025-12-30

## Overview

This feature replaces the simple streaming `tail` command with a split-screen interface featuring:
- Scrollable log output area (top)
- Status bar with live stats (middle)
- Always-visible command input line (bottom)

## Quick Demo

```bash
# Start pgtail and select an instance
pgtail

# Enter tail mode (status bar mode is now the default)
pgtail> tail 0

# The interface shows:
# ┌─────────────────────────────────────────────────────────────┐
# │ 2025-12-30 10:23:45.123 [12345] LOG: statement: SELECT ...  │
# │ 2025-12-30 10:23:45.456 [12346] ERROR: relation not found   │
# │ 2025-12-30 10:23:45.789 [12347] WARNING: slow query 250ms   │
# │                                                             │
# ├─────────────────────────────────────────────────────────────┤
# │ FOLLOW | E:1 W:1 | 3 lines | levels:ALL | PG17:5432        │
# ├─────────────────────────────────────────────────────────────┤
# │ tail> _                                                     │
# └─────────────────────────────────────────────────────────────┘

# Apply filter while logs stream (no pause needed!)
tail> level error

# Status bar updates immediately:
# │ FOLLOW | E:1 W:1 | 1 lines | levels:ERROR | PG17:5432      │

# Scroll back to find an error
# Press Page Up or use mouse wheel

# Status bar shows paused state:
# │ PAUSED +5 new | E:1 W:1 | 6 lines | levels:ERROR | PG17:5432│

# Resume following
# Press End key

# Exit to REPL
tail> stop
pgtail>
```

## Key Commands

### Filter Commands (apply without interrupting stream)

| Command | Example | Effect |
|---------|---------|--------|
| `level` | `level error,warning` | Show only ERROR and WARNING entries |
| `filter` | `filter /deadlock/` | Show entries matching regex |
| `since` | `since 5m` | Show entries from last 5 minutes |
| `slow` | `slow 100` | Highlight queries over 100ms |
| `clear` | `clear` | Remove all filters |

### Navigation Keys

| Key | Action |
|-----|--------|
| Up/Down | Scroll 1 line |
| Page Up/Down | Scroll 1 page |
| Home | Scroll to buffer start |
| End | Resume following |
| Mouse wheel | Scroll (enters paused mode) |
| Ctrl+L | Redraw screen |
| Ctrl+C | Exit to REPL |

### Display Commands (output appears inline)

| Command | Shows |
|---------|-------|
| `errors` | Error summary with SQLSTATE codes |
| `connections` | Active connection summary |

### Exit Commands

| Command | Effect |
|---------|--------|
| `stop` | Return to pgtail REPL |
| `exit` | Return to pgtail REPL |
| `q` | Return to pgtail REPL |
| Ctrl+C | Return to pgtail REPL |

## Status Bar Format

```
MODE | E:count W:count | total lines | [filters...] | PGversion:port
```

**Mode**:
- `FOLLOW` - Auto-scrolling to new entries
- `PAUSED +N new` - Scrolled back, N new entries waiting

**Counts**:
- `E:N` - Total ERROR entries seen
- `W:N` - Total WARNING entries seen

**Filters** (shown only when active):
- `levels:ERROR,WARNING` - Level filter
- `filter:/pattern/` - Regex filter
- `since:5m` - Time filter
- `slow:>100ms` - Slow query threshold

**Instance**:
- `PG17:5432` - PostgreSQL version and port

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         TailApp                              │
│  - Coordinates layout, buffer, status, tailer                │
│  - Runs prompt_toolkit Application event loop                │
└─────────────────────────────────────────────────────────────┘
         │
         ├── TailBuffer (ring buffer, 10k lines, scroll position)
         ├── TailStatus (counts, filters, mode display)
         ├── TailLayout (HSplit: log + status + input)
         └── LogTailer (background thread, queue-based)
```

## Implementation Files

| File | Purpose |
|------|---------|
| `tail_app.py` | Main coordinator, event loop |
| `tail_buffer.py` | Ring buffer with filtering |
| `tail_status.py` | Status bar state and rendering |
| `tail_layout.py` | HSplit layout builder |
| `cli_tail.py` | Command handlers for tail mode |

## Performance Targets

- UI input latency: <50ms
- Status bar updates: <100ms
- Log throughput: 1000+ lines/sec
- Memory: <50MB for 10k line buffer

## Dependencies

No new dependencies - uses existing:
- `prompt_toolkit >=3.0.0` (Application, HSplit, Window, KeyBindings)
- Python stdlib (deque, asyncio, dataclasses)
