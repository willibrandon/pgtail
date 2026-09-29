---
title: Tail mode
description: The full screen log view, its keys, mouse, selection, command input, and status bar.
---

Tail mode is pgtail's main view: a full screen log that follows new entries as PostgreSQL writes them.

## Entering tail mode

From the REPL:

```
pgtail> tail 0              # Instance 0
pgtail> tail 0 --since 1h   # Start with a time filter
pgtail> tail                # The only instance, if there is one
```

`tail` also accepts an instance's data directory in place of its ID.

Like `tail -f`, tail mode starts at the end of the log and shows entries as PostgreSQL writes them. With a time filter
such as `--since 1h`, it first shows the entries already in the log from that time on.

## Tailing files

You can tail any log file instead of a detected instance, from the command line or the REPL:

```sh
# Single file
pgtail tail --file /path/to/postgresql.log
pgtail tail -f ./test.log

# Glob patterns (multiple files)
pgtail tail --file "*.log"
pgtail tail --file "/var/log/postgresql/*.log"

# Multiple explicit files
pgtail tail --file a.log --file b.log

# From stdin (compressed logs)
cat log.gz | gunzip | pgtail tail --stdin

# With a time filter
pgtail tail --file ./test.log --since 5m
```

Glob patterns support `*`, `?`, `[...]`, `{a,b}`, and `**` for any number of directories, and match hidden files.
The files a pattern matches are read most recently modified first, and files that start matching it later are picked
up within five seconds.

