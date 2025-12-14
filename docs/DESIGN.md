# pgtail Design Document

A cross-platform interactive CLI tool for discovering PostgreSQL instances and tailing their log files.

## Problem Statement

PostgreSQL log files are notoriously difficult to locate. Their location varies based on:

- Installation method (package manager, source, installer, pgrx)
- Operating system (Linux, macOS, Windows)
- Configuration (`log_directory`, `log_destination` settings)
- Instance management (system service, manual, pgrx test instances)

Developers working with multiple PostgreSQL instances—especially those doing extension development with pgrx—waste time hunting for log files across different locations.

## Goals

1. **Auto-detect** all PostgreSQL instances on the local machine (running and dormant)
2. **Cross-platform** support for Linux, macOS, and Windows
3. **Interactive** experience with autocomplete, history, and color-coded output
4. **Simple** command set that's easy to remember
5. **Zero configuration** required for common setups

## Non-Goals

- Remote PostgreSQL instance log viewing
- Log aggregation or persistence
- Log parsing/analysis beyond basic filtering
- PostgreSQL administration features

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         main.go                             │
│                    (entry point, REPL)                      │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   detector.go   │ │   executor.go   │ │    completer.go     │
│                 │ │                 │ │                     │
│ - Process scan  │ │ - Command parse │ │ - Command suggest   │
│ - Path scan     │ │ - Dispatch      │ │ - Instance suggest  │
│ - Config parse  │ │ - State mgmt    │ │ - Level suggest     │
└─────────────────┘ └─────────────────┘ └─────────────────────┘
              │               │
              ▼               ▼
┌─────────────────┐ ┌─────────────────┐
│   instance.go   │ │    tailer.go    │
│                 │ │                 │
│ - Instance type │ │ - File tailing  │
│ - Log location  │ │ - Level filter  │
│ - Metadata      │ │ - Color output  │
└─────────────────┘ └─────────────────┘
```

### Package Structure

```
pgtail/
├── cmd/
│   └── pgtail/
│       └── main.go         # Entry point
├── internal/
│   ├── detector/
│   │   ├── detector.go     # Main detection orchestration
│   │   ├── process.go      # Running process detection
│   │   ├── paths.go        # Known path scanning
│   │   └── config.go       # postgresql.conf parsing
│   ├── instance/
│   │   └── instance.go     # PostgreSQL instance representation
│   ├── tailer/
│   │   ├── tailer.go       # Log file tailing
│   │   ├── parser.go       # Log line parsing
│   │   └── filter.go       # Level filtering
│   └── repl/
│       ├── repl.go         # REPL setup
│       ├── executor.go     # Command execution
│       └── completer.go    # Autocomplete
├── docs/
│   └── DESIGN.md           # This document
├── go.mod
├── go.sum
└── README.md
```

## Instance Detection

### Detection Sources

Detection runs in priority order, with deduplication by data directory path:

#### 1. Running Processes (Highest Priority)

Detect currently running PostgreSQL instances by examining process arguments.

**Unix (Linux/macOS):**
```bash
ps aux | grep '[p]ostgres.*-D'
```

Extract the `-D /path/to/data` argument from postmaster processes.

**Windows:**
```powershell
Get-WmiObject Win32_Process -Filter "Name='postgres.exe'" | Select CommandLine
# Or: wmic process where "name='postgres.exe'" get commandline
```

Parse `-D` argument or `--data-dir` from command line.

#### 2. pgrx Data Directories

Scan the pgrx home directory for managed instances:

| Platform | Path |
|----------|------|
| Unix | `~/.pgrx/data-{version}/` |
| Windows | `%USERPROFILE%\.pgrx\data-{version}\` |

#### 3. Common Installation Paths

**Linux (Debian/Ubuntu):**
```
/var/lib/postgresql/{version}/main/
/etc/postgresql/{version}/main/
```

**Linux (RHEL/CentOS/Fedora):**
```
/var/lib/pgsql/{version}/data/
/var/lib/pgsql/data/
```

**macOS (Homebrew):**
```
/opt/homebrew/var/postgresql@{version}/
/usr/local/var/postgresql@{version}/
/opt/homebrew/var/postgres/
/usr/local/var/postgres/
```

**macOS (Postgres.app):**
```
~/Library/Application Support/Postgres/var-{version}/
```

**Windows:**
```
C:\Program Files\PostgreSQL\{version}\data\
C:\Program Files (x86)\PostgreSQL\{version}\data\
%PROGRAMDATA%\PostgreSQL\{version}\data\
```

#### 4. Environment Variables

Check `PGDATA` environment variable if set.

#### 5. Service Registration (Platform-Specific)

**Linux (systemd):**
```bash
systemctl list-units --type=service | grep postgres
# Parse ExecStart for -D flag
```

**macOS (launchd):**
```bash
launchctl list | grep postgres
# Check plist for data directory
```

**Windows (Services):**
```powershell
Get-Service -Name "postgresql*" | Get-WmiObject Win32_Service
# Parse PathName for -D flag
```

### Log File Location

Once a data directory is identified, locate logs:

1. **Check `postgresql.conf`** for:
   - `log_directory` (default: `log` or `pg_log`)
   - `log_filename` (default: `postgresql-%Y-%m-%d_%H%M%S.log`)
   - `log_destination` (stderr, csvlog, syslog, eventlog)

2. **Scan standard locations:**
   - `{data_dir}/log/`
   - `{data_dir}/pg_log/`

3. **Handle special cases:**
   - **syslog:** Point to `/var/log/syslog` or `/var/log/messages` (Linux)
   - **eventlog:** Windows Event Viewer (Application log, source "PostgreSQL")
   - **csvlog:** Parse CSV format logs

### Instance Metadata

Each detected instance includes:

```go
type Instance struct {
    DataDir     string            // Absolute path to data directory
    Version     string            // PostgreSQL version (e.g., "16.1")
    Port        int               // Listening port (from postgresql.conf or postmaster.pid)
    Running     bool              // Whether postmaster is currently running
    LogDir      string            // Resolved log directory path
    LogPattern  string            // Log filename pattern
    Source      DetectionSource   // How this instance was detected
}

