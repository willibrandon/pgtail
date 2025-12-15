# pgtail

Interactive PostgreSQL log tailer with auto-detection.

## Features

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths)
- Real-time log tailing with polling (handles log rotation)
- Filter by log level (ERROR, WARNING, NOTICE, INFO, LOG, DEBUG1-5)
- Color-coded output by severity
- REPL with autocomplete and command history
- Cross-platform (macOS, Linux, Windows)

## Install

### From source

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
pip install -e .
```

### Build standalone executable

```bash
pip install pyinstaller
pyinstaller --onefile --name pgtail pgtail_py/__main__.py
# Output: dist/pgtail
```

## Usage

```bash
python -m pgtail_py
# Or after building:
./dist/pgtail
```

### Commands

```
list               Show detected PostgreSQL instances
tail <id|path>     Tail logs for an instance
levels [LEVEL...]  Set log level filter (no args = show current, ALL = clear)
enable-logging <id> Enable logging_collector for an instance
refresh            Re-scan for instances
stop               Stop current tail
clear              Clear screen
help               Show help
quit               Exit (alias: exit, q)
!<cmd>             Run shell command
```

### Log Levels

`PANIC` `FATAL` `ERROR` `WARNING` `NOTICE` `LOG` `INFO` `DEBUG1-5`

### Example

```
pgtail> list
  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
  0  16       5432   running  on   process ~/.pgrx/data-16

pgtail> tail 0
Tailing ~/.pgrx/data-16/log/postgresql-2024-01-15.log
Press Ctrl+C to stop

10:23:45.123 [12345] LOG    : statement: SELECT 1
10:23:46.456 [12345] ERROR  : relation "foo" does not exist

pgtail> levels ERROR WARNING
Filter set: ERROR WARNING
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Autocomplete |
| Up/Down | Command history |
| Ctrl+C | Stop tail |
| Ctrl+D | Exit |

## Requirements

- Python 3.10+
- prompt_toolkit
- psutil

## License

MIT
