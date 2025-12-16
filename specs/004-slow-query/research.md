# Research: Slow Query Detection and Highlighting

**Feature**: 004-slow-query
**Date**: 2025-12-15

## 1. PostgreSQL Duration Log Formats

### Research Question
What are the exact log formats PostgreSQL uses for query duration output?

### Findings

PostgreSQL logs duration information in two primary formats depending on configuration:

**1. log_duration = on**
```
2024-01-15 10:30:45.123 UTC [12345] LOG:  duration: 234.567 ms
```
- Logs duration of every completed statement
- Appears as separate LOG entry after statement execution

**2. log_min_duration_statement = N**
```
2024-01-15 10:30:45.123 UTC [12345] LOG:  duration: 234.567 ms  statement: SELECT * FROM users WHERE id = 1
```
- Only logs statements exceeding N milliseconds
- Combines duration and statement in single line

**Duration Format Pattern**
```
duration: \d+\.\d+ (ms|s)
```
- Always floating point with decimal
- Unit is "ms" (milliseconds) or "s" (seconds)
- Space between number and unit

### Decision
Parse duration using regex: `duration:\s*(\d+\.?\d*)\s*(ms|s)`
- Capture group 1: numeric value
- Capture group 2: unit for conversion
- Handle both ms and seconds (multiply s by 1000)

### Alternatives Considered
- Parsing only ms format: Rejected because seconds format exists for long queries
- Using a more complex parser: Rejected due to simplicity principle

---

## 2. Percentile Calculation for Statistics

### Research Question
How to efficiently calculate percentiles (p50, p95, p99) for potentially 10,000+ duration samples?

### Findings

**Python stdlib approach** using `statistics.quantiles()` (Python 3.8+):
```python
from statistics import quantiles

# For p50, p95, p99:
p50, p95, p99 = quantiles(data, n=100)[49], quantiles(data, n=100)[94], quantiles(data, n=100)[98]
```

**Performance characteristics**:
- `statistics.quantiles()` sorts the data internally (O(n log n))
- For 10,000 samples, sorting takes ~1-2ms on modern hardware
- Memory: stores all samples (8 bytes per float × 10,000 = 80KB)

**Alternative: Approximate algorithms**:
- t-digest: O(1) memory, but requires external dependency
- reservoir sampling: fixed memory, but approximate

### Decision
Use Python stdlib `statistics` module with full sample storage:
- `statistics.mean()` for average
- `statistics.quantiles(n=100)` for percentiles
- Simple list for sample collection

**Rationale**:
- No new dependencies (Constitution VI)
- 80KB memory for 10,000 samples is acceptable
- Exact percentiles preferred over approximations for debugging use case
- Performance target (<500ms) easily met

### Alternatives Considered
- t-digest algorithm: Rejected due to dependency requirement
- Reservoir sampling: Rejected due to approximate nature
- numpy: Rejected due to heavy dependency for simple calculation

---

## 3. prompt_toolkit Color Styles for Three-Tier Highlighting

### Research Question
What prompt_toolkit styles should be used for warning/slow/critical thresholds?

### Findings

Current pgtail uses ANSI color names from prompt_toolkit:
```python
LEVEL_STYLES = {
    LogLevel.WARNING: "fg:yellow",
    LogLevel.ERROR: "fg:red",
    # ...
}
```

**Available ANSI colors for three-tier system**:
- Warning: `fg:yellow` - standard warning color
- Slow: `fg:ansiyellow` with `bold` OR `fg:orange` (may not work on all terminals)
- Critical: `fg:red bold` - high visibility

**Cross-platform considerations**:
- ANSI 16-color palette is most portable
- Orange not in base ANSI palette; use bright yellow or 256-color
- Bold works universally

### Decision
```python
SLOW_QUERY_STYLES = {
    "warning": "fg:yellow",           # >warning_ms threshold
    "slow": "fg:yellow bold",         # >slow_ms threshold (bold yellow as "orange" substitute)
    "critical": "fg:red bold",        # >critical_ms threshold
}
```

**Rationale**:
- Maximum terminal compatibility
- Clear visual distinction between levels
- Consistent with existing WARNING (yellow) and ERROR (red) patterns

### Alternatives Considered
- Using 256-color orange (#FFA500): Rejected due to terminal compatibility concerns
- Background colors: Rejected to avoid conflict with highlight feature
- Underline for middle tier: Rejected as less visible than bold

---

## 4. Integration with Existing Highlighting

### Research Question
How should slow query highlighting interact with existing regex highlighting?

### Findings

From spec clarification session:
> Q: When slow query highlighting and regex highlighting both match, how should they interact?
> A: Replace - slow query color completely overrides regex highlight color

Current highlight flow in `tailer.py` and `colors.py`:
1. Log entry parsed
2. If regex highlights active, `format_log_entry_with_highlights()` called
3. Highlighted spans use `class:highlight` style

**Integration approach**:
- Check for slow query match BEFORE regex highlight check
- If duration exceeds threshold, apply slow query style to entire line
- Skip regex highlighting for that line

### Decision
Modify display logic in CLI/tailer:
```python
def display_entry(entry, slow_config, regex_state):
    duration_ms = extract_duration(entry.message)

    # Slow query takes precedence
    if slow_config.enabled and duration_ms is not None:
        level = slow_config.get_level(duration_ms)
        if level is not None:
            return format_with_slow_query_style(entry, level)

    # Fall back to regex highlighting
    if regex_state.has_highlights():
        return format_with_highlights(entry, regex_state)

    # Default formatting
    return format_log_entry(entry)
```

---

## 5. Statistics Data Structure

### Research Question
What data structure efficiently stores duration samples for session-scoped statistics?

### Findings

Requirements:
- Append-only during session (no deletions)
- Need: count, sum (for avg), min, max, all values (for percentiles)
- Memory budget: reasonable for 10,000+ samples

**Option 1: List-based**
```python
@dataclass
class DurationStats:
    samples: list[float] = field(default_factory=list)

    def add(self, duration_ms: float) -> None:
        self.samples.append(duration_ms)

    def percentile(self, p: int) -> float:
        return statistics.quantiles(self.samples, n=100)[p-1]
```

**Option 2: Incremental with list**
```python
@dataclass
class DurationStats:
    samples: list[float] = field(default_factory=list)
    _sum: float = 0.0
    _min: float = float('inf')
    _max: float = 0.0
```

### Decision
Use Option 2 (incremental tracking with list):
- O(1) for count, avg, min, max
- List required for percentiles anyway
- Memory: ~80KB for 10,000 samples (acceptable)

---

## Summary

All research questions resolved. No NEEDS CLARIFICATION items remain.

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Duration parsing | Regex `duration:\s*(\d+\.?\d*)\s*(ms|s)` | Handles both formats |
| Percentiles | Python `statistics.quantiles()` | No deps, exact results |
| Colors | yellow / yellow bold / red bold | Terminal compatibility |
| Highlight precedence | Slow query replaces regex | Per spec clarification |
| Stats storage | List + incremental counters | O(1) basic stats, percentiles supported |