type DetectionSource int

const (
    SourceProcess DetectionSource = iota
    SourcePgrx
    SourceKnownPath
    SourceEnvVar
    SourceService
)
```

## Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `list` | Show all detected PostgreSQL instances |
| `refresh` | Re-scan for instances |
| `tail <id\|path>` | Tail logs for specified instance |
| `follow <id\|path>` | Alias for `tail` |
| `stop` | Stop current tail operation |
| `levels [LEVEL...]` | Set log level filter (persists across tails) |
| `clear` | Clear screen |
| `help` | Show available commands |
| `quit` / `exit` | Exit pgtail |

### Command Details

#### `list`

Display detected instances in a table:

```
pgtail> list

  #  VERSION  PORT   STATUS   SOURCE  DATA DIRECTORY
  0  16.1     5432   running  pgrx    ~/.pgrx/data-16
  1  15.4     5433   running  pgrx    ~/.pgrx/data-15
  2  14.9     5434   stopped  brew    /opt/homebrew/var/postgresql@14
```

#### `tail <id|path>`

Begin tailing logs for the specified instance. Accepts:
- Numeric index from `list` output
- Full or partial data directory path
- Fuzzy match on path components

```
pgtail> tail 0
[Following: ~/.pgrx/data-16/log/postgresql-2024-01-15.log]
[Press Ctrl+C to stop]

2024-01-15 10:23:45.123 PST [12345] LOG:  statement: SELECT 1
2024-01-15 10:23:45.456 PST [12345] ERROR:  relation "foo" does not exist
```

#### `levels [LEVEL...]`

Filter output to specific log levels:

```
pgtail> levels ERROR WARNING
[Filter set: ERROR, WARNING]

