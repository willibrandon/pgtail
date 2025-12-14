# Data Model: pgtail CLI Tool

**Date**: 2025-12-14
**Branch**: `001-pgtail-cli`

## Overview

pgtail is a stateless CLI tool with no persistence. This document defines the in-memory data structures used during runtime.

## Core Entities

### Instance

Represents a detected PostgreSQL installation.

```go
type Instance struct {
    DataDir    string          // Absolute path to data directory
    Version    string          // PostgreSQL version (e.g., "16.1")
    Port       int             // Listening port (0 if unknown)
    Running    bool            // Whether postmaster is currently running
    LogDir     string          // Resolved log directory path
    LogPattern string          // Log filename pattern (e.g., "postgresql-%Y-%m-%d_%H%M%S.log")
    Source     DetectionSource // How this instance was detected
}
```

**Field Details**:

| Field | Type | Required | Default | Validation |
|-------|------|----------|---------|------------|
| DataDir | string | Yes | - | Must be absolute path; must exist; must contain PG_VERSION |
| Version | string | Yes | - | Read from PG_VERSION file; format "X.Y" or "X" |
| Port | int | No | 0 | Range 1-65535 if set; 0 means unknown |
| Running | bool | Yes | false | True if postmaster process found with matching data dir |
| LogDir | string | No | "" | Resolved from log_directory config or default paths |
| LogPattern | string | No | "" | From log_filename config; empty if not configured |
| Source | DetectionSource | Yes | - | One of the defined detection sources |

**Identity**: Instances are uniquely identified by `DataDir` (absolute path, normalized).

**Lifecycle**: Created during detection, immutable during session, refreshed on `refresh` command.

### DetectionSource

Enumeration of how an instance was discovered.

```go
type DetectionSource int

const (
    SourceProcess   DetectionSource = iota // Found via running postgres process
    SourcePgrx                             // Found in ~/.pgrx/data-*/
    SourceKnownPath                        // Found in platform-specific known paths
    SourceEnvVar                           // Found via PGDATA environment variable
    SourceService                          // Found via system service registration
)
```

**Display Mapping**:

| Value | Display String | Priority |
|-------|---------------|----------|
| SourceProcess | "process" | 1 (highest) |
| SourcePgrx | "pgrx" | 2 |
| SourceEnvVar | "env" | 3 |
| SourceKnownPath | varies by path | 4 |
| SourceService | "service" | 5 (lowest) |

**KnownPath Display Values**:
- Homebrew: "brew"
- Postgres.app: "app"
- System package: "pkg"
- Windows installer: "installer"

### LogLevel

PostgreSQL log severity levels.

```go
type LogLevel int

const (
    LevelDebug5 LogLevel = iota
    LevelDebug4
    LevelDebug3
    LevelDebug2
    LevelDebug1
    LevelInfo
    LevelNotice
    LevelWarning
    LevelError
    LevelLog
    LevelFatal
    LevelPanic
)
```

**String Mapping**:

| Level | String | Severity | Color |
|-------|--------|----------|-------|
| LevelPanic | "PANIC" | Critical | Bold Red |
| LevelFatal | "FATAL" | Critical | Bold Red |
| LevelError | "ERROR" | High | Red |
| LevelWarning | "WARNING" | Medium | Yellow |
| LevelNotice | "NOTICE" | Low | Cyan |
| LevelLog | "LOG" | Info | Default |
| LevelInfo | "INFO" | Info | Green |
| LevelDebug1-5 | "DEBUG1"-"DEBUG5" | Verbose | Dark Gray |

### Filter

User-configured set of log levels to display.

```go
type Filter struct {
    Levels map[LogLevel]bool // True for levels to show
}
```

**Behavior**:
- Empty filter (nil or all false): Show all levels
- Non-empty filter: Show only levels with `true` value
- Filter persists across tail sessions until cleared

**Methods**:
- `Allow(level LogLevel) bool`: Check if level should be displayed
- `Set(levels ...LogLevel)`: Set specific levels to show
- `Clear()`: Remove all filtering (show all)
- `String() string`: Format for prompt display (e.g., "ERR,WARN")

### LogEntry

Parsed log line for display.

```go
type LogEntry struct {
    Timestamp string   // Original timestamp string
    PID       int      // PostgreSQL backend PID
    Level     LogLevel // Parsed log level
    Message   string   // Log message content
    Raw       string   // Original unparsed line
}
```

**Parsing Rules**:
- If line matches log pattern: populate all fields
- If line is continuation (no timestamp): Level = previous entry's level, only Raw populated
- If line unparseable: Level = LevelLog (default), only Raw populated

### AppState

Runtime state for the REPL session.

```go
type AppState struct {
    Instances      []*Instance // Detected instances (indexed 0-N)
    CurrentIndex   int         // Selected instance index (-1 if none)
    Filter         *Filter     // Active log level filter
    Tailing        bool        // Whether actively tailing logs
    TailCancel     context.CancelFunc // Function to stop tailing
}
```

**State Transitions**:

```
Initial State:
  Instances: []
  CurrentIndex: -1
  Filter: nil
  Tailing: false

After 'list' or startup:
  Instances: [detected...]
  CurrentIndex: -1 (unchanged)

After 'tail N':
  CurrentIndex: N
  Tailing: true
  TailCancel: set

After Ctrl+C during tail:
  Tailing: false
  TailCancel: nil
  CurrentIndex: unchanged (persists)

After 'levels ERROR WARNING':
  Filter: {ERROR: true, WARNING: true}

After 'levels' (no args):
  Filter: nil

After 'refresh':
  Instances: [re-detected...]
  CurrentIndex: -1 (reset)
  Filter: unchanged
```

## Relationships

```
AppState
    ├── has many → Instance
    │                 └── has one → DetectionSource
    ├── has one  → Filter
    │                 └── contains many → LogLevel
    └── tailing  → produces many → LogEntry
                                      └── has one → LogLevel
```

## Validation Rules

### Instance Validation

1. `DataDir` MUST be an absolute path
2. `DataDir` MUST exist and be a directory
3. `DataDir` MUST contain a `PG_VERSION` file
4. `Version` MUST be parseable from `PG_VERSION` content
5. `Port` if non-zero MUST be in range 1-65535
6. `LogDir` if non-empty MUST be an absolute path

### Deduplication

Instances are deduplicated by normalized `DataDir`:
1. Convert to absolute path
2. Clean path (remove `.`, `..`, trailing slashes)
3. On case-insensitive filesystems (Windows, macOS default): lowercase
4. First detection source wins (by priority order)

### Log Entry Parsing

1. Attempt to match standard PostgreSQL log format
2. If no match, treat entire line as message with default level
3. Multi-line entries: detect by leading whitespace or continuation
4. Maximum line length: 64KB (PostgreSQL default max)

## No Persistence

pgtail maintains no persistent state between sessions:
- No configuration files
- No history file (go-prompt handles session history only)
- No cache of detected instances
- No saved filters

This aligns with the constitution's Simplicity First principle.
