# Data Model: Export Logs and Pipe to External Commands

**Date**: 2025-12-15
**Feature**: 006-export-pipe

## Entities

### ExportFormat (Enum)

Enumeration of supported output formats for export and pipe commands.

```python
from enum import Enum

class ExportFormat(str, Enum):
    """Supported export output formats."""
    TEXT = "text"   # Raw log line (original format)
    JSON = "json"   # JSONL format (one JSON object per line)
    CSV = "csv"     # CSV with header row
```

**Validation Rules**:
- Default format is TEXT
- Format is case-insensitive when parsing from user input

### ExportOptions (Dataclass)

Configuration for an export operation.

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

@dataclass
class ExportOptions:
    """Configuration for an export operation."""
    path: Path                          # Target file path
    format: ExportFormat = ExportFormat.TEXT
    follow: bool = False                # Continuous export mode
    append: bool = False                # Append to existing file
    since: datetime | None = None       # Filter entries after this time

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if self.follow and self.append:
            errors.append("Cannot use --follow with --append")
        return errors
```

**Validation Rules**:
- `path` must be writable (checked at export time)
- `follow` and `append` are mutually exclusive
- `since` is optional; when set, filters entries with timestamp >= since

### PipeOptions (Dataclass)

Configuration for a pipe operation.

```python
@dataclass
class PipeOptions:
    """Configuration for a pipe operation."""
    command: str                        # Shell command to pipe to
    format: ExportFormat = ExportFormat.TEXT

    def validate(self) -> list[str]:
        """Return list of validation errors, empty if valid."""
        errors = []
        if not self.command.strip():
            errors.append("Command cannot be empty")
        return errors
```

**Validation Rules**:
- `command` must not be empty
- Command is executed via shell (allows pipes, redirects in command)

### Existing Entities (Reference)

These entities already exist and will be reused:

#### LogEntry (from parser.py)

```python
@dataclass
class LogEntry:
    """A parsed PostgreSQL log line."""
    timestamp: datetime | None  # Parsed timestamp
    level: LogLevel             # Log severity level
    message: str                # The log message content
    raw: str                    # Original line
    pid: int | None = None      # Process ID
```

#### FilterState (from regex_filter.py)

```python
@dataclass
class FilterState:
    """Current state of regex filters and highlights."""
    includes: list[RegexFilter]
    excludes: list[RegexFilter]
    ands: list[RegexFilter]
    highlights: list[Highlight]
```

#### LogLevel (from filter.py)

```python
class LogLevel(IntEnum):
    """PostgreSQL log severity levels."""
    PANIC = 0
    FATAL = 1
    ERROR = 2
    WARNING = 3
    NOTICE = 4
    LOG = 5
    INFO = 6
    DEBUG1 = 7
    # ... DEBUG2-DEBUG5
```

## Relationships

```
AppState (existing)
├── active_levels: set[LogLevel] | None  → Used to filter exported entries
├── regex_state: FilterState             → Used to filter exported entries
├── tailer: LogTailer | None             → Source of log entries for export
└── current_instance: Instance | None    → Provides context for errors

LogEntry (existing)
├── timestamp: datetime                  → Formatted to ISO 8601 in JSON/CSV
├── level: LogLevel                      → Converted to string name
├── pid: int                             → Included in JSON/CSV
└── message: str                         → Main content, escaped in JSON/CSV

ExportOptions (new)
├── path: Path                           → Target file
├── format: ExportFormat                 → Determines output formatting
├── follow: bool                         → Continuous vs one-shot mode
├── append: bool                         → Write mode (append vs overwrite)
└── since: datetime                      → Entry timestamp filter

PipeOptions (new)
├── command: str                         → Subprocess to spawn
└── format: ExportFormat                 → Determines stdin format
```

## State Transitions

### Export Command State

```
IDLE → EXPORTING → COMPLETED
  │         │
  │         └─────→ ERROR (permission denied, disk full)
  │
  └─→ FOLLOW_MODE ─→ STOPPED (Ctrl+C)
            │
            └─────→ ERROR
```

### Export Flow

1. **Parse Arguments**: Parse command line into ExportOptions
2. **Validate Options**: Check for conflicting options
3. **Check File Exists**: If exists and not append, prompt for overwrite
4. **Create Directories**: Ensure parent directories exist
5. **Open File**: Open for write/append
6. **Stream Entries**: Apply filters, format each entry, write to file
7. **Report Count**: Display number of entries exported
8. **Handle Errors**: Catch IOError, report entries written before failure

### Pipe Flow

1. **Parse Arguments**: Parse command line into PipeOptions
2. **Validate Command**: Check command is not empty
3. **Spawn Process**: Create subprocess with stdin pipe
4. **Stream Entries**: Apply filters, format each entry, write to stdin
5. **Capture Output**: Display stdout from subprocess
6. **Report Errors**: Display stderr if process fails

## Output Format Specifications

### TEXT Format

Raw log line as stored in `LogEntry.raw`:
```
2024-01-15 10:23:45.123 UTC [12345] ERROR: connection refused
```

### JSON Format (JSONL)

One JSON object per line with ISO 8601 timestamps:
```json
{"timestamp":"2024-01-15T10:23:45.123000","level":"ERROR","pid":12345,"message":"connection refused"}
```

Fields:
- `timestamp`: ISO 8601 string or `null` if unparseable
- `level`: String name of LogLevel enum
- `pid`: Integer or `null`
- `message`: String (escaped for JSON)

### CSV Format

CSV with header row:
```csv
timestamp,level,pid,message
2024-01-15T10:23:45.123000,ERROR,12345,connection refused
"2024-01-15T10:23:45.123000",ERROR,12345,"message with, comma"
```

Fields (same as JSON):
- Quoting: QUOTE_MINIMAL (only when necessary)
- Encoding: UTF-8
- Line endings: Platform default (via csv module)