pgtail> levels
[Filter cleared - showing all levels]
```

Supported levels: `DEBUG5`, `DEBUG4`, `DEBUG3`, `DEBUG2`, `DEBUG1`, `INFO`, `NOTICE`, `WARNING`, `ERROR`, `LOG`, `FATAL`, `PANIC`

## User Interface

### go-prompt Integration

Use [go-prompt](https://github.com/c-bata/go-prompt) for the interactive REPL:

- **Autocomplete:** Commands, instance paths, log levels
- **History:** Command history with Up/Down navigation
- **Colors:** Syntax highlighting for commands and output

### Live Prefix

Show current state in the prompt:

```
pgtail> list
...

pgtail[0]> tail 0
[Following ~/.pgrx/data-16]

pgtail[0:ERR,WARN]> levels ERROR WARNING
[Filter updated]
```

Format: `pgtail[instance:filters]>`

### Log Output Coloring

| Level | Color |
|-------|-------|
| PANIC, FATAL | Red, Bold |
| ERROR | Red |
| WARNING | Yellow |
| NOTICE | Cyan |
| LOG | Default |
| INFO | Green |
| DEBUG* | Dark Gray |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Tab | Autocomplete |
| Up/Down | History navigation |
| Ctrl+C | Stop current tail / Clear input |
| Ctrl+D | Exit (when input empty) |
| Ctrl+L | Clear screen |

## Platform-Specific Considerations

### Windows

1. **Path separators:** Use `filepath` package for cross-platform path handling
2. **Process detection:** Use `wmic` or WMI API via `github.com/yusufpapurcu/wmi`
3. **Terminal colors:** Use `github.com/fatih/color` which handles Windows console
4. **File tailing:** Use polling-based approach (fsnotify has Windows limitations)
5. **Event Log:** Support Windows Event Viewer as a log destination
   - Use `golang.org/x/sys/windows/svc/eventlog` for reading

### macOS

1. **SIP restrictions:** Some system paths may not be accessible
2. **Homebrew paths:** Check both `/opt/homebrew` (Apple Silicon) and `/usr/local` (Intel)
3. **Postgres.app:** Check `~/Library/Application Support/Postgres/`

### Linux

1. **Permissions:** May need elevated privileges for some log files
2. **SELinux/AppArmor:** Handle permission denied gracefully
3. **systemd journal:** Support `journalctl -u postgresql` as log source
4. **Multiple distributions:** Handle varied package manager conventions

## Dependencies

```go
require (
    github.com/c-bata/go-prompt v0.2.6
    github.com/fatih/color v1.16.0
    github.com/fsnotify/fsnotify v1.7.0  // File watching (Unix)
    github.com/shirou/gopsutil/v3 v3.24.1  // Cross-platform process info
)
```

### Dependency Rationale

- **go-prompt:** Feature-rich REPL with autocomplete, chosen per user preference
- **fatih/color:** Cross-platform terminal colors including Windows support
- **fsnotify:** File system notifications for efficient tailing (Unix)
- **gopsutil:** Cross-platform process and system information

## Error Handling

### Graceful Degradation

- If process detection fails, continue with path scanning
- If a log file is unreadable, report and skip (don't crash)
- If no instances found, provide helpful suggestions

### User-Friendly Messages

```
pgtail> tail 99
Error: No instance with index 99. Run 'list' to see available instances.

pgtail> tail /nonexistent
Error: No PostgreSQL instance found at '/nonexistent'
Did you mean: /opt/homebrew/var/postgresql@16 ?
```

## Future Considerations

These features are explicitly out of scope for v1 but may be considered later:

1. **Remote instances:** SSH tunneling to remote PostgreSQL servers
2. **Log search:** Grep-like searching within logs
3. **Bookmarks:** Save frequently-used instances
4. **Configuration file:** Persist settings across sessions
5. **JSON output:** Machine-readable output mode
6. **Multi-tail:** View multiple instance logs simultaneously (split view)
7. **Log rotation handling:** Seamlessly follow across log file rotations

## Success Metrics

The tool is successful if:

1. A developer can find and tail any PostgreSQL log in under 10 seconds
2. Zero configuration is required for pgrx development workflows
3. The tool works identically on macOS, Linux, and Windows
4. New users can be productive after reading `help` output alone
