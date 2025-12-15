# pgtail

Interactive PostgreSQL log tailer with auto-detection.

## Features

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths)
- Real-time log tailing with fsnotify (polling fallback)
- Filter by log level (ERROR, WARNING, NOTICE, INFO, LOG, DEBUG1-5)
- Color-coded output by severity
- REPL with autocomplete and command history
- Cross-platform (macOS, Linux, Windows)

## Install

```bash
go install github.com/willibrandon/pgtail/cmd/pgtail@latest
```

Or build from source:

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
make build
```

## Usage

```bash
pgtail
```

### Commands

```
list               Show detected PostgreSQL instances
tail <id|path>     Tail logs for an instance (alias: follow)
levels [LEVEL...]  Set log level filter (no args = clear)
enable-logging <id> Enable logging_collector for an instance
refresh            Re-scan for instances
stop               Stop current tail
clear              Clear screen
help               Show help
quit               Exit (alias: exit)
```

### Log Levels

`PANIC` `FATAL` `ERROR` `WARNING` `NOTICE` `LOG` `INFO` `DEBUG1-5`

### Example

```
pgtail> list
  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
  0  16       5432   running  on   process ~/.pgrx/data-16

pgtail> tail 0
[Tailing ~/.pgrx/data-16/log/postgresql-2024-01-15.log]
2024-01-15 10:23:45 PST [12345] LOG: statement: SELECT 1
2024-01-15 10:23:46 PST [12345] ERROR: relation "foo" does not exist

pgtail> levels ERROR WARNING
[Filter set: ERR,WARN]
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Autocomplete |
| Up/Down | Command history |
| Ctrl+C | Stop tail / Clear input |
| Ctrl+D | Exit (when input empty) |
| Ctrl+L | Clear screen |

## License

MIT
