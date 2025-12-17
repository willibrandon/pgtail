# Research: Error Statistics Dashboard

**Feature**: 009-error-stats
**Date**: 2025-12-16

## R1: PostgreSQL SQLSTATE Codes

### Decision
Use a static dictionary of common PostgreSQL SQLSTATE codes with human-readable descriptions.

### Rationale
- PostgreSQL SQLSTATE codes follow the SQL standard and are stable
- Only ~200 commonly-seen codes; most errors fall into a few categories
- No runtime parsing or external files needed

### Research Findings

PostgreSQL organizes SQLSTATE codes by class (first two characters):

| Class | Category | Common Codes |
|-------|----------|--------------|
| 00 | Successful Completion | 00000 |
| 01 | Warning | 01000 |
| 02 | No Data | 02000 |
| 03 | SQL Statement Not Yet Complete | 03000 |
| 08 | Connection Exception | 08000, 08003, 08006 |
| 09 | Triggered Action Exception | 09000 |
| 0A | Feature Not Supported | 0A000 |
| 0B | Invalid Transaction Initiation | 0B000 |
| 0F | Locator Exception | 0F000 |
| 0L | Invalid Grantor | 0L000 |
| 0P | Invalid Role Specification | 0P000 |
| 0Z | Diagnostics Exception | 0Z000 |
| 20 | Case Not Found | 20000 |
| 21 | Cardinality Violation | 21000 |
| 22 | Data Exception | 22000, 22001, 22003, 22007, 22008, 22012, 22023 |
| 23 | Integrity Constraint Violation | 23000, 23502, 23503, 23505, 23514 |
| 24 | Invalid Cursor State | 24000 |
| 25 | Invalid Transaction State | 25000, 25001, 25002, 25P01, 25P02 |
| 26 | Invalid SQL Statement Name | 26000 |
| 27 | Triggered Data Change Violation | 27000 |
| 28 | Invalid Authorization | 28000, 28P01 |
| 2B | Dependent Privilege Descriptors | 2B000 |
| 2D | Invalid Transaction Termination | 2D000 |
| 2F | SQL Routine Exception | 2F000 |
| 34 | Invalid Cursor Name | 34000 |
| 38 | External Routine Exception | 38000 |
| 39 | External Routine Invocation Exception | 39000 |
| 3B | Savepoint Exception | 3B000 |
| 3D | Invalid Catalog Name | 3D000 |
| 3F | Invalid Schema Name | 3F000 |
| 40 | Transaction Rollback | 40000, 40001, 40002, 40003, 40P01 |
| 42 | Syntax Error or Access Rule Violation | 42000, 42501, 42601, 42703, 42P01, 42P02 |
| 44 | WITH CHECK OPTION Violation | 44000 |
| 53 | Insufficient Resources | 53000, 53100, 53200, 53300 |
| 54 | Program Limit Exceeded | 54000, 54001, 54011, 54023 |
| 55 | Object Not In Prerequisite State | 55000, 55006, 55P02, 55P03 |
| 57 | Operator Intervention | 57000, 57014, 57P01, 57P02, 57P03 |
| 58 | System Error | 58000, 58030, 58P01, 58P02 |
| 72 | Snapshot Failure | 72000 |
| F0 | Configuration File Error | F0000, F0001 |
| HV | Foreign Data Wrapper Error | HV000+ |
| P0 | PL/pgSQL Error | P0000, P0001, P0002 |
| XX | Internal Error | XX000, XX001, XX002 |

### Most Common Error Codes (for priority implementation)

```python
SQLSTATE_CODES = {
    # Class 23: Integrity Constraint Violation
    "23000": "integrity_constraint_violation",
    "23502": "not_null_violation",
    "23503": "foreign_key_violation",
    "23505": "unique_violation",
    "23514": "check_violation",

    # Class 42: Syntax Error or Access Rule Violation
    "42000": "syntax_error_or_access_rule_violation",
    "42501": "insufficient_privilege",
    "42601": "syntax_error",
    "42703": "undefined_column",
    "42P01": "undefined_table",
    "42P02": "undefined_parameter",

    # Class 53: Insufficient Resources
    "53000": "insufficient_resources",
    "53100": "disk_full",
    "53200": "out_of_memory",
    "53300": "too_many_connections",

    # Class 57: Operator Intervention
    "57000": "operator_intervention",
    "57014": "query_canceled",
    "57P01": "admin_shutdown",
    "57P02": "crash_shutdown",
    "57P03": "cannot_connect_now",

    # Class 58: System Error
    "58000": "system_error",
    "58030": "io_error",
    "58P01": "undefined_file",
    "58P02": "duplicate_file",
}
```

### Alternatives Considered
1. **Parse pg_errcodes.txt from PostgreSQL source**: Adds file I/O, version compatibility concerns
2. **External package (psycopg2.errorcodes)**: Adds dependency, only needed for display names
3. **No descriptions, raw codes only**: Less user-friendly

## R2: Terminal Sparkline Implementation

### Decision
Use Unicode block characters with 8 levels of granularity.

