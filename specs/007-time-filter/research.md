# Research: Time-Based Filtering

**Feature**: 007-time-filter
**Date**: 2025-12-16

## 1. Time Parsing Approach

### Decision: Extend existing `parse_since` function

**Rationale**: The `export.py` module already contains `parse_since()` which handles relative times (1h, 30m, 2d, 10s) and ISO 8601 format. Rather than duplicate this logic, we will:
1. Move time parsing to a dedicated `time_filter.py` module
2. Extend to support HH:MM and HH:MM:SS formats for "today at time"
3. Support UTC (Z suffix) vs local timezone interpretation

**Alternatives Considered**:
- External library (dateutil, arrow): Rejected per VI. Minimal Dependencies principle
- Keep `parse_since` in export.py, import from there: Rejected - creates awkward coupling for a core feature
- Multiple parsing functions per format: Rejected - single unified parser is simpler

### Time Format Parsing Priority

1. **Relative time**: `^\d+[smhd]$` → duration from now (e.g., `5m`, `2h`)
2. **Time only (HH:MM)**: `^\d{2}:\d{2}$` → today at specified time
3. **Time only (HH:MM:SS)**: `^\d{2}:\d{2}:\d{2}$` → today at specified time with seconds
4. **ISO 8601 with T**: `^\d{4}-\d{2}-\d{2}T` → datetime.fromisoformat()
5. **Fallback ISO**: datetime.fromisoformat() for any remaining formats

## 2. TimeFilter State Management

### Decision: Dataclass with optional start/end bounds

**Rationale**: Follows the pattern established by `FilterState` (regex) and `SlowQueryConfig`. A dataclass provides:
- Clear field definitions
- Immutable design (create new instance to update)
- Easy integration with AppState

```python
@dataclass
class TimeFilter:
    since: datetime | None = None  # Show entries >= this time
    until: datetime | None = None  # Show entries <= this time
    original_input: str = ""       # For display in status
```

**Alternatives Considered**:
- Simple tuple (start, end): Rejected - no place for original input string
- Dict: Rejected - loses type safety
- Named tuple: Rejected - dataclass provides clearer field access

## 3. Integration with Existing Filters

### Decision: Compose filters in `_should_show` method

**Rationale**: The `LogTailer._should_show()` method already checks level and regex filters. Adding time filter follows the same pattern:

```python
def _should_show(self, entry: LogEntry) -> bool:
    # Check time filter first (cheapest comparison)
    if self._time_filter and not self._time_filter.matches(entry):
        return False
    # Check level filter
    if self._active_levels is not None and entry.level not in self._active_levels:
        return False
    # Check regex filter
    if self._regex_state and not self._regex_state.should_show(entry.raw):
        return False
    return True
```

**Order matters**: Time filter first because datetime comparison is faster than regex matching.

## 4. File Seeking Strategy

### Decision: Sequential scan (no binary search)

**Rationale**: Binary search optimization was explicitly marked as "nice-to-have but not required" in the spec's Assumptions section. Reasons to defer:

1. **Log structure varies**: PostgreSQL log_line_prefix is configurable; no guaranteed line length
2. **Multi-line entries**: Continuation lines (DETAIL, HINT, CONTEXT) break binary search
3. **Typical file sizes**: Most active log files are <10MB; sequential scan is fast enough
4. **Implementation complexity**: Binary search in variable-width files is error-prone

For typical 10MB log file at ~100 bytes/line: ~100K lines scanned in <100ms.

**Future optimization path** (if needed):
- Index line offsets during initial scan
- Use indexed offsets for binary search on subsequent queries

## 5. Command Syntax Design

### Decision: Follow existing pgtail command patterns

| Command | Syntax | Notes |
|---------|--------|-------|
| `since` | `since <time>` | Shows entries from time onward |
| `until` | `until <time>` | Shows entries up to time (no follow) |
| `between` | `between <start> <end>` | Shows entries in range |
| `since clear` | Clears time filter | Special case, not `clear since` |

**Rationale**:
- `since clear` follows pattern of `filter clear` (existing command)
- Commands are verbs describing the action
- Arguments are natural language order ("since 5 minutes")

## 6. Status Display Integration

### Decision: Add time filter to existing status output

Current status shows: instance, levels, regex filters. Add time filter section:

```
Time filter: since 5m ago (since 14:30:25)
Time filter: between 14:00 and 15:00
```

## 7. Entries Without Timestamps

### Decision: Skip silently during time-filtered viewing

**Rationale**: Per FR-011, system must gracefully handle entries without timestamps. When time filter is active:
- Entries with `timestamp=None` are filtered out
- No warning spam (these are typically continuation lines)
- When no time filter is active, entries display normally

## 8. Future Time Handling

### Decision: Warn user but allow command

**Rationale**: Per FR-013, warn when time is in future. However:
- Don't block the command (user may be waiting for entries)
- Display: "Warning: time is in future, no entries will match yet"
- Useful for `since` in tail mode to start fresh

## Summary of Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| Parsing | Extend existing parse_since | Reuse existing code, add HH:MM support |
| State | Dataclass with since/until/input | Follows FilterState pattern |
| Filter order | Time first, then level, then regex | Datetime comparison is cheapest |
| File seeking | Sequential scan | Log structure doesn't support binary search reliably |
| Command syntax | `since`, `until`, `between`, `since clear` | Follows existing command patterns |
| No-timestamp entries | Skip silently | Graceful degradation per constitution |
| Future times | Warn but allow | Useful for waiting scenarios |
