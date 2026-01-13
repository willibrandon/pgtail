<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="art/pgtail-logo-gh-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="art/pgtail-logo-gh-light.png">
    <img alt="pgtail logo" src="art/pgtail-logo-gh-light.png" width="200">
  </picture>
</p>

# pgtail

Interactive PostgreSQL log tailer with auto-detection.

## Features

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths)
- **Tail arbitrary log files** (`--file`) with glob patterns and multi-file support
- **Stdin pipe support** (`--stdin`) for archived/compressed logs
- Auto-detects log format (text, csvlog, jsonlog) and parses structured fields
- Real-time log tailing with polling (handles log rotation and PostgreSQL restarts)
- **Textual-based tail mode** with split-screen interface (header, log, input, status bar)
- **Vim-style navigation** (j/k, g/G, Ctrl+d/u/f/b, p/f for pause/follow)
- **Visual mode selection** (v/V for character/line mode, y to yank, Ctrl+a/c)
- **Clipboard support** via OSC 52 terminal escape + pyperclip fallback
- Filter by log level with flexible syntax (ERROR, error+, warning-, abbreviations)
- Filter by field values (app=, db=, user=) for CSV/JSON logs
- Time-based filtering (since, until, between)
- Regex pattern filtering (include, exclude, AND/OR logic)
- Display modes: compact (default), full (all fields), custom fields
- Output formats: colored text or JSON Lines for piping to jq
- Highlight matching text with yellow background
- Slow query detection with configurable thresholds
- Query duration statistics (count, average, percentiles)
- Error statistics with trend visualization and live counter
- Connection statistics with history trends and live watch mode
- Desktop notifications for critical log events (FATAL, PANIC, patterns, thresholds)
- Export logs to files (text, JSON, CSV formats)
- Pipe logs to external commands (grep, jq, wc, etc.)
- Color themes: 6 built-in themes plus custom TOML themes
- **SQL syntax highlighting** in log messages (keywords, identifiers, strings, numbers, operators, comments)
- Color-coded output by severity with SQL state codes
- REPL with autocomplete and command history
- Cross-platform (macOS, Linux, Windows)

## Installation

### pip / pipx / uv (Python 3.10+)

```bash
# pip
pip install git+https://github.com/willibrandon/pgtail.git

# pipx (recommended for CLI tools - isolated environment)
pipx install git+https://github.com/willibrandon/pgtail.git

# uv (fast Python package manager)
uv tool install git+https://github.com/willibrandon/pgtail.git
```

Install a specific version:
```bash
pip install git+https://github.com/willibrandon/pgtail.git@v0.1.0
```

### Homebrew (macOS / Linux)

```bash
brew tap willibrandon/tap
brew install pgtail
```

### winget (Windows)

```powershell
winget install willibrandon.pgtail
```

### Binary Download

Download pre-built archives from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest).

| Platform | Archive | Python Required |
|----------|---------|-----------------|
| macOS (Apple Silicon) | `pgtail-macos-arm64.tar.gz` | No |
| macOS (Intel) | `pgtail-macos-x86_64.tar.gz` | No |
| Linux (x86_64) | `pgtail-linux-x86_64.tar.gz` | No |
| Linux (ARM64) | `pgtail-linux-arm64.tar.gz` | No |
| Windows (x86_64) | `pgtail-windows-x86_64.zip` or `.msi` | No |

**macOS / Linux:**
```bash
# Extract the archive
tar -xzf pgtail-macos-arm64.tar.gz

# Run pgtail from the extracted folder
./pgtail-macos-arm64/pgtail --version

# Optional: Add to PATH
sudo cp -r pgtail-macos-arm64 /usr/local/lib/
sudo ln -s /usr/local/lib/pgtail-macos-arm64/pgtail /usr/local/bin/pgtail
```

**Windows (ZIP - portable, no admin):**
```powershell
# Extract the ZIP
Expand-Archive pgtail-windows-x86_64.zip -DestinationPath .

# Run pgtail from the extracted folder
.\pgtail-windows-x86_64\pgtail.exe --version

# Optional: Add to PATH manually via System Properties
```

**Windows (MSI - admin, adds to PATH):**
```powershell
# Run the installer (requires admin)
msiexec /i pgtail-windows-x86_64.msi

# After install, pgtail is available system-wide
pgtail --version
```

### From Source

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
pip install -e .
```

### Build Standalone Executable

pgtail is compiled with Nuitka for optimal performance. To build locally:

```bash
# Install build dependencies
pip install nuitka

