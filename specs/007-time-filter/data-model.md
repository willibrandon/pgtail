# Data Model: Time-Based Filtering

**Feature**: 007-time-filter
**Date**: 2025-12-16

## Entities

### TimeFilter

Represents an active time-based filter with optional start and end bounds.

```python
@dataclass
class TimeFilter:
    """Time-based filter for log entries.

    Attributes:
        since: Include entries at or after this time. None means no lower bound.
        until: Include entries at or before this time. None means no upper bound.
        original_input: Original user input string for display purposes.
    """
    since: datetime | None = None
    until: datetime | None = None
    original_input: str = ""

    def matches(self, entry: LogEntry) -> bool:
        """Check if a log entry falls within the time filter.

        Args:
            entry: Log entry to check.

        Returns:
            True if entry matches filter, False otherwise.
            Entries without timestamps return False when any time filter is active.
        """
        ...

    def is_active(self) -> bool:
        """Check if any time constraint is set."""
        ...

    def format_description(self) -> str:
        """Return human-readable description of active filter."""
        ...

    @classmethod
    def empty(cls) -> "TimeFilter":
        """Return an empty (inactive) time filter."""
        ...
```

**Validation Rules**:
- `since` must be <= `until` when both are set
- Invalid ranges raise `ValueError` at construction
- `None` values indicate unbounded (no filter on that side)

**State Transitions**:
- Empty → Active (via `since`, `until`, or `between` command)
- Active → Empty (via `since clear` command)
- Active → Active (new command replaces previous filter)

### ParsedTime (Internal)

Intermediate representation during time parsing, before resolution to datetime.

```python
@dataclass
class ParsedTime:
    """Parsed time value before resolution to datetime.

    Used internally to distinguish relative vs absolute times
    before computing the actual datetime.
    """
    is_relative: bool
    delta: timedelta | None = None  # For relative times
    time_only: time | None = None   # For HH:MM or HH:MM:SS
    datetime_value: datetime | None = None  # For full datetime

    def resolve(self, reference: datetime | None = None) -> datetime:
        """Resolve to absolute datetime.

        Args:
            reference: Reference time for relative times. Defaults to now.

        Returns:
            Resolved datetime.
        """
        ...
```

**Note**: This may be simplified to just returning `datetime` directly from `parse_time()` if the intermediate representation adds no value during implementation.

## Modified Entities

### AppState (cli.py)

Add time filter field to existing dataclass:

```python
@dataclass
class AppState:
    # ... existing fields ...
    time_filter: TimeFilter = field(default_factory=TimeFilter.empty)
```

### LogTailer (tailer.py)

Add time filter support:

```python
class LogTailer:
    def __init__(
        self,
        log_path: Path,
        active_levels: set[LogLevel] | None = None,
        regex_state: FilterState | None = None,
        time_filter: TimeFilter | None = None,  # NEW
        poll_interval: float = 0.1,
    ) -> None:
        ...
        self._time_filter = time_filter

    def update_time_filter(self, time_filter: TimeFilter | None) -> None:
        """Update the time filter.

        Args:
            time_filter: New time filter. None means no time filtering.
        """
        self._time_filter = time_filter
```

## Relationships

```
AppState
├── time_filter: TimeFilter (1:1, new)
├── active_levels: set[LogLevel] | None (1:1, existing)
├── regex_state: FilterState (1:1, existing)
└── tailer: LogTailer | None (1:1, existing)

LogTailer
├── _time_filter: TimeFilter | None (1:1, new)
├── _active_levels: set[LogLevel] | None (1:1, existing)
└── _regex_state: FilterState | None (1:1, existing)

TimeFilter
└── Uses LogEntry.timestamp for matching (1:N, reads)
```

## Functions

### Time Parsing (time_filter.py)

```python
def parse_time(value: str) -> datetime:
    """Parse time string into datetime.

    Supported formats:
    - Relative: 5m, 30s, 2h, 1d (from now)
    - Time only: 14:30, 14:30:45 (today at time)
    - Date-time: 2024-01-15T14:30, 2024-01-15T14:30:00Z

    Args:
        value: Time specification string.

    Returns:
        Resolved datetime.

    Raises:
        ValueError: If value cannot be parsed.
    """
    ...

def is_future_time(dt: datetime) -> bool:
    """Check if datetime is in the future.

    Args:
        dt: Datetime to check.

    Returns:
        True if dt > now.
    """
    ...

def format_time_range(since: datetime | None, until: datetime | None) -> str:
    """Format time range for display.

    Args:
        since: Start time or None.
        until: End time or None.

    Returns:
        Human-readable string like "since 14:30" or "between 14:00 and 15:00".
    """
    ...
```

### Filter Application

Filtering follows the existing pattern in `LogTailer._should_show()`:

```python
# Order of filter evaluation (cheapest first):
1. time_filter.matches(entry)      # datetime comparison: O(1)
2. level in active_levels          # set membership: O(1)
3. regex_state.should_show(raw)    # regex match: O(n) where n = line length
```

## Error Handling

| Error Condition | Response |
|-----------------|----------|
| Invalid time format | ValueError with helpful message listing valid formats |
| Start time > end time | ValueError: "Start time must be before end time" |
| Entry has no timestamp | Return False from `matches()` (skip entry) |
| Future time specified | Warning printed, command proceeds |
