# Data Model: Tail Arbitrary Log Files

**Feature Branch**: `021-tail-file-option`
**Created**: 2026-01-05

## Overview

This feature adds minimal data model changes. The primary additions are:
1. A new `file_path` tracking field in `TailStatus`
2. Optional instance info detection from log content

No database or persistent storage changes required.

## Entity Changes

### TailStatus (Modified)

**File**: `pgtail_py/tail_status.py`

```python
@dataclass
class TailStatus:
    """State container for status bar display."""

    # Existing fields...
    error_count: int = 0
    warning_count: int = 0
    total_lines: int = 0
    follow_mode: bool = True
    new_since_pause: int = 0
    active_levels: set[LogLevel] = field(default_factory=LogLevel.all_levels)
    regex_pattern: str | None = None
    time_filter_display: str | None = None
    slow_threshold: int | None = None
    pg_version: str = ""
    pg_port: int = 5432

    # NEW FIELDS for file-based tailing
    filename: str | None = None              # Filename when tailing arbitrary file
    file_unavailable: bool = False           # True when file is deleted/inaccessible
    detected_from_content: bool = False      # True if pg_version/pg_port detected from log content
```

**New Methods**:

```python
def set_file_source(self, filename: str) -> None:
    """Set the filename for file-based tailing.

    Args:
        filename: The log filename (e.g., 'postmaster.log')
    """
    self.filename = filename

def set_file_unavailable(self, unavailable: bool) -> None:
    """Set file unavailability status.

    Args:
        unavailable: True if file is currently inaccessible
    """
    self.file_unavailable = unavailable
```

**Display Logic**:

The `format_rich()` method priority:
1. If `pg_version` is set → show `PG{version}:{port}` (detected from log content)
2. Else if `filename` is set → show `{filename}` (file-only mode)
3. Else → show `:{port}` (fallback)

### AppState (Modified)

**File**: `pgtail_py/cli.py`

```python
@dataclass
class AppState:
    """Runtime state for the REPL session."""

    # Existing fields...
    instances: list[Instance] = field(default_factory=list)
    current_instance: Instance | None = None
    # ... other fields ...

    # NEW FIELD for file-based tailing
    current_file_path: Path | None = None    # When tailing arbitrary file (no instance)
```

### TailApp (Modified)

**File**: `pgtail_py/tail_textual.py`

```python
class TailApp(App[None]):
    def __init__(
        self,
        state: AppState,
        instance: Instance | None,           # CHANGED: Now optional
        log_path: Path,
        max_lines: int = 10000,
    ) -> None:
        ...
        self._instance: Instance | None = instance  # Can be None for file-only mode
        self._log_path: Path = log_path
        self._instance_detected: bool = False       # NEW: True when detected from content
```

## Instance Info Detection

### DetectedInstanceInfo (New)

**File**: `pgtail_py/tail_textual.py` (internal class)

```python
@dataclass
class DetectedInstanceInfo:
    """PostgreSQL instance info detected from log content.

    Used when tailing arbitrary files to extract version/port
    from PostgreSQL startup messages.
    """
    version: str | None = None    # e.g., "17" or "17.0"
    port: int | None = None       # e.g., 5432
```

**Detection Patterns**:

```python
# Version detection
# Matches: "starting PostgreSQL 17.0 on x86_64..."
VERSION_PATTERN = re.compile(r'starting PostgreSQL (\d+)(?:\.(\d+))?')

# Port detection
# Matches: "listening on IPv4 address "0.0.0.0", port 5432"
# Matches: "listening on Unix socket "/tmp/.s.PGSQL.5432""
PORT_PATTERN = re.compile(r'listening on .*port (\d+)')
PORT_SOCKET_PATTERN = re.compile(r'\.s\.PGSQL\.(\d+)')
```

## State Transitions

### File Tailing States

```
                    ┌──────────────┐
                    │   INITIAL    │
                    │  (no tail)   │
                    └──────┬───────┘
                           │ tail --file <path>
                           ▼
                    ┌──────────────┐
                    │   TAILING    │◄──────────────┐
                    │    FILE      │               │
                    └──────┬───────┘               │
                           │                       │
              ┌────────────┼────────────┐          │
              │            │            │          │
              ▼            ▼            ▼          │
      ┌───────────┐ ┌───────────┐ ┌───────────┐   │
      │  DETECT   │ │   FILE    │ │    USER   │   │
      │ INSTANCE  │ │  DELETED  │ │   STOPS   │   │
      │   INFO    │ │           │ │           │   │
      └─────┬─────┘ └─────┬─────┘ └─────┬─────┘   │
            │             │             │          │
            │             │ recreated   │          │
            └─────────────┼─────────────┘          │
                          │                        │
                          └────────────────────────┘
```

### Status Bar Display States

| State | pg_version | filename | Display |
|-------|------------|----------|---------|
| Instance tailing | Set | None | `PG17:5432` |
| File tailing (detected) | Set | Set | `PG17:5432` |
| File tailing (not detected) | None | Set | `postmaster.log` |
| File tailing (unavailable) | None | Set | `postmaster.log (unavailable)` |

## Validation Rules

### Path Validation

```python
def validate_file_path(path_str: str) -> tuple[Path, str | None]:
    """Validate a file path for tailing.

    Args:
        path_str: User-provided path string

    Returns:
        Tuple of (resolved_path, error_message).
        If error_message is None, path is valid.
    """
    path = Path(path_str).resolve()

    if not path.exists():
        return path, f"File not found: {path}"

    if path.is_dir():
        return path, f"Not a file: {path} (is a directory)"

    try:
        # Check read permission
        with open(path, 'rb') as f:
            pass
    except PermissionError:
        return path, f"Permission denied: {path}"
    except OSError as e:
        return path, f"Cannot access file: {path} ({e})"

    return path, None  # Valid
```

### Mutual Exclusivity

```python
def validate_tail_args(
    file_path: str | None,
    instance_id: int | None
) -> str | None:
    """Validate tail command arguments.

    Returns error message if invalid, None if valid.
    """
    if file_path is not None and instance_id is not None:
        return "Cannot specify both --file and instance ID"
    return None
```

## Relationships

```
AppState
├── current_instance: Instance | None
├── current_file_path: Path | None      # NEW
└── tailer: LogTailer | None

TailApp
├── _state: AppState
├── _instance: Instance | None          # MODIFIED: Now optional
├── _log_path: Path
├── _status: TailStatus
└── _tailer: LogTailer

TailStatus
├── pg_version: str
├── pg_port: int
├── filename: str | None                # NEW
├── file_unavailable: bool              # NEW
└── detected_from_content: bool         # NEW

LogTailer (unchanged)
├── _log_path: Path
├── _data_dir: Path | None
└── _log_directory: Path | None
```

## Migration Notes

No data migration required. All changes are:
- New optional fields with defaults
- Modified constructor signatures with backward-compatible defaults
- New display logic that falls back gracefully
