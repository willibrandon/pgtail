# Research: pgtail CLI Tool

**Date**: 2025-12-14
**Branch**: `001-pgtail-cli`

## Overview

Research findings for implementing the pgtail CLI tool. All technology choices were pre-determined by the project constitution; this document captures best practices and implementation patterns.

## 1. go-prompt REPL Implementation

**Decision**: Use `github.com/c-bata/go-prompt` v0.2.6 for interactive REPL

**Rationale**: Constitution-approved dependency providing autocomplete, history, and cross-platform terminal handling out of the box.

**Best Practices**:
- Use `prompt.New()` with custom `Executor` and `Completer` functions
- Implement `LivePrefixChangedCallback` for dynamic prompt showing state
- Handle Ctrl+C gracefully by returning empty string from executor (not os.Exit)
- Set `prompt.OptionPrefixTextColor` for visual consistency
- Use `prompt.OptionAddKeyBind` for custom key bindings (Ctrl+L for clear)

**Implementation Pattern**:
```go
p := prompt.New(
    executor,
    completer,
    prompt.OptionPrefix("pgtail> "),
    prompt.OptionLivePrefix(livePrefix),
    prompt.OptionTitle("pgtail"),
)
p.Run()
```

**Alternatives Considered**:
- `liner`: Simpler but lacks built-in autocomplete suggestions display
- `readline`: More complex, manual autocomplete implementation required
- Custom implementation: Violates Minimal Dependencies principle

## 2. Cross-Platform Process Detection

**Decision**: Use `github.com/shirou/gopsutil/v3` for process enumeration

**Rationale**: Constitution-approved; provides unified API across macOS, Linux, Windows without platform-specific syscalls in our code.

**Best Practices**:
- Use `process.Processes()` to get all running processes
- Filter by name containing "postgres" (case-insensitive)
- Extract `-D` argument from `Cmdline()` to find data directory
- Handle permission errors gracefully (some processes unreadable)
- Cache results briefly to avoid repeated system calls

**Implementation Pattern**:
```go
procs, _ := process.Processes()
for _, p := range procs {
    name, _ := p.Name()
    if strings.Contains(strings.ToLower(name), "postgres") {
        cmdline, _ := p.Cmdline()
        dataDir := extractDataDir(cmdline) // parse -D flag
    }
}
```

**Platform Notes**:
- macOS: Works with SIP restrictions (processes visible)
- Linux: May need elevated privileges for some process info
- Windows: Use `Name()` checking for "postgres.exe"

**Alternatives Considered**:
- Direct syscalls: Platform-specific code; violates Cross-Platform Parity
- `os/exec` with `ps`/`wmic`: Parsing output fragile; Windows different

## 3. File Tailing Strategy

**Decision**: Use `github.com/fsnotify/fsnotify` for Unix, polling fallback for Windows

**Rationale**: Constitution-approved; fsnotify efficient on Unix but has Windows limitations.

**Best Practices**:
- Open file, seek to end, read new content on events
- Use `fsnotify.Write` events to trigger reads
- Implement polling fallback (100ms interval) for Windows
- Handle file rotation: detect truncation, reopen file
- Buffer reads to avoid partial line output

**Implementation Pattern**:
```go
// Unix: fsnotify
watcher, _ := fsnotify.NewWatcher()
watcher.Add(logFile)
for event := range watcher.Events {
    if event.Op&fsnotify.Write != 0 {
        readNewContent()
    }
}

// Windows: polling
ticker := time.NewTicker(100 * time.Millisecond)
for range ticker.C {
    checkAndReadNewContent()
}
```

**Edge Cases**:
- Log rotation: Check file size decreased → reopen and read from start
- File deleted: Report error, stop tailing, return to prompt
- Permissions change: Report and suggest remediation

**Alternatives Considered**:
- Pure polling everywhere: Works but less efficient on Unix
- tail -f subprocess: Not cross-platform; external dependency

## 4. PostgreSQL Log Format Parsing

**Decision**: Parse standard PostgreSQL log_line_prefix patterns

**Rationale**: PostgreSQL has well-documented log formats; parsing enables level filtering and coloring.

**Best Practices**:
- Default format: `%t [%p] %l %q%e: ` (timestamp, PID, line, level)
- Common levels: DEBUG5-DEBUG1, INFO, NOTICE, WARNING, ERROR, LOG, FATAL, PANIC
- Use regex with named groups for flexibility
- Handle multi-line log entries (continuation lines lack prefix)
- Gracefully handle unparseable lines (show as-is)

**Implementation Pattern**:
```go
// Common PostgreSQL log pattern
var logPattern = regexp.MustCompile(
    `^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ \w+)\s+` + // timestamp
    `\[(\d+)\]\s+` +                                        // PID
    `(\w+):\s*` +                                           // level
    `(.*)$`,                                                // message
)

func parseLogLine(line string) (level, message string) {
    matches := logPattern.FindStringSubmatch(line)
    if matches == nil {
        return "", line // unparseable, return as-is
    }
    return matches[3], matches[4]
}
```

**Log Level Mapping**:
| PostgreSQL Level | Color |
|------------------|-------|
| PANIC, FATAL | Bold Red |
| ERROR | Red |
| WARNING | Yellow |
| NOTICE | Cyan |
| LOG | Default |
| INFO | Green |
| DEBUG1-5 | Dark Gray |

