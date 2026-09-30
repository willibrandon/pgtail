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

- Auto-detects PostgreSQL instances (running processes, pgrx, PGDATA, known paths), including Debian and Ubuntu clusters
  and their `/var/log/postgresql` logs
- **Tail arbitrary log files** (`--file`) with glob patterns and multi-file support
- **Stdin pipe support** (`--stdin`) for archived/compressed logs
- Auto-detects log format (text, csvlog, jsonlog) and parses structured fields
- Real-time log tailing with polling (handles log rotation and PostgreSQL restarts)
- **Full screen tail mode** with split-screen interface (header, log, input, status bar)
- **Vim-style navigation** (j/k, g/G, Ctrl+d/u/f/b, p/f for pause/follow) and mouse scrolling, clicking, and dragging
- **Visual mode selection** (v/V for character/line mode, y to yank, Ctrl+a/c)
- **Clipboard support** via OSC 52 terminal escape plus the platform clipboard (pbcopy, clip.exe, wl-copy, xclip, xsel)
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
- **Semantic highlighting** - 30 built-in highlighters for timestamps, durations, SQLSTATE codes, WAL, locks, and more
- Color-coded output by severity with SQL state codes
- **Command history** in tail mode with Up/Down arrow recall (persists across sessions)
- **Ghost text autocomplete** in tail mode with context-aware suggestions for commands, arguments, and flags
- REPL with autocomplete, command history, and **bottom toolbar** (instance count, filters, theme)
- **Shell mode** (`!` prefix) with clear toolbar indicator
- **Built-in editor** for the configuration file and custom themes, with TOML highlighting and checks before saving
- Cross-platform (macOS, Linux, Windows), a single native executable built with .NET Native AOT and [Hex1b](https://github.com/mitchdenny/hex1b)

## Installation

### .NET tool

```bash
dotnet tool install -g pgtail
```

The tool installs the native executable for your platform (Windows, Linux, and macOS on x64 and Arm64), and a
framework-dependent build that needs the .NET 10 runtime anywhere else.

### Homebrew (macOS / Linux)

```bash
brew tap willibrandon/tap
brew install pgtail
```

### winget (Windows)

```powershell
winget install willibrandon.pgtail
```

### Scoop (Windows)

```powershell
scoop bucket add willibrandon https://github.com/willibrandon/scoop-bucket
scoop install pgtail
```

### Binary Download

Download pre-built archives from [GitHub Releases](https://github.com/willibrandon/pgtail/releases/latest). Each holds a
native executable (with Hex1b's small console helper beside it on macOS and Linux); nothing else needs to be installed.

| Platform | Archive |
|----------|---------|
| macOS (Apple Silicon) | `pgtail-macos-arm64.tar.gz` |
| macOS (Intel) | `pgtail-macos-x86_64.tar.gz` |
| Linux (x86_64) | `pgtail-linux-x86_64.tar.gz` |
| Linux (ARM64) | `pgtail-linux-arm64.tar.gz` |
| Windows (x86_64) | `pgtail-windows-x86_64.zip` or `.msi` |
| Windows (ARM64) | `pgtail-windows-arm64.zip` |

**macOS / Linux:**
```bash
# Extract the archive
tar -xzf pgtail-macos-arm64.tar.gz

# Run pgtail from the extracted folder
./pgtail-macos-arm64/pgtail --version

# Optional: Add to PATH (keep the folder together; the helper library sits beside the executable)
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

pgtail needs the [.NET 10 SDK](https://dotnet.microsoft.com/download).

```bash
git clone https://github.com/willibrandon/pgtail.git
cd pgtail
dotnet build
dotnet test
dotnet run --project src/Pgtail
```

Publish a native executable for your machine (on the machine it targets):

```bash
dotnet publish src/Pgtail -c Release -r linux-x64 -o out
./out/pgtail --version
```

`scripts/Publish-NativeAot.cs` publishes, checks, and packs a runtime as the release does; see `scripts/README.md`.

### Installation Summary

| Method | Platforms | Auto-Update | Notes |
|--------|-----------|-------------|-------|
| .NET tool | All | `dotnet tool update -g pgtail` | Native executable per platform |
| Homebrew | macOS, Linux | `brew upgrade` | |
| winget | Windows | `winget upgrade` | |
| Scoop | Windows | `scoop update` | Portable install |
| MSI | Windows | Manual | Admin required, adds to PATH |
| ZIP/tar.gz | All | Manual | Portable, extract and run |

## Upgrading

Check for available updates:
```bash
pgtail --check-update
```

Upgrade commands by installation method:

| Method | Upgrade Command |
|--------|-----------------|
| .NET tool | `dotnet tool update -g pgtail` |
| Homebrew | `brew upgrade pgtail` |
| winget | `winget upgrade willibrandon.pgtail` |
| Scoop | `scoop update pgtail` |
| Binary | Re-download from [releases](https://github.com/willibrandon/pgtail/releases/latest) |

pgtail checks for updates automatically on startup (once per 24 hours) and suggests the upgrade command for the way it
was installed. Disable the check with:
```bash
pgtail set updates.check false
```

## Usage

```bash
pgtail                      # Interactive REPL
pgtail list                 # List detected instances (alias of list-instances)
pgtail tail 0               # Full screen tail mode for instance 0
pgtail tail 0 --stream      # Print entries to standard output instead
pgtail enable-logging 0     # Turn on logging_collector for an instance
pgtail config --edit        # Edit the configuration in the built-in editor
```

### Shell Completion

pgtail supports shell completion for commands and PostgreSQL instance IDs. Tab completion shows available instances with version, port, and status:

```bash
$ pgtail tail <TAB>
0  -- PG17:5432 (running)
1  -- PG16:5433 (stopped)
```

Enable shell completion (auto-detects your current shell; bash, zsh, fish, and PowerShell are supported):

```bash
pgtail --install-completion
pgtail --show-completion zsh    # Print the script to install it yourself
```

After installation, restart your shell or source your shell's config file.

### Commands

```
list               Show detected PostgreSQL instances
tail <id>          Tail logs for an instance in full screen tail mode (supports --since)
tail --file <path> Tail arbitrary log file(s) (glob patterns, multiple files)
tail --stdin       Read log data from stdin pipe
tail ... --stream  Print entries in the REPL instead (Ctrl+C pauses, 'stop' ends)
levels [LEVEL...]  Set log level filter (no args = show current, ALL = clear; also 'level')
since <time>       Filter logs since time (e.g., 5m, 14:30, 2024-01-15T14:30)
until <time>       Filter logs until time
between <s> <e>    Filter logs in time range (e.g., between 14:30 15:00)
filter /pattern/   Regex filter (see Filtering below)
filter field=value Filter by field (app=, db=, user=) for CSV/JSON logs
display [mode]     Set display mode (compact, full, fields <f1,f2,...>)
output [format]    Set output format (text, json)
highlight          Manage semantic highlighters (see Semantic Highlighting below)
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
!<cmd>             Run shell command (through your shell, so pipes and quoting work)
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
zcat archived.log.gz | pgtail tail --stdin --stream | grep deadlock   # Filtered, to standard output

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
- All data buffered before displaying (allows keyboard navigation); with `--stream`, entries print as they are read
- Without a terminal for the keyboard (for example under cron), use `--stream`
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
| TEXT   | `log_destination = 'stderr'` | Basic (timestamp, pid, level, message; user and database with Debian's `%u@%d` prefix) |
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

To process entries as JSON with `jq`, pipe them from the REPL:
```
pipe --format json jq '.message'
```

`pgtail tail ... --stream` writes one entry per line with no status lines when its output is piped, so it also works
with `grep` and friends:
```bash
pgtail tail 0 --stream | grep deadlock
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

pgtail provides automatic semantic highlighting for PostgreSQL log patterns. See [Semantic Highlighting](#semantic-highlighting) for the full command reference.

Quick examples:
```
highlight /pattern/       Highlight text matching a regex (REPL)
highlight                 Show all highlighters and their status
highlight preview         Preview highlighting with sample log lines
highlight disable duration   Disable duration highlighting
highlight add req_id "REQ-\d+" --style cyan   Add custom pattern
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
- **Only new entries**: history read back by `--since` never notifies
- **No spam during incidents**: at most 1 notification per 5 seconds; alerts in between arrive as one summary, and a
  message repeated within a minute is counted instead of shown again
- **Quiet hours**: Suppress notifications during configured time ranges (handles overnight spans like 22:00-08:00)
- **Multiple triggers**: Combine level-based, pattern-based, and threshold-based rules
- **Cross-platform**: macOS (osascript), Linux (notify-send), Windows (WinRT toast)

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

`theme edit <name>` opens the theme in the built-in editor, starting from a template, and checks it before saving.
Themes are TOML files:
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

### Semantic Highlighting

Beyond SQL, pgtail automatically colorizes meaningful patterns throughout PostgreSQL log messages. 30 built-in highlighters recognize timestamps, PIDs, SQLSTATE codes, durations, identifiers, WAL segments, lock types, and more.

**Commands:**

```
highlight                     Show global status and list all highlighters
highlight list                Same as above
highlight on                  Enable all highlighting globally
highlight off                 Disable all highlighting globally
highlight enable <name>       Enable a specific highlighter
highlight disable <name>      Disable a specific highlighter
highlight add <name> <pattern> [--style <style>]  Add custom regex highlighter
highlight remove <name>       Remove custom highlighter
highlight preview             Preview all highlighters with sample output
highlight reset               Reset all settings to defaults
highlight export [--file <path>]  Export config as TOML
highlight import <path>       Import config from TOML file
```

**Built-in highlighter categories:**

| Category | Highlighters | Examples |
|----------|--------------|----------|
| Structural | timestamp, pid, context | `2024-01-15 14:30:45.123 UTC`, `[12345]`, `DETAIL:` |
| Diagnostic | sqlstate, error_name | `23505`, `unique_violation` |
| Performance | duration, memory, statistics | `150.234 ms`, `1024 MB` |
| Objects | identifier, relation, schema | `"users_pkey"`, `public.users` |
| WAL | lsn, wal_segment, txid | `0/1234ABCD`, `000000010000000000000001` |
| Connection | connection, ip, backend | `host=192.168.1.1`, `autovacuum launcher` |
| SQL | sql_keyword, sql_string, sql_number | `SELECT`, `'hello'`, `42` |
| Lock | lock_type, lock_wait | `ShareLock`, `waiting for ExclusiveLock` |
| Checkpoint | checkpoint, recovery | `checkpoint starting`, `redo done at` |

**Duration threshold coloring:**

Query durations are colored based on configurable thresholds:
- Fast (< 100ms): Default color
- Slow (100-499ms): Yellow
- Very slow (500-4999ms): Orange
- Critical (≥ 5000ms): Red, bold

Configure thresholds in `config.toml`:
```toml
[highlighting.duration]
slow = 100        # ms
very_slow = 500   # ms
critical = 5000   # ms
```

**Custom highlighters:**

Add your own regex patterns:
```
highlight add request_id "REQ-[A-Z]{3}-\d{6}" --style "cyan"
highlight add txn_id "TXN:[0-9a-f]{16}" --style "bold magenta"
highlight remove request_id
```

**Export/import configuration:**
```
highlight export --file ~/highlight.toml   # Save current config
highlight import ~/highlight.toml          # Load config from file
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
export --highlighted color.log Keep colors as ANSI escapes (view with less -R)
```

Formats:
- **text**: Log lines as written by PostgreSQL (default)
- **json**: JSON Lines format, one object per line
- **csv**: CSV with timestamp, level, pid, message columns

### Pipe

Pipe filtered log entries to external commands:

```
pipe wc -l                     Count matching entries
pipe grep "SELECT"             Filter with grep
pipe --format json jq '.message'  Process JSON with jq
pipe head -20 | sort           Pipelines and quoting work: the command runs through your shell
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
config edit                Edit in the built-in editor (checked before saving)
config reset               Reset to defaults (creates backup)
```

Available settings:
- `default.levels` - Default log level filter (e.g., `ERROR WARNING`)
- `slow.warn`, `slow.error`, `slow.critical` - Threshold values in ms
- `theme.name` - Color theme (dark, light, high-contrast, monokai, solarized-dark, solarized-light, or custom)
- `notifications.enabled` - Enable/disable desktop notifications
- `notifications.levels` - Log levels that trigger notifications
- `notifications.patterns` - Regex patterns that trigger notifications
- `notifications.error_rate` - Error rate threshold (errors per minute)
- `notifications.slow_query_ms` - Slow query threshold in milliseconds
- `notifications.quiet_hours` - Time range to suppress notifications (e.g., `22:00-08:00`)
- `updates.check` - Check for a newer release at startup (default `true`)
- `highlighting.enabled`, `highlighting.max_length` - Semantic highlighting on/off and the longest message it colors
- `highlighting.duration.slow`, `.very_slow`, `.critical` - Duration coloring thresholds in ms
- `highlighting.enabled_highlighters.<name>` - Turn one built-in highlighter on or off

### Example

```
pgtail> list
  #  VERSION  PORT   STATUS   LOG  SOURCE  DATA DIRECTORY
  0  16       5432   running  on   process ~/.pgrx/data-16

pgtail> tail 0 --stream
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

When you run `tail <id>`, pgtail enters a full screen split-screen interface on the terminal's alternate screen, and
returns to the REPL, with your scrollback intact, when you leave:

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
| q | Exit tail mode (in the command input, `q` and Enter) |
| ? | Show help overlay |
| / | Focus command input |
| Tab | Toggle focus between log and input |
| Mouse wheel | Scroll (Shift+wheel scrolls sideways) |
| Click | Select a line |

Moving off the newest line stops following and shows `PAUSED`; returning to the end resumes. Long lines scroll sideways
to keep the cursor in view.

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

Text is copied to the clipboard with OSC 52 (the terminal's clipboard) and the platform's clipboard tool.
Mouse drag selection auto-copies to clipboard on release.

**Command input (history & autocomplete):**

The `tail>` command prompt has the focus when tail mode starts and keeps it after each command, so commands can be typed
one after another; text typed on the log that is not one of its keys goes to the prompt too. A command's output, such as
`help`, is written into the log.

| Key | Action |
|-----|--------|
| Enter | Run the command |
| Up | Recall previous command from history |
| Down | Navigate forward through history |
| Right / End | Accept ghost text suggestion |
| PgUp / PgDn | Scroll the log a page |
| Escape | Clear the prompt and move to the log |

- **Command history** persists across sessions (Up/Down arrows to navigate)
- **Ghost text autocomplete** shows dimmed suggestions as you type:
  - Command names (e.g., type `lev` to see `level` suggested)
  - Arguments and flags based on command context (e.g., `level err` → `error`)
  - Subcommands (e.g., `highlight ` → `add`, `disable`, `enable`, etc.)
  - Falls back to history prefix search when no structural match exists

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
| `highlight ...` | Manage semantic highlighters |
| `export <file>` | Export the displayed entries |
| `set <key> <value>` | Change a setting |
| `theme <name>` | Switch theme |
| `notify ...` | Configure desktop notifications |
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
| Tab / Shift+Tab | Autocomplete, cycling through the menu |
| Up/Down | Completion menu, or command history |
| `!` | Enter shell mode (with empty prompt) |
| Escape | Close the completion menu, or exit shell mode |
| Ctrl+C | Abandon the line; while streaming, pause output |
| Ctrl+L | Clear the screen |
| Ctrl+R | Search history backward (Ctrl+R again for older; Enter runs, Escape edits, Ctrl+G cancels) |
| Ctrl+A / Ctrl+E | Start / end of the line (also in tail mode's command input) |
| Ctrl+B / Ctrl+F, Alt+B / Alt+F | Back / forward a character, a word |
| Ctrl+K / Ctrl+U / Ctrl+W / Alt+D | Cut to the end, to the start, the word before, the word after |
| Ctrl+Y | Paste the last cut text |
| Ctrl+D | Exit pgtail |

## REPL Bottom Toolbar

The REPL displays a persistent bottom toolbar showing current state:

```
 7 instances • levels:ERROR,WARNING filter:/deadlock/i • Theme: monokai
```

**Toolbar sections:**
- **Instance count**: Number of detected PostgreSQL instances, or "No instances (run 'refresh')" warning
- **Active filters**: Level filters, regex patterns, time filters, slow query thresholds
- **Theme**: Currently active color theme

**Shell mode indicator:**

When you press `!` with an empty prompt to enter shell mode, the toolbar changes to:
```
 SHELL • Press Escape to exit
```

The toolbar updates automatically when you change filters, switch themes, or refresh instances.

## License

MIT
