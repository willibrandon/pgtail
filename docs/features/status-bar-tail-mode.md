# Feature: Status Bar Tail Mode

## Problem

When tailing logs, developers and DBAs need to issue commands without interrupting the log stream:
- Adjusting filters requires Ctrl+C, typing command, resuming tail
- Can't see current filter state while watching logs
- No visibility into error/warning counts during tailing
- Scrolling back through history loses the live tail position
- Context switching between "watching" and "commanding" is jarring

The current workflow requires too many keypresses and mental context switches.

## Proposed Solution

Replace the simple streaming tail with a split-screen interface:
- **Top area**: Scrollable log output with history buffer
- **Status bar**: Live stats, current filters, instance info
- **Command input**: Always-visible prompt for issuing commands

Logs stream continuously while user types commands. No pause/resume cycle needed.

## User Scenarios

### Scenario 1: Basic Tailing with Command Input
Developer starts tailing and wants to filter to errors only:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 17:27:48.311 [78324] DEBUG1 : checkpoint sync: number=1 file=pg_xact... │
│ 17:27:48.312 [78324] LOG    : checkpoint complete: wrote 0 buffers...   │
│ 17:27:53.817 [79282] DEBUG1 : autovacuum: processing database "post...  │
│ 17:27:56.148 [78357] DEBUG1 : serializing snapshot to pg_logical/sn...  │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ [E:0 W:0 L:4] levels:ALL │ PG17 │ :28817 │ FOLLOW                       │
├─────────────────────────────────────────────────────────────────────────┤
│ > level error_                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```
User types `level error` and presses Enter. Filter applies immediately, logs keep streaming.

### Scenario 2: Scrollback Without Losing Position
DBA sees an error flash by, wants to scroll back:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 17:27:45.102 [78324] ERROR  : relation "users" does not exist           │
│ 17:27:45.103 [78324] STATEMENT: SELECT * FROM users WHERE id = 1        │
│ 17:27:45.200 [78324] LOG    : statement: SELECT * FROM accounts...      │
│ 17:27:45.201 [78324] LOG    : duration: 0.234 ms                        │
│                         ↑ SCROLLED (press End to resume follow)         │
├─────────────────────────────────────────────────────────────────────────┤
│ [E:1 W:0 L:847] levels:ALL │ PG17 │ :28817 │ PAUSED +12 new             │
├─────────────────────────────────────────────────────────────────────────┤
│ > _                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```
User presses PgUp/↑ to scroll. Status shows PAUSED and count of new lines. Press End to jump back to live tail.

### Scenario 3: Command Output Inline
Developer runs `errors` command while tailing:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│ Errors: 3 total                                                         │
│   23505 unique_violation     2                                          │
│   42P01 undefined_table      1                                          │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │
│ 17:28:01.234 [78324] LOG    : statement: INSERT INTO orders...          │
│ 17:28:01.235 [78324] LOG    : duration: 1.234 ms                        │
├─────────────────────────────────────────────────────────────────────────┤
│ [E:3 W:0 L:892] levels:ALL │ PG17 │ :28817 │ FOLLOW                     │
├─────────────────────────────────────────────────────────────────────────┤
│ > _                                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```
Command output appears inline with visual separator, then logs resume streaming.

### Scenario 4: Live Stats Update
Ops watching during deployment sees error count climb:
```
├─────────────────────────────────────────────────────────────────────────┤
│ [E:47 W:12 L:2341] levels:ERROR,WARNING │ PG17 │ :5432 │ FOLLOW         │
├─────────────────────────────────────────────────────────────────────────┤
```
Error count updates in real-time. Red highlight when errors spike.

### Scenario 5: Quick Filter Toggle
Developer wants to focus on slow queries:
```
> slow 100
```
Immediately filters to queries >100ms. Status bar updates to show `slow:>100ms`.

### Scenario 6: Exit to Full REPL
User needs to run complex multi-command workflow:
```
> exit
pgtail>
```
Returns to standard REPL. Can re-enter tail mode with `tail 0`.

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                          LOG OUTPUT AREA                                │
│                    (scrollable, 10k line buffer)                        │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ [STATS] [FILTERS] │ [INSTANCE] │ [PORT] │ [MODE]          <- STATUS BAR │
├─────────────────────────────────────────────────────────────────────────┤
│ > [COMMAND INPUT WITH TAB COMPLETION]                     <- INPUT LINE │
└─────────────────────────────────────────────────────────────────────────┘
```

