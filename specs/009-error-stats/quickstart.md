# Quickstart: Error Statistics Dashboard

**Feature**: 009-error-stats
**Date**: 2025-12-16

## Overview

This guide covers implementing the error statistics feature for pgtail. The feature adds an `errors` command that tracks ERROR, FATAL, PANIC, and WARNING log entries and provides statistics, trends, and breakdowns.

## Prerequisites

- Familiarity with pgtail codebase structure
- Understanding of LogEntry dataclass and parsing
- Knowledge of prompt_toolkit basics

## Implementation Steps

### Step 1: Create error_stats.py

Create the core error tracking module:

```python
# pgtail_py/error_stats.py
"""Error statistics tracking for PostgreSQL logs."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry

# Levels to track
ERROR_LEVELS = {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR}
WARNING_LEVELS = {LogLevel.WARNING}
TRACKED_LEVELS = ERROR_LEVELS | WARNING_LEVELS


@dataclass(frozen=True)
class ErrorEvent:
    """A tracked error or warning event."""
    timestamp: datetime
    level: LogLevel
    sql_state: str | None
    message: str
    pid: int | None
    database: str | None
    user: str | None

    @classmethod
    def from_entry(cls, entry: "LogEntry") -> "ErrorEvent":
        """Create ErrorEvent from a LogEntry."""
        return cls(
            timestamp=entry.timestamp or datetime.now(),
            level=entry.level,
            sql_state=entry.sql_state,
            message=(entry.message or "")[:200],
            pid=entry.pid,
            database=entry.database_name,
            user=entry.user_name,
        )


@dataclass
class ErrorStats:
    """Session-scoped error statistics."""
    _events: deque[ErrorEvent] = field(default_factory=lambda: deque(maxlen=10000))
    session_start: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    warning_count: int = 0
    last_error_time: datetime | None = None

    def add(self, entry: "LogEntry") -> None:
        """Add a log entry if it's an error/warning."""
        if entry.level not in TRACKED_LEVELS:
            return

        event = ErrorEvent.from_entry(entry)
        self._events.append(event)

        if entry.level in ERROR_LEVELS:
            self.error_count += 1
            self.last_error_time = event.timestamp
        else:
            self.warning_count += 1

    def clear(self) -> None:
        """Reset all statistics."""
        self._events.clear()
        self.error_count = 0
        self.warning_count = 0
        self.last_error_time = None
        self.session_start = datetime.now()

    def is_empty(self) -> bool:
        """Check if any events tracked."""
        return len(self._events) == 0
```

### Step 2: Add SQLSTATE Lookup

Add to error_stats.py:

```python
# SQLSTATE code categories
SQLSTATE_CATEGORIES: dict[str, str] = {
    "23": "Integrity Constraint Violation",
    "42": "Syntax Error or Access Rule Violation",
    "53": "Insufficient Resources",
    "57": "Operator Intervention",
    "58": "System Error",
}

# Common SQLSTATE codes
SQLSTATE_NAMES: dict[str, str] = {
    "23502": "not_null_violation",
    "23503": "foreign_key_violation",
    "23505": "unique_violation",
    "23514": "check_violation",
    "42501": "insufficient_privilege",
    "42601": "syntax_error",
    "42703": "undefined_column",
    "42P01": "undefined_table",
    "53100": "disk_full",
    "53200": "out_of_memory",
    "53300": "too_many_connections",
    "57014": "query_canceled",
    "57P01": "admin_shutdown",
    "58030": "io_error",
}

def get_sqlstate_name(code: str) -> str:
    """Get human-readable name for SQLSTATE code."""
    return SQLSTATE_NAMES.get(code, code)

def get_sqlstate_category(code: str) -> str:
    """Get category for SQLSTATE code class."""
    return SQLSTATE_CATEGORIES.get(code[:2], "Unknown")
```

### Step 3: Create error_trend.py

Create the trend visualization module:

```python
# pgtail_py/error_trend.py
"""Error trend visualization."""

from datetime import datetime, timedelta

SPARK_CHARS = "▁▂▃▄▅▆▇█"

def sparkline(values: list[int]) -> str:
    """Generate sparkline from values."""
    if not values:
        return ""
    max_val = max(values) or 1
    return "".join(
        SPARK_CHARS[min(int(v / max_val * 7), 7)]
        for v in values
    )

def bucket_events(events: list, minutes: int = 60) -> list[int]:
    """Bucket events into per-minute counts."""
    now = datetime.now()
    buckets = [0] * minutes
    cutoff = now - timedelta(minutes=minutes)

    for event in events:
        if event.timestamp < cutoff:
            continue
        age_minutes = int((now - event.timestamp).total_seconds() / 60)
        if 0 <= age_minutes < minutes:
            buckets[minutes - 1 - age_minutes] += 1

    return buckets
```

