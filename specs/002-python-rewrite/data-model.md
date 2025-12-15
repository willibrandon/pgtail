# Data Model: pgtail Python Rewrite

## Entities

### Instance

Represents a detected PostgreSQL installation.

```python
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from typing import Optional

class DetectionSource(Enum):
    PROCESS = "process"      # Running postgres process
    PGRX = "pgrx"            # ~/.pgrx/data-{version}
    PGDATA = "pgdata"        # PGDATA environment variable
    KNOWN_PATH = "known"     # Platform-specific default paths

@dataclass
class Instance:
    id: int                           # Sequential ID for user reference (1, 2, 3...)
    version: str                      # PostgreSQL version (e.g., "16.1")
    data_dir: Path                    # Path to data directory
    log_path: Optional[Path]          # Path to log file (None if logging disabled)
    source: DetectionSource           # How this instance was detected
    running: bool                     # Whether postgres process is currently running
    pid: Optional[int]                # Process ID if running, None otherwise
```

**Validation Rules**:
- `id` must be positive integer, unique within session
- `data_dir` must exist and be a directory
- `log_path` must exist if not None
- `version` extracted from `PG_VERSION` file or process

**State Transitions**:
- `running: True → False`: Process terminated (detected via psutil)
- `running: False → True`: Process started (detected on refresh)

### LogEntry

Represents a parsed log line.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LogEntry:
    timestamp: Optional[datetime]     # Parsed timestamp (None if unparseable)
    level: LogLevel                   # Severity level
    message: str                      # Log message content
    raw: str                          # Original line (for fallback display)
    pid: Optional[int]                # Process ID from log line
```

**Validation Rules**:
- `raw` is never empty (original line always preserved)
- `level` defaults to `LOG` if not parseable
- `timestamp` is None for malformed lines

### LogLevel

Enumeration of PostgreSQL log severity levels.

```python
from enum import IntEnum

class LogLevel(IntEnum):
    PANIC = 0      # System crash
    FATAL = 1      # Session abort
    ERROR = 2      # Command failure
    WARNING = 3    # Potential issues
    NOTICE = 4     # Informational
    LOG = 5        # Operational info
    INFO = 6       # User-requested info
    DEBUG1 = 7     # Debug levels
    DEBUG2 = 8
    DEBUG3 = 9
    DEBUG4 = 10
    DEBUG5 = 11
```

**Ordering**: Lower value = higher severity (for filtering comparison)

### AppState

Runtime state for the REPL session.

```python
from dataclasses import dataclass, field
from typing import Optional, Set
from pathlib import Path

@dataclass
class AppState:
    instances: list[Instance] = field(default_factory=list)
    current_instance: Optional[Instance] = None
    active_levels: Set[LogLevel] = field(default_factory=lambda: set(LogLevel))
    tailing: bool = False
    history_path: Path = field(default_factory=get_history_path)
```

**State Transitions**:
- `tailing: False → True`: User runs `tail` command
- `tailing: True → False`: User runs `stop` or Ctrl+C
- `active_levels` modified by `levels` command
- `instances` refreshed by `refresh` command

## Relationships

```
AppState 1──* Instance
    │
    └── current_instance ──> Instance (optional)

Instance ──> LogEntry (produced during tail)
    │
    └── log_path ──> file system

LogEntry ──> LogLevel
```

## Data Flow

1. **Startup**: Detector scans → populates `AppState.instances`
2. **List**: Render `AppState.instances` as formatted table
3. **Tail**:
   - Set `AppState.current_instance`
   - Set `AppState.tailing = True`
   - Tailer reads `current_instance.log_path`
   - Parser converts lines → `LogEntry`
   - Filter checks `entry.level in AppState.active_levels`
   - Colors renders filtered entries
4. **Stop**: Set `AppState.tailing = False`
5. **Refresh**: Re-run detector → update `AppState.instances`