# Build standalone folder distribution
make build

# Output: dist/pgtail-{platform}-{arch}/pgtail
```

### Installation Summary

| Method | Platforms | Python Required | Auto-Update | Notes |
|--------|-----------|-----------------|-------------|-------|
| pip / pipx / uv | All | Yes (3.10+) | Manual | |
| Homebrew | macOS, Linux | No | `brew upgrade` | |
| winget | Windows | No | `winget upgrade` | |
| MSI | Windows | No | Manual | Admin required, adds to PATH |
| ZIP/tar.gz | All | No | Manual | Portable, extract and run |

## Upgrading

Check for available updates:
```bash
pgtail --check-update
```

Upgrade commands by installation method:

| Method | Upgrade Command |
|--------|-----------------|
| pip | `pip install --upgrade git+https://github.com/willibrandon/pgtail.git` |
| pipx | `pipx upgrade pgtail` |
| uv | `uv tool upgrade pgtail` |
| Homebrew | `brew upgrade pgtail` |
| winget | `winget upgrade willibrandon.pgtail` |
| Binary | Re-download from [releases](https://github.com/willibrandon/pgtail/releases/latest) |

pgtail checks for updates automatically on startup (once per 24 hours). Disable with:
```bash
pgtail set updates.check false
```

## Usage

```bash
python -m pgtail_py
# Or after building:
./dist/pgtail
```

### Shell Completion

pgtail supports shell completion for commands and PostgreSQL instance IDs. Tab completion shows available instances with version, port, and status:

```bash
$ pgtail tail <TAB>
0  -- PG17:5432 (running)
1  -- PG16:5433 (stopped)
```

Enable shell completion (auto-detects your current shell):

```bash
pgtail --install-completion
```

After installation, restart your shell or source your shell's config file.

### Commands

```
list               Show detected PostgreSQL instances
tail <id>          Tail logs for an instance (supports --since flag)
tail --file <path> Tail arbitrary log file(s) (glob patterns, multiple files)
tail --stdin       Read log data from stdin pipe
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
connections        Show connection statistics (see Connection Statistics below)
notify             Configure desktop notifications (see Desktop Notifications below)
theme              Switch color themes (see Color Themes below)
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

### File Tailing

Tail arbitrary log files instead of auto-detected PostgreSQL instances:

```bash
# Single file
pgtail tail --file /path/to/postgresql.log
pgtail tail -f ./test.log                    # Short form

# Glob patterns (multiple files)
pgtail tail --file "*.log"                   # All .log files in current dir
pgtail tail --file "/var/log/postgresql/*.log"  # Absolute path with glob

# Multiple explicit files
pgtail tail --file a.log --file b.log

# From stdin (compressed/archived logs)
cat log.gz | gunzip | pgtail tail --stdin
zcat archived.log.gz | pgtail tail --stdin

# Combine with time filter
pgtail tail --file ./test.log --since 5m
```

**Glob Pattern Features:**
- Pattern characters: `*`, `?`, `[...]`
- Multi-level globs: `**/*.log` for recursive matching
- Files sorted by modification time (newest first)
- Dynamic file watching: newly created files detected within 5 seconds

**Multi-File Display:**
- Entries interleaved by timestamp across files
- Source file indicator shown as `[filename]` prefix:
  ```
  [a.log] 10:30:45 [12345] ERROR: duplicate key
  [b.log] 10:30:46 [12346] LOG: statement executed
  ```
- Per-file format auto-detection

**Stdin Pipe Support:**
- All data buffered before displaying (allows keyboard navigation)
- Format auto-detected from first line
- All filters work (level, regex, time, field)
- Press `q` to quit after viewing

**Status Bar:**
- Shows filename when no PostgreSQL instance detected: `FOLLOW | E:0 W:0 | 42 lines | postmaster.log`
- Shows `PGversion:port` if detected from log content: `FOLLOW | E:0 W:0 | 42 lines | PG17:5432`

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

### Connection Statistics

Track connection and disconnection events from PostgreSQL logs:

```
connections                    Show summary with active count by database/user/app
connections --history          Sparkline of connect/disconnect rate (last 60 min)
connections --watch            Live stream of connection events (Ctrl+C to exit)
connections --db=mydb          Filter by database name
connections --user=postgres    Filter by user name
connections --app=psql         Filter by application name
connections clear              Reset all statistics
```

Requires PostgreSQL connection logging to be enabled:
```sql
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;
SELECT pg_reload_conf();
```

Example output:
```
pgtail> connections
Active connections: 5

By database:
  mydb              3
  postgres          2

By user:
  postgres          4
  app_user          1

By application:
  psql              3
  pgcli             2

Session totals: 12 connects, 7 disconnects

pgtail> connections --watch
Watching connections - postgresql.log (Ctrl+C to exit)
[+] connect  [-] disconnect  [!] failed

[+] 14:30:15  postgres@mydb (psql) from [local]
[-] 14:30:18  postgres@mydb (psql) from [local] (3.2s)
[+] 14:30:22  app_user@production (rails) from 192.168.1.100

pgtail> connections --history
Connection History (last 60 min, 15-min buckets)
─────────────────────────────────────────────────

  Connects:    ▂▃▅▇  total 45
  Disconnects: ▂▂▄▆  total 40

  Net change: +5 (connections growing)
  Active now: 5
```

### Desktop Notifications

Get desktop alerts for critical PostgreSQL events:

```
notify                         Show current notification settings
notify on FATAL PANIC          Enable for specific log levels
notify on ERROR WARNING        Add more levels to notify on
notify on /deadlock/i          Enable for regex pattern (case-insensitive)
notify on /timeout/            Enable for regex pattern (case-sensitive)
notify on errors > 10/min      Alert when error rate exceeds threshold
notify on slow > 500ms         Alert when queries exceed duration
notify off                     Disable all notifications
notify test                    Send a test notification
notify quiet 22:00-08:00       Suppress notifications during quiet hours
notify quiet off               Disable quiet hours
notify clear                   Remove all notification rules
```

Features:
- **Rate limiting**: Max 1 notification per 5 seconds to prevent spam during incidents
- **Quiet hours**: Suppress notifications during configured time ranges (handles overnight spans like 22:00-08:00)
- **Multiple triggers**: Combine level-based, pattern-based, and threshold-based rules
- **Cross-platform**: macOS (osascript), Linux (notify-send), Windows (PowerShell toast)

Example output:
```
pgtail> notify
Notifications: enabled
  Levels: FATAL, PANIC
  Patterns: /deadlock/i
  Slow queries: > 500ms
  Quiet hours: 22:00-08:00
Platform: macOS (osascript)

pgtail> notify test
Test notification sent
Platform: macOS (osascript)
```

### Color Themes

Customize log output colors with built-in or custom themes:

```
theme                      Show current theme
theme <name>               Switch theme (dark, light, monokai, etc.)
theme list                 Show all available themes
theme preview <name>       Preview a theme with sample output
theme edit <name>          Create or edit a custom theme
theme reload               Reload current theme after external edits
```

**Built-in themes:**

| Theme | Best For |
|-------|----------|
| `dark` | Dark terminal backgrounds (default) |
| `light` | Light terminal backgrounds |
| `high-contrast` | Accessibility, bright displays |
| `monokai` | Developers familiar with editor theme |
| `solarized-dark` | Dark terminals, reduced eye strain |
| `solarized-light` | Light terminals, reduced eye strain |

**Custom themes:**

Create custom themes as TOML files:
- **macOS**: `~/Library/Application Support/pgtail/themes/mytheme.toml`
- **Linux**: `~/.config/pgtail/themes/mytheme.toml`
- **Windows**: `%APPDATA%/pgtail/themes/mytheme.toml`

```toml
[meta]
name = "My Theme"
description = "Custom colors"

[levels]
PANIC = { fg = "white", bg = "red", bold = true }
FATAL = { fg = "red", bold = true }
ERROR = { fg = "#ff6b6b" }
WARNING = { fg = "#ffd93d" }
LOG = { fg = "default" }

[ui]
timestamp = { fg = "gray" }
highlight = { bg = "yellow", fg = "black" }
```

Color formats: ANSI names (`ansired`), hex codes (`#ff6b6b`), CSS names (`DarkRed`)

To disable all colors: `NO_COLOR=1 pgtail`

### SQL Syntax Highlighting

SQL statements in log messages are automatically highlighted with distinct colors for each element:

| Element | Default Color | Example |
|---------|--------------|---------|
| Keywords | Blue (bold) | `SELECT`, `FROM`, `WHERE`, `JOIN` |
| Identifiers | Cyan | `users`, `created_at` |
| Strings | Green | `'hello world'`, `$$body$$` |
| Numbers | Magenta | `42`, `3.14` |
| Operators | Yellow | `=`, `<>`, `||`, `::` |
| Comments | Gray | `-- comment`, `/* block */` |
| Functions | Blue | `COUNT()`, `NOW()` |

SQL is detected in log messages containing:
- `LOG: statement:` - Statement logging
- `LOG: execute <name>:` - Prepared statement execution
- `LOG: duration: ... statement:` - Query timing with SQL
- `DETAIL:` - Error context details

Example output (colors shown as `[color]`):
```
10:23:45 [12345] LOG: statement: [blue]SELECT[/] [cyan]id[/], [cyan]name[/] [blue]FROM[/] [cyan]users[/] [blue]WHERE[/] [cyan]active[/] [yellow]=[/] [green]'yes'[/]
```

SQL highlighting:
- Respects current theme colors (each theme defines SQL colors)
- Gracefully handles malformed SQL (highlights what it can recognize)
- Disabled when `NO_COLOR=1` is set

Custom theme SQL colors can be defined in TOML:
```toml
[ui]
sql_keyword = { fg = "blue", bold = true }
sql_identifier = { fg = "cyan" }
sql_string = { fg = "green" }
sql_number = { fg = "magenta" }
sql_operator = { fg = "yellow" }
sql_comment = { fg = "gray" }
sql_function = { fg = "blue" }
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
- `theme.name` - Color theme (dark, light, high-contrast, monokai, solarized-dark, solarized-light, or custom)
- `notifications.enabled` - Enable/disable desktop notifications
- `notifications.levels` - Log levels that trigger notifications
- `notifications.patterns` - Regex patterns that trigger notifications
- `notifications.error_rate` - Error rate threshold (errors per minute)
- `notifications.slow_query_ms` - Slow query threshold in milliseconds
- `notifications.quiet_hours` - Time range to suppress notifications (e.g., `22:00-08:00`)

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

## Tail Mode

When you run `tail <id>`, pgtail enters a Textual-based split-screen interface:

```
┌─────────────────────────────────────────────────────────────┐
│ q Quit   ? Help   / Cmd   v Visual   y Yank   p Pause   ... │
├─────────────────────────────────────────────────────────────┤
│ Log output area (scrollable, vim navigation, visual mode)   │
│ 10:23:45.123 [12345] LOG    : statement: SELECT 1           │
│ 10:23:46.456 [12345] ERROR   42P01: relation "foo" ...      │
│ ...                                                         │
├─────────────────────────────────────────────────────────────┤
│ tail> level error+                                          │
├─────────────────────────────────────────────────────────────┤
│ FOLLOW | E:2 W:0 | 150 lines | levels:ERROR | PG16:5432     │
└─────────────────────────────────────────────────────────────┘
```

**Status bar:**
- `FOLLOW` (green) / `PAUSED +N new` (yellow) - Auto-scrolling or frozen display
- `E:X W:Y` - Error and warning counts (respects active filters)
- `N lines` - Entry count (respects active filters)
- Active filters: `levels:`, `filter:/pattern/`, `since:`, `slow:>`
- PostgreSQL version and port

**Navigation keys (vim-style):**

| Key | Action |
|-----|--------|
| j / k | Scroll down/up one line |
| g | Go to top |
| G | Go to bottom (resume FOLLOW mode) |
| Ctrl+d / Ctrl+u | Half page down/up |
| Ctrl+f / Ctrl+b | Full page down/up |
| PgDn / PgUp | Full page down/up |
| p | Pause (freeze display) |
| f | Resume FOLLOW mode |
| q | Exit tail mode |
| ? | Show help overlay |
| / | Focus command input |
| Tab | Toggle focus between log and input |

**Visual mode (text selection):**

| Key | Action |
|-----|--------|
| v | Enter character-wise visual mode |
| V | Enter line-wise visual mode |
| h / l | Move cursor left/right |
| 0 / $ | Move to line start/end |
| y | Yank (copy) selection and exit visual mode |
| Escape | Clear selection and exit visual mode |
| Ctrl+a | Select all content |
| Ctrl+c | Copy current selection |

Text is copied to clipboard using OSC 52 (terminal clipboard) with pyperclip fallback.
Mouse drag selection auto-copies to clipboard on release.

**Commands in tail mode:**

| Command | Action |
|---------|--------|
| `level <levels>` | Filter by level (see Level Filter Syntax below) |
| `filter /pattern/[i]` | Filter by regex (i = case-insensitive) |
| `since <time>` | Filter by time (e.g., `since 5m`, `since 14:30`) |
| `until <time>` | Filter until time |
| `between <s> <e>` | Filter time range |
| `slow <ms>` | Set slow query threshold |
| `clear` | Reset to initial filters |
| `clear force` | Clear all filters |
| `errors` | Show error statistics |
| `connections` | Show connection statistics |
| `pause` / `p` | Enter PAUSED mode |
| `follow` / `f` | Resume FOLLOW mode |
| `help` | Show all commands |
| `help keys` | Show keybinding reference |
| `help <cmd>` | Show command-specific help |
| `stop` / `q` | Exit tail mode |

**Level filter syntax:**
- `level error` - Exact match (ERROR only)
- `level error+` - ERROR and more severe (FATAL, PANIC)
- `level warning-` - WARNING and less severe (NOTICE, LOG, INFO, DEBUG)
- `level error,warning` - Multiple exact levels
- Abbreviations: `e`=error, `w`=warning, `f`=fatal, `p`=panic, `n`=notice, `i`=info, `l`=log, `d`=debug

Examples:
```
level e+         # ERROR, FATAL, PANIC
level w          # WARNING only
level e,w,f      # ERROR, WARNING, FATAL
level all        # Clear level filter (show all)
```

## Keyboard Shortcuts (REPL)

| Key | Action |
|-----|--------|
| Tab | Autocomplete |
| Up/Down | Command history |
| Ctrl+C | Stop current tail |
| Ctrl+D | Exit pgtail |

## Troubleshooting

### macOS: Binary won't run (Gatekeeper)

macOS blocks unsigned binaries downloaded from the internet. Remove the quarantine flag from the extracted folder:

```bash
xattr -dr com.apple.quarantine pgtail-macos-arm64/
```

Or: **System Preferences → Security & Privacy → General → Allow Anyway**

### macOS: Wrong architecture binary

If you see `Bad CPU type in executable`, download the correct archive:
- Apple Silicon (M1/M2/M3): `pgtail-macos-arm64.tar.gz`
- Intel Mac: `pgtail-macos-x86_64.tar.gz`

Check your architecture: `uname -m` (arm64 or x86_64)

### Windows: SmartScreen warning

Windows SmartScreen may block the executable. Click **"More info"** → **"Run anyway"**.

For the MSI installer, you may also see this warning during installation.

### Windows: Antivirus blocking dependencies

Some antivirus software may flag the bundled Python libraries. If pgtail fails to start:

1. Add the pgtail folder to your antivirus exclusions
2. Or use the MSI installer (signed with Microsoft's requirements)

### Linux: Wrong architecture binary

If you see `cannot execute binary file: Exec format error`, download the correct archive:
- x86_64 (Intel/AMD): `pgtail-linux-x86_64.tar.gz`
- ARM64 (Raspberry Pi 4, AWS Graviton): `pgtail-linux-arm64.tar.gz`

Check your architecture: `uname -m` (x86_64 or aarch64)

### Missing dependency folder

pgtail requires its dependency folder to run. If you see errors about missing libraries:

- Ensure the entire folder was extracted (not just the `pgtail` executable)
- The executable must remain in its folder with all `.so`/`.dylib`/`.dll` files
- Do not move only the executable; move the entire folder

### Update check fails

If `pgtail --check-update` shows "Unable to check for updates":
- Check your internet connection
- The GitHub API may be rate-limited (60 requests/hour for unauthenticated users)
- No releases exist yet (404 is handled silently)

### Binary updates

Pre-built archives do not auto-update. To update:
1. Download the new version from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest)
2. Extract and replace the old folder
3. On macOS, you may need to remove the quarantine flag again
4. Update any symlinks if you created them

### Unsupported platform/architecture

If your platform/architecture is not listed, you can compile from source:

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
pip install -e .
# Or build a standalone binary with Nuitka:
pip install nuitka
make build
```

### Download interrupted

If a download is interrupted, delete the partial file and re-download. Browsers typically do not resume partial downloads for these archives.

### Repository access error

If pip/pipx/uv install fails with authentication errors:
- Ensure the repository URL is correct: `git+https://github.com/willibrandon/pgtail.git`
- Check if the repository is public (no authentication required)
- Try using HTTPS instead of SSH

## Requirements

- Python 3.10+
- prompt_toolkit (REPL with autocomplete)
- textual >=0.89.0 (tail mode UI)
- pyperclip (clipboard support)
- psutil (process detection)
- tomlkit (config file support)

## License

MIT
