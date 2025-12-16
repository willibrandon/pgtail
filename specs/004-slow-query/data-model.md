# Data Model: Slow Query Detection and Highlighting

**Feature**: 004-slow-query
**Date**: 2025-12-15

## Entities

### SlowQueryConfig

Configuration state for slow query detection and highlighting.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| enabled | bool | Whether slow query highlighting is active | Default: False |
| warning_ms | float | Threshold for warning level (yellow) | > 0, < slow_ms |
| slow_ms | float | Threshold for slow level (orange/bold yellow) | > warning_ms, < critical_ms |
| critical_ms | float | Threshold for critical level (red bold) | > slow_ms |

**Default Values**:
- warning_ms: 100.0
- slow_ms: 500.0
- critical_ms: 1000.0

**State Transitions**:
```
[Disabled] --slow 100 500 1000--> [Enabled with custom thresholds]
[Enabled]  --slow off-----------> [Disabled]
[Enabled]  --slow 10 100 500----> [Enabled with new thresholds]
```

**Methods**:
- `get_level(duration_ms: float) -> SlowQueryLevel | None`: Returns the threshold level for a duration, or None if below warning
- `format_thresholds() -> str`: Human-readable threshold display

---

### SlowQueryLevel

Enumeration of slow query severity levels.

| Value | Display | Style | Meaning |
|-------|---------|-------|---------|
| WARNING | "warning" | fg:yellow | Duration > warning_ms |
| SLOW | "slow" | fg:yellow bold | Duration > slow_ms |
| CRITICAL | "critical" | fg:red bold | Duration > critical_ms |

---

### DurationStats

Session-scoped collection of query duration samples for statistical analysis.

| Field | Type | Description |
|-------|------|-------------|
| samples | list[float] | All observed duration values (ms) |
| _sum | float | Running sum for O(1) average |
| _min | float | Minimum observed duration |
| _max | float | Maximum observed duration |

**Derived Properties** (computed on access):
- `count`: Number of samples (len of samples list)
- `average`: Mean duration (_sum / count)
- `min`: Minimum duration
- `max`: Maximum duration
- `p50`: 50th percentile (median)
- `p95`: 95th percentile
- `p99`: 99th percentile

**Methods**:
- `add(duration_ms: float) -> None`: Add a sample and update running stats
- `clear() -> None`: Reset all statistics
- `is_empty() -> bool`: Check if no samples collected
- `format_summary() -> str`: Human-readable statistics output

**Memory Considerations**:
- Each sample: 8 bytes (Python float)
- 10,000 samples: ~80 KB
- No upper limit enforced (session-scoped)

---

### DurationMatch

Result of parsing a log line for duration information.

| Field | Type | Description |
|-------|------|-------------|
| duration_ms | float | Extracted duration in milliseconds |
| original_value | float | Original numeric value from log |
| original_unit | str | Original unit ("ms" or "s") |

**Factory Method**:
- `parse(text: str) -> DurationMatch | None`: Extract duration from log line text

**Parsing Logic**:
```
Pattern: duration:\s*(\d+\.?\d*)\s*(ms|s)
- If unit is "s": duration_ms = value * 1000
- If unit is "ms": duration_ms = value
- Returns None if pattern not found or value invalid
```

---

## Entity Relationships

```
AppState (existing)
├── slow_query_config: SlowQueryConfig      # NEW: Configuration for slow query detection
└── duration_stats: DurationStats           # NEW: Session statistics collector

LogEntry (existing, modified)
├── timestamp
├── level
├── message
├── raw
├── pid
└── duration_ms: float | None               # NEW: Extracted duration if present

SlowQueryConfig
├── get_level() --> SlowQueryLevel | None
└── uses default thresholds from constants

DurationStats
├── add() <-- called when duration found in log entry
└── format_summary() --> stats command output
```

---

## Integration Points

### AppState Modifications

Add to existing `AppState` dataclass in `cli.py`:

```python
@dataclass
class AppState:
    # ... existing fields ...
    slow_query_config: SlowQueryConfig = field(default_factory=SlowQueryConfig)
    duration_stats: DurationStats = field(default_factory=DurationStats)
```

### LogEntry Modifications

Optionally extend `LogEntry` in `parser.py` OR compute duration lazily:

**Option A: Extend LogEntry** (recommended)
```python
@dataclass
class LogEntry:
    # ... existing fields ...
    duration_ms: float | None = None  # Extracted during parsing
```

**Option B: Lazy extraction**
```python
# In display logic
duration_ms = extract_duration(entry.message)
```

**Decision**: Option A - parse once during log line parsing for efficiency.

---

## Validation Rules

### Threshold Validation

When user provides `slow 100 500 1000`:

1. All three values must be provided
2. All values must be positive numbers
3. Values must be in ascending order: warning < slow < critical
4. If validation fails: display error, retain previous thresholds

```python
def validate_thresholds(warning: float, slow: float, critical: float) -> str | None:
    """Returns error message if invalid, None if valid."""
    if warning <= 0 or slow <= 0 or critical <= 0:
        return "All thresholds must be positive numbers"
    if not (warning < slow < critical):
        return "Thresholds must be in ascending order: warning < slow < critical"
    return None
```

### Duration Parsing Validation

- Non-matching lines: `None` (no error, just no duration)
- Negative values: Treat as invalid, return `None`
- Zero values: Valid (very fast query)
- Very large values: Valid (no upper limit)
