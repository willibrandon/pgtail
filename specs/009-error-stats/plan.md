# Implementation Plan: Error Statistics Dashboard

**Branch**: `009-error-stats` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-error-stats/spec.md`

## Summary

Add an `errors` command to pgtail that tracks error events during log tailing and provides statistics, trends, and breakdowns. The feature integrates with the existing log parsing pipeline to capture ERROR, FATAL, PANIC, and WARNING entries, storing them in a session-scoped sliding window. Users can view summaries, trend visualizations, live counters, and filter by SQLSTATE code.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: prompt_toolkit >=3.0.0 (REPL), psutil (detection), tomlkit (config)
**Storage**: In-memory only (session-scoped, no persistence)
**Testing**: pytest with existing test patterns
**Target Platform**: macOS, Linux, Windows (cross-platform)
**Project Type**: Single CLI application
**Performance Goals**: <1s summary display, <5% tailing overhead, <500ms live update
**Constraints**: Memory bounded (sliding window ~10,000 entries), 80-column terminal minimum
**Scale/Scope**: Session-scoped tracking, typical sessions <1 hour

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First | PASS | Single `errors` command with intuitive subcommands; no configuration required for basic use |
| II. Cross-Platform Parity | PASS | Uses only stdlib and existing approved dependencies; no platform-specific code needed |
| III. Graceful Degradation | PASS | Returns "no errors recorded" when no data; degrades gracefully without SQLSTATE codes |
| IV. User-Friendly Feedback | PASS | Color-coded output, clear summaries, actionable messages |
| V. Focused Scope | PASS | Statistics only, no alerting/persistence per spec's Out of Scope |
| VI. Minimal Dependencies | PASS | No new dependencies required; stdlib `collections`, `statistics` modules sufficient |
| VII. Developer Workflow Priority | PASS | Helps debug issues during pgrx development; no configuration needed |

**Post-Design Re-Check**: PASS (2025-12-16)
- Design adds 3 new modules following existing patterns (error_stats.py, error_trend.py, cli_errors.py)
- No new dependencies introduced
- Cross-platform compatibility maintained (stdlib deque, Unicode sparklines)
- Memory bounded by design (deque maxlen)

**Quality Standards**:
- Unit tests for ErrorStats, SQLSTATE parsing, trend calculations
- Type hints on all public functions
- Module docstrings

## Project Structure

### Documentation (this feature)

```text
specs/009-error-stats/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI command specs)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
pgtail_py/
├── error_stats.py       # NEW: ErrorEvent, ErrorStats, SQLStateInfo classes
├── error_trend.py       # NEW: Trend calculation and sparkline rendering
├── cli_errors.py        # NEW: errors command handler
├── cli.py               # MODIFY: Add ErrorStats to AppState, integrate tracking
├── commands.py          # MODIFY: Add errors command to COMMANDS dict
├── tailer.py            # MODIFY: Add callback hook for error tracking
└── ...                  # Existing modules unchanged

tests/
├── test_error_stats.py  # NEW: Unit tests for error tracking
├── test_error_trend.py  # NEW: Unit tests for trend visualization
└── ...                  # Existing tests unchanged
```

**Structure Decision**: Single project structure following existing patterns. New modules for error statistics parallel the existing `slow_query.py` and `cli_slow.py` pattern.

## Complexity Tracking

No violations - design follows existing patterns and requires no new dependencies.

## Design Decisions

### D1: Error Tracking Integration Point

**Decision**: Hook into LogTailer's entry processing via callback mechanism

**Rationale**:
- LogTailer already has `_buffer` and callback patterns (`_format_callback`)
- Adding an `_entry_callback` allows ErrorStats to receive entries without modifying filter logic
- Keeps separation of concerns: tailer handles I/O, stats handles aggregation

**Alternative Rejected**: Polling the tailer's buffer - would require synchronization and duplicate entries

### D2: Memory Bounding Strategy

**Decision**: Use `collections.deque` with maxlen for sliding window

**Rationale**:
- O(1) append and automatic oldest-entry removal
- Simple, stdlib solution
- deque is thread-safe for append/popleft operations

**Alternative Rejected**: Custom ring buffer - unnecessary complexity

### D3: SQLSTATE Code Lookup

**Decision**: Static lookup dict with common PostgreSQL error codes

**Rationale**:
- No external dependency needed
- PostgreSQL error codes are stable
- Can show raw code for unknown values

**Alternative Rejected**: Parsing pg_errcodes.txt at runtime - adds filesystem dependency

### D4: Trend Visualization

**Decision**: Unicode block characters (▁▂▃▄▅▆▇█) with per-minute buckets

**Rationale**:
- Works in all modern terminals
- Compact representation (one char per bucket)
- Same approach used by popular CLI tools (spark, etc.)

**Alternative Rejected**: ASCII-only bars - less visually distinct

### D5: Live Mode Implementation

**Decision**: Use prompt_toolkit's `run_in_terminal` with ANSI cursor control

**Rationale**:
- prompt_toolkit already handles terminal state
- `run_in_terminal` properly saves/restores terminal
- Existing pattern in other CLI tools

**Alternative Rejected**: Full-screen Application - overkill for simple counter

## Integration Points

### AppState Changes

Add to `AppState` dataclass in `cli.py`:
```python
error_stats: ErrorStats = field(default_factory=ErrorStats)
```

### LogTailer Changes

Add optional callback in `LogTailer.__init__`:
```python
on_entry: Callable[[LogEntry], None] | None = None
```

Call in `_read_new_lines` after `_queue.put(entry)`:
```python
if self._on_entry:
    self._on_entry(entry)
```

### Command Registration

Add to `COMMANDS` in `commands.py`:
```python
"errors": "Show error statistics (--trend, --live, --code, --since, clear)"
```

Add completion methods to `PgtailCompleter`:
- `_complete_errors()` for subcommands and flags