### Rationale
- Standard Unicode, works in all modern terminals
- Commonly used pattern (spark, termgraph, etc.)
- No external library needed

### Research Findings

Standard sparkline characters (U+2581 to U+2588):
```
▁ (U+2581) - LOWER ONE EIGHTH BLOCK
▂ (U+2582) - LOWER ONE QUARTER BLOCK
▃ (U+2583) - LOWER THREE EIGHTHS BLOCK
▄ (U+2584) - LOWER HALF BLOCK
▅ (U+2585) - LOWER FIVE EIGHTHS BLOCK
▆ (U+2586) - LOWER THREE QUARTERS BLOCK
▇ (U+2587) - LOWER SEVEN EIGHTHS BLOCK
█ (U+2588) - FULL BLOCK
```

### Implementation Pattern

```python
SPARK_CHARS = "▁▂▃▄▅▆▇█"

def sparkline(values: list[float]) -> str:
    """Generate a sparkline string from values."""
    if not values:
        return ""
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return SPARK_CHARS[3] * len(values)  # Middle height
    scale = (len(SPARK_CHARS) - 1) / (max_val - min_val)
    return "".join(
        SPARK_CHARS[int((v - min_val) * scale)]
        for v in values
    )
```

### Alternatives Considered
1. **ASCII only (|, #, -)**: Works everywhere but less readable
2. **Braille characters**: More resolution but less common font support
3. **External library (asciichartpy)**: Overkill for simple inline charts

## R3: In-Place Terminal Updates

### Decision
Use ANSI escape sequences with prompt_toolkit's `run_in_terminal` for live mode.

### Rationale
- prompt_toolkit handles terminal state management
- ANSI sequences work cross-platform (including Windows Terminal)
- Simple implementation without full-screen mode

### Research Findings

Key ANSI sequences:
- `\033[K` - Clear to end of line
- `\033[A` - Move cursor up
- `\r` - Return to start of line

prompt_toolkit pattern for in-place updates:
```python
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import HTML

def live_update():
    while running:
        print_formatted_text(
            HTML(f'\r<style fg="green">Errors: {count}</style>\033[K'),
            end=""
        )
        time.sleep(0.5)
```

### Alternatives Considered
1. **Full-screen prompt_toolkit Application**: Complex, overkill for counter
2. **curses/blessed**: Platform-specific complexity
3. **No live mode, poll-and-print**: Creates scrolling output

## R4: Thread-Safe Statistics Collection

### Decision
Use `collections.deque` with maxlen for the sliding window, rely on GIL for atomic operations.

### Rationale
- deque append is atomic under GIL
- No explicit locking needed for producer-consumer pattern
- Simple, stdlib solution

### Research Findings

Python's GIL makes single operations atomic:
- `deque.append()` - atomic
- `deque.popleft()` - atomic
- `len(deque)` - atomic

For the error stats pattern:
- Tailer thread appends errors
- Main thread reads for display
- No explicit lock needed for this use case

```python
from collections import deque

class ErrorStats:
    def __init__(self, max_entries: int = 10000):
        self._events: deque[ErrorEvent] = deque(maxlen=max_entries)

    def add(self, entry: LogEntry) -> None:
        """Called from tailer thread."""
        if entry.level in ERROR_LEVELS:
            self._events.append(ErrorEvent.from_entry(entry))

    def get_summary(self) -> dict:
        """Called from main thread."""
        # Snapshot the deque (thread-safe iteration)
        events = list(self._events)
        return self._compute_summary(events)
```

### Alternatives Considered
1. **threading.Lock**: Unnecessary overhead given GIL
2. **queue.Queue**: Better for producer-consumer, but we need random access for stats
3. **multiprocessing.Manager**: Overkill, single-process tool

## R5: Error Level Filtering

### Decision
Track ERROR, FATAL, PANIC as "errors" and WARNING separately.

### Rationale
- Matches PostgreSQL severity semantics
- Users typically want errors vs warnings distinction
- Aligns with spec requirements

### Research Findings

PostgreSQL log levels (from filter.py):
```python
class LogLevel(IntEnum):
    PANIC = 0   # Track as error
    FATAL = 1   # Track as error
    ERROR = 2   # Track as error
    WARNING = 3 # Track as warning
    NOTICE = 4  # Not tracked
    LOG = 5     # Not tracked
    INFO = 6    # Not tracked
    DEBUG1-5    # Not tracked
```

### Implementation
```python
ERROR_LEVELS = {LogLevel.PANIC, LogLevel.FATAL, LogLevel.ERROR}
WARNING_LEVELS = {LogLevel.WARNING}
TRACKED_LEVELS = ERROR_LEVELS | WARNING_LEVELS
```

## Summary

All research items resolved. No external dependencies required. Implementation can proceed with:

1. Static SQLSTATE lookup dict (~100 common codes)
2. Unicode sparkline characters for trends
3. ANSI escape sequences for live mode
4. collections.deque for thread-safe sliding window
5. LogLevel enum for error classification
