# Tail Mode

Tail mode is pgtail's primary interface for viewing PostgreSQL logs in real-time.

## Entering Tail Mode

```
pgtail> tail 0           # Tail instance 0
pgtail> tail 0 --since 1h  # Start with time filter
```

## Interface Layout

```text
+--------------------------------------------------------------+
| q Quit  ? Help  / Cmd  v Visual  y Yank  p Pause  f Follow   |  <- Header
+--------------------------------------------------------------+
| 14:30:45.123 [12345] LOG:  statement: SELECT * FROM...       |  <- Log Display
| 14:30:45.456 [12345] LOG:  duration: 1.234 ms                |
| ...                                                          |
+--------------------------------------------------------------+
| tail>                                                        |  <- Command Input
+--------------------------------------------------------------+
| FOLLOW | E:0 W:0 | 42 lines | PG16:5432                      |  <- Status Bar
+--------------------------------------------------------------+
```

## Navigation Keys

### Scrolling

| Key | Action |
|-----|--------|
| `j` | Scroll down one line |
| `k` | Scroll up one line |
| `Ctrl+d` | Scroll down half page |
| `Ctrl+u` | Scroll up half page |
| `Ctrl+f` / `PageDown` | Scroll down full page |
| `Ctrl+b` / `PageUp` | Scroll up full page |
| `g` | Go to top |
| `G` | Go to bottom (resumes FOLLOW) |

### Mode Control

| Key | Action |
|-----|--------|
| `p` | Pause auto-scroll |
| `f` | Resume FOLLOW mode |
| `q` | Quit tail mode |
| `?` | Show help overlay |
| `/` | Focus command input |
| `Tab` | Toggle focus (log ↔ input) |

## Visual Mode Selection

### Entering Visual Mode

| Key | Action |
|-----|--------|
| `v` | Character-wise visual mode |
| `V` | Line-wise visual mode |
| `Ctrl+a` | Select all |

### In Visual Mode

| Key | Action |
|-----|--------|
| `h` / `l` | Move cursor left / right |
| `j` / `k` | Extend selection down / up |
| `0` | Move to line start |
| `$` | Move to line end |
| `y` | Yank (copy) and exit |
| `Ctrl+c` | Copy and exit |
| `Escape` | Cancel selection |

### Clipboard

Copied text goes to the system clipboard via:

1. OSC 52 escape sequence (works in most modern terminals)
2. `pyperclip` fallback (uses `pbcopy`/`xclip`/`xsel`)

## Status Bar

The status bar shows:

```
FOLLOW | E:5 W:12 | 1,234 lines | level=error | PG16:5432
```

- **Mode**: `FOLLOW` (green) or `PAUSED +N new` (yellow)
- **Counts**: Error (E) and Warning (W) counts
- **Lines**: Total filtered lines
- **Filters**: Active filters (level, regex, time)
- **Instance**: PostgreSQL version and port

## Commands

Type commands in the `tail>` prompt:

| Command | Description |
|---------|-------------|
| `level <lvl>` | Filter by level (e.g., `error`, `warning+`) |
| `filter /pattern/` | Regex filter |
| `since <time>` | Time filter (e.g., `5m`, `1h`) |
| `until <time>` | End time filter |
| `between <start> <end>` | Time range |
| `slow <ms>` | Slow query threshold |
| `errors` | Show error statistics |
| `connections` | Show connection statistics |
| `clear` | Reset filters |
| `clear force` | Clear all filters including anchor |
| `pause` / `p` | Pause auto-scroll |
| `follow` / `f` | Resume follow |
| `stop` / `q` | Exit tail mode |
| `help` | Show command help |
