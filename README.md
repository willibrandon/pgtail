# pgtail

Interactive PostgreSQL log tailer with auto-detection.

## Features

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths)
- Real-time log tailing with polling (handles log rotation)
- Filter by log level (ERROR, WARNING, NOTICE, INFO, LOG, DEBUG1-5)
- Regex pattern filtering (include, exclude, AND/OR logic)
- Highlight matching text with yellow background
- Slow query detection with configurable thresholds
- Query duration statistics (count, average, percentiles)
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
filter /pattern/   Regex filter (see Filtering below)
highlight /pattern/ Highlight matching text (yellow background)
slow [w s c]       Configure slow query highlighting (thresholds in ms)
stats              Show query duration statistics
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

### Filtering

```
filter /pattern/     Show only lines matching pattern
filter -/pattern/    Exclude lines matching pattern
filter +/pattern/    Add OR pattern (match any)
filter &/pattern/    Add AND pattern (must match all)
filter /pattern/c    Case-sensitive match
filter clear         Remove all filters
filter               Show current filters
```

### Highlighting

```
highlight /pattern/   Highlight matches with yellow background
highlight /pattern/c  Case-sensitive highlight
highlight clear       Remove all highlights
highlight             Show current highlights
```

### Slow Query Detection

```
slow 100 500 1000    Set thresholds: warning >100ms, slow >500ms, critical >1000ms
slow                 Show current settings
slow off             Disable slow query highlighting
stats                Show duration statistics (count, avg, p50, p95, p99, max)
```

Requires PostgreSQL `log_min_duration_statement` to be enabled:
```sql
ALTER SYSTEM SET log_min_duration_statement = 0;
SELECT pg_reload_conf();
```

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

pgtail> filter /SELECT/
Filter set: /SELECT/

pgtail> highlight /users/
Highlight added: /users/

pgtail> slow 100 500 1000
Slow query highlighting enabled
# Queries >100ms yellow, >500ms bold yellow, >1000ms red bold

pgtail> stats
Query Duration Statistics
─────────────────────────
  Queries:  42
  Average:  234.5ms
  p50: 150.2ms  p95: 890.1ms  p99: 1205.3ms  max: 1501.2ms
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