**Status bar components:**
- `[E:N W:N L:N]` - Error count, warning count, total lines
- `levels:X` - Current level filter (ALL, ERROR, etc.)
- `filter:/pattern/` - Active regex filter
- `since:Xm` - Time filter if active
- `slow:>Nms` - Slow query threshold if active
- `PG17` - PostgreSQL version
- `:5432` - Port number
- `FOLLOW` / `PAUSED +N` - Tail mode status

## Commands in Tail Mode

All existing commands work, plus:

```
# Navigation
↑/↓, PgUp/PgDn    Scroll through log buffer
Home              Jump to oldest buffered line
End               Resume following (jump to live tail)
Ctrl+L            Clear screen and redraw

# Quick filters
level <levels>    Set level filter
filter <pattern>  Set regex filter
since <time>      Set time filter
slow <ms>         Set slow query threshold
clear             Clear all filters

# Stats (output appears inline)
errors            Show error summary
connections       Show connection summary
stats             Show session statistics

# Control
pause             Stop following (keep buffer updating)
follow            Resume following
stop              Stop tailing, return to REPL
exit              Alias for stop
q                 Alias for stop
Ctrl+C            Stop tailing, return to REPL
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `↑` / `↓` | Scroll one line |
| `PgUp` / `PgDn` | Scroll one page |
| `Home` | Jump to buffer start |
| `End` | Resume follow mode |
| `Ctrl+L` | Redraw screen |
| `Ctrl+C` | Exit tail mode |
| `Tab` | Command completion |
| `↑` (in input) | Previous command history |
| `↓` (in input) | Next command history |

## Technical Architecture

```
pgtail_py/
├── tail_app.py           # prompt_toolkit Application, main event loop
├── tail_layout.py        # HSplit layout: output + status + input
├── tail_buffer.py        # Ring buffer for log lines (10k max)
├── tail_status.py        # Status bar formatting and state
├── tail_keybindings.py   # Navigation and shortcut bindings
├── tail_output.py        # FormattedText rendering for log area
└── tail_commands.py      # Command dispatch in tail context
```

**Key classes:**

```python
class TailBuffer:
    """Ring buffer storing FormattedText lines with scrollback."""
    def __init__(self, max_lines: int = 10000): ...
    def append(self, line: FormattedText) -> None: ...
    def get_visible(self, height: int, offset: int) -> list[FormattedText]: ...

class TailStatus:
    """Formats status bar from current state."""
    def __init__(self, stats: ErrorStats, ...): ...
    def render(self) -> FormattedText: ...

class TailApp:
    """Main application coordinating tailer, buffer, and UI."""
    def __init__(self, instance: Instance, ...): ...
    async def run(self) -> None: ...
```

**Threading model:**
- Main thread: prompt_toolkit event loop, handles input and rendering
- Tailer thread: Polls log file, pushes entries to queue
- Queue: Thread-safe handoff from tailer to UI
- Invalidation: UI redraws when queue has new entries

## Success Criteria

1. Logs stream without interruption while typing commands
2. Scrollback preserves 10,000 lines minimum
3. Scroll position maintained when paused, easy resume to live
4. Status bar updates in real-time (<100ms latency)
5. All existing commands work in tail mode
6. Command output appears inline without disrupting flow
7. Tab completion and history work in input line
8. Clean exit with Ctrl+C or `stop` command
9. Responsive on large log volumes (1000+ lines/sec)
10. Memory bounded (ring buffer, not unbounded growth)
11. Mouse scroll wheel navigates buffer
12. Terminal resize reflows layout correctly
13. Graceful degradation when terminal too small

## Mouse Support

- Scroll wheel scrolls through log buffer
- Click on status bar elements to toggle (stretch goal)
- Click in log area focuses scroll position

## Resize Handling

- Detect terminal resize events
- Reflow content to new dimensions
- Preserve scroll position relative to content
- Minimum size: 40 columns x 10 rows (show warning if smaller)

## Out of Scope

- Multiple panes / split views
- Search highlighting in scrollback (use filter instead)
- Saving scrollback to file (use export command)
- Custom status bar layout