### Step 4: Create cli_errors.py

Create the command handler:

```python
# pgtail_py/cli_errors.py
"""Error statistics command handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

from pgtail_py.error_stats import get_sqlstate_name
from pgtail_py.error_trend import bucket_events, sparkline

if TYPE_CHECKING:
    from pgtail_py.cli import AppState

def errors_command(state: "AppState", args: list[str]) -> None:
    """Handle the errors command."""
    if not args:
        _show_summary(state)
    elif args[0] == "clear":
        _clear_stats(state)
    elif args[0] == "--trend":
        _show_trend(state)
    elif args[0] == "--live":
        _show_live(state)
    elif args[0] == "--code" and len(args) > 1:
        _show_by_code(state, args[1])
    else:
        print_formatted_text(HTML("<ansiyellow>Usage: errors [--trend|--live|--code CODE|clear]</ansiyellow>"))

def _show_summary(state: "AppState") -> None:
    """Display error summary."""
    stats = state.error_stats
    if stats.is_empty():
        print_formatted_text("No errors recorded in this session.")
        return

    print_formatted_text(HTML(
        f"<b>Error Statistics</b>\n"
        f"─────────────────────────────\n"
        f"Errors: <ansired>{stats.error_count}</ansired>  "
        f"Warnings: <ansiyellow>{stats.warning_count}</ansiyellow>"
    ))
    # ... add by_type and by_level breakdowns
```

### Step 5: Integrate with AppState

Modify cli.py:

```python
from pgtail_py.error_stats import ErrorStats

@dataclass
class AppState:
    # ... existing fields ...
    error_stats: ErrorStats = field(default_factory=ErrorStats)
```

### Step 6: Add Entry Callback to LogTailer

Modify tailer.py:

```python
def __init__(
    self,
    # ... existing params ...
    on_entry: Callable[[LogEntry], None] | None = None,
) -> None:
    # ... existing init ...
    self._on_entry = on_entry

def _read_new_lines(self) -> None:
    # ... existing code ...
    if self._should_show(entry):
        self._queue.put(entry)
        self._buffer.append(entry)
    # Always call entry callback (before filtering)
    if self._on_entry:
        self._on_entry(entry)
```

### Step 7: Register Command

Add to commands.py:

```python
COMMANDS: dict[str, str] = {
    # ... existing commands ...
    "errors": "Show error statistics (--trend, --live, --code, clear)",
}
```

### Step 8: Add Tests

Create tests/test_error_stats.py:

```python
import pytest
from datetime import datetime
from pgtail_py.error_stats import ErrorStats, ErrorEvent, TRACKED_LEVELS
from pgtail_py.filter import LogLevel

def test_add_error():
    stats = ErrorStats()
    # Create mock LogEntry and test add()
    ...

def test_clear():
    stats = ErrorStats()
    stats.add(...)
    assert not stats.is_empty()
    stats.clear()
    assert stats.is_empty()

def test_sliding_window():
    stats = ErrorStats()
    stats._events = deque(maxlen=10)
    for i in range(15):
        stats.add(...)
    assert len(stats._events) == 10
```

## Testing

Run the test suite:

```bash
make test
```

Manual testing:

```bash
# Start pgtail and tail an instance with errors
pgtail
> tail 1
> errors          # Should show summary
> errors --trend  # Should show sparkline
> errors clear    # Should reset
```

## Key Files Modified

| File | Changes |
|------|---------|
| pgtail_py/error_stats.py | NEW: ErrorEvent, ErrorStats, SQLSTATE lookup |
| pgtail_py/error_trend.py | NEW: Sparkline and bucketing |
| pgtail_py/cli_errors.py | NEW: Command handler |
| pgtail_py/cli.py | Add error_stats to AppState |
| pgtail_py/tailer.py | Add on_entry callback |
| pgtail_py/commands.py | Register errors command |
| tests/test_error_stats.py | NEW: Unit tests |

## Common Issues

1. **Events not being tracked**: Ensure the on_entry callback is passed to LogTailer
2. **Memory growing**: Verify deque maxlen is set
3. **Sparkline not displaying**: Check terminal Unicode support
4. **Live mode not updating**: Ensure proper ANSI sequence handling