With `--stdin`, pgtail reads the whole pipe first, then takes keyboard input from the terminal. Where no terminal is
available for the keyboard, it says so and suggests `--stream`, which prints the entries instead (see
[Streaming](#streaming)).

### Multi-file display

When tailing several files, entries are interleaved by time with the file each came from:

```
[a.log] 10:30:45.123 [12345] ERROR  : duplicate key value violates unique constraint "users_pkey"
[b.log] 10:30:46.456 [12346] LOG    : statement: SELECT 1
[a.log] 10:30:47.789 [12347] WARNING: there is no transaction in progress
```

## Layout

```text
+---------------------------------------------------------------------+
|  q Quit  ? Help  / Cmd  v Visual  y Yank  p Pause  f Follow  g/G ...|  <- Key hints
+---------------------------------------------------------------------+
| 14:30:45.123 [12345] LOG    : statement: SELECT * FROM users       |  <- Log
| 14:30:45.456 [12345] LOG    : duration: 1.234 ms                    |
| ...                                                                 |
+---------------------------------------------------------------------+
| tail>                                                               |  <- Command input
+---------------------------------------------------------------------+
|  FOLLOW | E:0 W:0 | 42 lines | levels:ALL slow:>100ms | PG16:5432   |  <- Status bar
+---------------------------------------------------------------------+
```

The command input has focus when tail mode starts. **Tab** switches between the log and the input; `/` in the log
moves to the input, and **Escape** in the input clears it and returns to the log. After a command runs, focus
returns to the log.

## Log keys

### Scrolling

| Key | Action |
|-----|--------|
| `j` / `↓` | Down one line |
| `k` / `↑` | Up one line |
| `Ctrl+d` | Half page down |
| `Ctrl+u` | Half page up |
| `Ctrl+f` / `PageDown` | Full page down |
| `Ctrl+b` / `PageUp` | Full page up |
| `g` / `Home` | Go to the top |
| `G` / `End` | Go to the bottom |

Moving up highlights the current line and stops following, which the status bar shows as `PAUSED`; going back to the
last line follows again, as `less +F` does.

### Following and leaving

| Key | Action |
|-----|--------|
| `p` | Pause: new entries are counted but not shown |
| `f` | Follow: show the entries that arrived while paused, clear the selection, and follow again |
| `q` | Leave tail mode |
| `?` | Show the key reference (Escape, `q`, or `?` closes it) |
| `/` or `Tab` | Focus the command input |

Keys typed faster than the screen draws still each take effect, so holding `j` scrolls steadily.

## Selection and copying

### Keyboard

| Key | Action |
|-----|--------|
| `v` | Character-wise visual mode |
| `V` | Line-wise visual mode |
| `h` / `l` (or `←` / `→`) | Move the cursor left / right |
| `j` / `k` | Extend the selection down / up |
| `0` / `$` | Line start / end |
| `y` | Yank (copy) the selection and leave visual mode |
| `Ctrl+a` | Select everything |
| `Ctrl+c` | Copy the selection; with nothing selected, leave tail mode |
| `Escape` | Clear the selection |

Lines longer than the window scroll sideways to keep the cursor in view.

### Mouse

| Action | Result |
|--------|--------|
| Wheel | Scroll up or down three lines |
| Shift+wheel | Scroll sideways |
| Click | Select the clicked line |
| Drag | Select text; it is copied when you release the button |

### Clipboard

Copied text goes to the clipboard two ways:

1. The OSC 52 escape sequence, which reaches the clipboard of the machine your terminal runs on, even over SSH, in
   terminals that support it
2. The platform's clipboard command: `pbcopy` on macOS, `clip.exe` on Windows, and `wl-copy`, `xclip`, or `xsel` on
   Linux

`y` and `Ctrl+c` report `Copied N characters`; a mouse drag copies silently.

## Status bar

```
 FOLLOW | E:5 W:12 | 1,234 lines | levels:ERROR,FATAL,PANIC filter:/timeout/ since:1h slow:>100ms | PG16:5432
```

- **Mode**: `FOLLOW`, or `PAUSED` with `+N new` when entries arrived while paused
- **Counts**: errors (E) and warnings (W) among the shown entries
- **Lines**: the lines in the log
- **Filters**: levels, the regular expression, the time filter, and the slow query threshold
- **Source**: the PostgreSQL version and port, or the file name when tailing files. When a file's log shows the
  version and port (for example in its startup messages), the status bar shows them instead. `(unavailable)` or
  `(permission denied)` follows when the file cannot be read.

## Command input

The `tail>` input runs [commands](#commands). It keeps a history and suggests completions as you type.

### Command history

**Up** and **Down** walk through earlier commands. The last 500 are kept across sessions, in:

- **macOS**: `~/Library/Application Support/pgtail/tail_history`
- **Linux**: `~/.local/share/pgtail/tail_history` (or `$XDG_DATA_HOME/pgtail/tail_history`)
- **Windows**: `%APPDATA%\pgtail\tail_history`

### Suggestions

As you type, the rest of a suggested command appears dimmed after the cursor. **Right** or **End** accepts it.

| Context | You type | Suggested |
|---------|----------|-----------|
| Command names | `lev` | `level` |
| Level values | `level err` | `error` |
| Subcommands | `highlight ` | `add` |
| Flag names | `export --f` | `--format` |
| Flag values | `export --format ` | `csv` |
| Theme names | `theme ` | `dark` |
| Time presets | `since ` | `10m` |
| History | `filter /dead` | `filter /deadlock/` (from history) |

Suggestions come from each command's arguments, flags, and subcommands first, and from history otherwise.

### Input keys

| Key | Action |
|-----|--------|
| `Up` / `Down` | Previous / next command from history |
| `Right` / `End` | Accept the suggestion |
| `Enter` | Run the command |
| `Escape` | Clear the input and return to the log |
| `Tab` | Return to the log |
| `q` | On an empty input, leave tail mode |

## Commands

| Command | Description |
|---------|-------------|
| `level <lvl>` | Filter by level (`error`, `warning+`, `error,warning`, `all`) |
| `filter /pattern/` | Filter by regular expression (also `-/p/`, `+/p/`, `&/p/`, `field=value`, `clear`) |
| `since <time>` | Show entries from a time on |
| `until <time>` | Show entries up to a time |
| `between <start> <end>` | Show entries in a time range |
| `slow <ms>` | Highlight queries slower than a threshold (`slow off` to stop) |
| `clear` | Reset filters to those tail mode started with |
| `clear force` | Clear every filter |
| `errors` | Error statistics (`--trend`, `--code`, `--since`, `clear`) |
| `connections` | Connection statistics (`--history`, `--db=`, `--user=`, `--app=`, `clear`) |
| `highlight` | Manage semantic highlighters |
| `set <key> [value]` | Show or change a setting |
| `export <path>` | Export the shown entries (`--format`, `--highlighted`) |
| `theme <name>` | Switch color theme |
| `notify` | Configure desktop notifications |
| `pause` / `p` | Pause |
| `follow` / `f` | Resume following |
| `help` | List commands; `help keys` lists the keys; `help <command>` explains one |
| `stop` / `exit` / `q` | Leave tail mode |

`<command> help` or `<command> ?` also shows a command's help. An unknown command reports
`✗ Unknown command: ... Type 'help' for commands.`

Filters change the whole log: it is redrawn from every entry read so far, so an entry hidden by one filter comes back
when you widen or clear it.

## Streaming

`pgtail tail --stream` (or `tail --stream` in the REPL) prints entries to the terminal instead of opening tail mode,
with the same filters and colors. It follows a single file. In the REPL, `Ctrl+C` pauses the stream and shows a
`paused` prompt; `stop` stops it. On the command line, `Ctrl+C` stops it. With `--stdin`, `--stream` prints the piped
entries through the filters. When its output is piped, only the entries are written, one per line, without colors or
status lines.
