# pgtail

Interactive PostgreSQL log tailer with auto-detection.

## Features

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths)
- Auto-detects log format (text, csvlog, jsonlog) and parses structured fields
- Real-time log tailing with polling (handles log rotation)
- Filter by log level (ERROR, WARNING, NOTICE, INFO, LOG, DEBUG1-5)
- Filter by field values (app=, db=, user=) for CSV/JSON logs
- Time-based filtering (since, until, between)
- Regex pattern filtering (include, exclude, AND/OR logic)
- Display modes: compact (default), full (all fields), custom fields
- Output formats: colored text or JSON Lines for piping to jq
- Highlight matching text with yellow background
- Slow query detection with configurable thresholds
- Query duration statistics (count, average, percentiles)
- Error statistics with trend visualization and live counter
- Export logs to files (text, JSON, CSV formats)
- Pipe logs to external commands (grep, jq, wc, etc.)
- Color-coded output by severity with SQL state codes
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
tail <id|path>     Tail logs for an instance (supports --since flag)
levels [LEVEL...]  Set log level filter (no args = show current, ALL = clear)
since <time>       Filter logs since time (e.g., 5m, 14:30, 2024-01-15T14:30)
until <time>       Filter logs until time
between <s> <e>    Filter logs in time range (e.g., between 14:30 15:00)
filter /pattern/   Regex filter (see Filtering below)
filter field=value Filter by field (app=, db=, user=) for CSV/JSON logs
display [mode]     Set display mode (compact, full, fields <f1,f2,...>)
output [format]    Set output format (text, json)
highlight /pattern/ Highlight matching text (yellow background)
slow [w s c]       Configure slow query highlighting (thresholds in ms)
stats              Show query duration statistics
errors             Show error statistics (see Error Statistics below)
export <file>      Export filtered logs to file (see Export below)
pipe <cmd>         Pipe filtered logs to external command (see Pipe below)
set <key> [val]    Set/view a config value (persists across sessions)
unset <key>        Remove a setting, revert to default
config             Show current configuration (subcommands: path, edit, reset)
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

### Time Filtering

Filter logs by time using relative durations, absolute times, or ISO 8601:

```
since 5m                   Show entries from last 5 minutes
since 14:30                Show entries since 2:30 PM today
since 2024-01-15T14:30     Show entries since specific datetime
until 15:00                Show entries until 3 PM today
between 14:30 15:00        Show entries between 2:30 PM and 3 PM
between 14:30 and 15:00    "and" keyword is optional
since clear                Remove time filter
until clear                Remove time filter
tail 0 --since 1h          Start tailing with time filter
```

Supported time formats:
- **Relative**: `5m`, `30s`, `2h`, `1d` (minutes, seconds, hours, days from now)
- **Time only**: `14:30`, `14:30:45` (today at specified time)
- **ISO 8601**: `2024-01-15T14:30`, `2024-01-15T14:30:00Z`

### Log Format Support

pgtail auto-detects and parses three PostgreSQL log formats:

| Format | Config Setting | Fields |
|--------|---------------|--------|
| TEXT   | `log_destination = 'stderr'` | Basic (timestamp, pid, level, message) |
| CSV    | `log_destination = 'csvlog'` | 26 fields (user, database, query, SQL state, etc.) |
| JSON   | `log_destination = 'jsonlog'` | 29 fields (PostgreSQL 15+) |

When tailing, the detected format is displayed:
```
pgtail> tail 0
Detected format: jsonlog
```

### Display Modes

Control how log entries are displayed:

```
display              Show current display mode
display compact      Single line per entry (default)
display full         All fields with labels
display fields timestamp,level,message,sql_state  Custom fields
```

Full mode example:
```
10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
  Database: mydb
  User: postgres
  Application: psql
  Query: SELECT * FROM foo
```

### Output Formats

Switch between human-readable and machine-readable output:

```
output              Show current output format
output text         Colored terminal output (default)
output json         JSON Lines format (one object per line)
```

JSON output can be piped to `jq`:
```bash
./pgtail | jq '.message'
```

### Filtering