**Alternatives Considered**:
- CSV log parsing: More structured but requires csvlog destination
- No parsing: Cannot filter or color by level

## 5. postgresql.conf Parsing

**Decision**: Simple key-value parsing for required settings

**Rationale**: Only need `log_directory`, `log_filename`, `port`, `log_destination`; full parser overkill.

**Best Practices**:
- Read file line by line
- Skip comments (lines starting with #)
- Parse `key = value` or `key=value` format
- Handle quoted string values
- Resolve relative `log_directory` paths against data directory

**Implementation Pattern**:
```go
func parseConfig(dataDir string) map[string]string {
    config := make(map[string]string)
    file, _ := os.Open(filepath.Join(dataDir, "postgresql.conf"))
    scanner := bufio.NewScanner(file)
    for scanner.Scan() {
        line := strings.TrimSpace(scanner.Text())
        if strings.HasPrefix(line, "#") || line == "" {
            continue
        }
        if idx := strings.Index(line, "="); idx > 0 {
            key := strings.TrimSpace(line[:idx])
            value := strings.Trim(strings.TrimSpace(line[idx+1:]), "'\"")
            config[key] = value
        }
    }
    return config
}
```

**Required Settings**:
- `log_directory`: Where logs are stored (default: `log` or `pg_log`)
- `log_filename`: Log file pattern (default: `postgresql-%Y-%m-%d_%H%M%S.log`)
- `port`: Listening port for display (default: 5432)
- `log_destination`: stderr, csvlog, syslog, eventlog

**Alternatives Considered**:
- Full postgresql.conf parser library: Overkill for 4 settings
- Exec `pg_config`: Not available if PostgreSQL not in PATH

## 6. Path Detection Strategy

**Decision**: Prioritized scan of known paths by platform

**Rationale**: Constitution requires pgrx-first detection; known paths cover 95% of installations.

**Detection Priority Order**:
1. Running processes (highest confidence)
2. pgrx directories (`~/.pgrx/data-*`)
3. PGDATA environment variable
4. Platform-specific known paths
5. Service registration (lowest priority)

**Platform Paths**:

**macOS**:
```
~/.pgrx/data-*/
/opt/homebrew/var/postgresql@*/
/opt/homebrew/var/postgres/
/usr/local/var/postgresql@*/
/usr/local/var/postgres/
~/Library/Application Support/Postgres/var-*/
```

**Linux (Debian/Ubuntu)**:
```
~/.pgrx/data-*/
/var/lib/postgresql/*/main/
/etc/postgresql/*/main/
```

**Linux (RHEL/CentOS)**:
```
~/.pgrx/data-*/
/var/lib/pgsql/*/data/
/var/lib/pgsql/data/
```

**Windows**:
```
%USERPROFILE%\.pgrx\data-*\
C:\Program Files\PostgreSQL\*\data\
C:\Program Files (x86)\PostgreSQL\*\data\
%PROGRAMDATA%\PostgreSQL\*\data\
```

**Validation**: Directory is valid PostgreSQL data dir if contains:
- `PG_VERSION` file (read for version)
- `postgresql.conf` file

**Alternatives Considered**:
- Only process detection: Misses stopped instances
- Only path scanning: Misses non-standard locations

## 7. Color Output Strategy

**Decision**: Use `github.com/charmbracelet/lipgloss` for terminal styling

**Rationale**: Modern terminal styling library with flexible theming, cross-platform support, and foundation for future bubbletea TUI enhancements.

**Best Practices**:
- Define styles as package-level variables for reuse
- Use `lipgloss.NewStyle()` to create base styles
- Chain style methods: `.Foreground()`, `.Bold()`, `.Padding()`
- Check `lipgloss.HasDarkBackground()` for adaptive theming
- Use `NO_COLOR` env var detection via lipgloss

**Implementation Pattern**:
```go
var (
    errorStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("9"))  // red
    fatalStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("9")).Bold(true)
    warnStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("11")) // yellow
    noticeStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("14")) // cyan
    infoStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("10")) // green
    debugStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("8"))  // gray

    // UI elements
    headerStyle = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("12"))
    mutedStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("8"))
)

func colorize(level, line string) string {
    switch level {
    case "FATAL", "PANIC":
        return fatalStyle.Render(line)
    case "ERROR":
        return errorStyle.Render(line)
    // ...
    }
}
```

**Alternatives Considered**:
- fatih/color: Simpler but less flexible styling options
- ANSI codes directly: Windows compatibility issues
- No color: Reduces usability for quick scanning

## Summary

All technology decisions align with the project constitution. Key implementation patterns:

1. **REPL**: go-prompt with live prefix for state display
2. **Process Detection**: gopsutil for cross-platform process enumeration
3. **File Tailing**: fsnotify on Unix, polling on Windows
4. **Log Parsing**: Regex for standard PostgreSQL format
5. **Config Parsing**: Simple key-value extraction
6. **Path Detection**: Prioritized platform-specific paths with pgrx first
7. **Colors**: lipgloss for cross-platform terminal styling

No unresolved clarifications remain. Ready for Phase 1 design.