```
filter /pattern/     Show only lines matching pattern
filter -/pattern/    Exclude lines matching pattern
filter +/pattern/    Add OR pattern (match any)
filter &/pattern/    Add AND pattern (must match all)
filter /pattern/c    Case-sensitive match
filter app=myapp     Filter by application name (CSV/JSON only)
filter db=prod       Filter by database name
filter user=postgres Filter by user name
filter clear         Remove all filters
filter               Show current filters
```

Available field filters: `app`/`application`, `db`/`database`, `user`, `pid`, `backend`

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

### Error Statistics

Track and analyze ERROR, FATAL, PANIC, and WARNING entries:

```
errors                     Show summary by SQLSTATE code and level
errors --trend             Sparkline of error rate (last 60 minutes)
errors --live              Real-time counter (Ctrl+C to exit)
errors --code 23505        Filter by SQLSTATE code
errors --since 30m         Only errors from last 30 minutes
errors --trend --since 1h  Combine time filter with trend
errors clear               Reset all statistics
```

Example output:
```
pgtail> errors
Error Statistics
─────────────────────────────
Errors: 5  Warnings: 2

By type:
  23505 unique_violation           3
  42P01 undefined_table            2

By level:
  ERROR         5
  WARNING       2

pgtail> errors --trend
Error rate (per minute):

Last 60 min: ▁▁▁▂▁▁▃▁▅▁▁▁▁▁▂▁▁▁▁▁  total 12, avg 0.2/min
```

### Export

Export filtered log entries to a file:

```
export errors.log              Save to text file
export --format json logs.json Save as JSON Lines
export --format csv data.csv   Save as CSV with headers
export --since 1h recent.log   Only entries from last hour
export --append errors.log     Append to existing file
export --follow test.log       Continuous export (like tail -f | tee)
```

Formats:
- **text**: Raw log lines (default)
- **json**: JSON Lines format, one object per line
- **csv**: CSV with timestamp, level, pid, message columns

### Pipe

Pipe filtered log entries to external commands:

```
pipe wc -l                     Count matching entries
pipe grep "SELECT"             Filter with grep
pipe --format json jq '.message'  Process JSON with jq
pipe head -20                  First 20 entries
```

### Configuration

Settings persist in a TOML config file:
- **macOS**: `~/Library/Application Support/pgtail/config.toml`
- **Linux**: `~/.config/pgtail/config.toml`
- **Windows**: `%APPDATA%/pgtail/config.toml`

```
set slow.warn 50           Save a setting (creates config file)
set slow.warn              Show current value
unset slow.warn            Remove setting, use default
config                     Show all settings as TOML
config path                Show config file location
config edit                Open in $EDITOR
config reset               Reset to defaults (creates backup)
```

Available settings:
- `default.levels` - Default log level filter (e.g., `ERROR WARNING`)
- `slow.warn`, `slow.error`, `slow.critical` - Threshold values in ms
- `display.timestamp_format` - strftime format for timestamps
- `display.show_pid`, `display.show_level` - Toggle output fields
- `theme.name` - Color theme (`dark` or `light`)

### Example

```
pgtail> list
  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
  0  16       5432   running  on   process ~/.pgrx/data-16

pgtail> tail 0
Tailing ~/.pgrx/data-16/log/postgresql-2024-01-15.json
Press Ctrl+C to stop

Detected format: jsonlog
10:23:45.123 [12345] LOG    : statement: SELECT 1
10:23:46.456 [12345] ERROR   42P01: relation "foo" does not exist

pgtail> display full
Display mode: full
10:23:46.456 [12345] ERROR 42P01: relation "foo" does not exist
  Database: mydb
  User: postgres
  Application: psql
  Query: SELECT * FROM foo

pgtail> filter app=myapp
Field filter set: application=myapp

pgtail> output json
Output format: json
{"timestamp":"2024-01-15T10:23:46.456","level":"ERROR","message":"relation \"foo\" does not exist",...}

pgtail> levels ERROR WARNING
Filter set: ERROR WARNING

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
- tomlkit

## License

MIT
