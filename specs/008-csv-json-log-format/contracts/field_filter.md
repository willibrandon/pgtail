# Field Filter Contract

**Module**: `pgtail_py/field_filter.py`

## FieldFilter Dataclass

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FieldFilter:
    """A single field filter condition.

    Attributes:
        field: Canonical field name (e.g., "app", "db")
        value: Value to match (case-sensitive exact match)
    """
    field: str
    value: str

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry matches this filter.

        Args:
            entry: Log entry to check

        Returns:
            True if entry's field value equals this filter's value.
            False if field is not available in entry.
        """
        ...
```

---

## FieldFilterState Class

```python
class FieldFilterState:
    """Manages active field filters.

    Filters are combined with AND logic - an entry must match
    all active filters to pass.
    """

    def __init__(self) -> None:
        self._filters: dict[str, FieldFilter] = {}

    def add(self, field: str, value: str) -> None:
        """Add or update a filter for a field.

        Args:
            field: Canonical field name or alias
            value: Value to match

        Raises:
            ValueError: If field name is not recognized
        """
        ...

    def remove(self, field: str) -> bool:
        """Remove filter for a field.

        Args:
            field: Canonical field name or alias

        Returns:
            True if filter was removed, False if no filter existed
        """
        ...

    def clear(self) -> None:
        """Remove all filters."""
        ...

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry passes all active filters.

        Args:
            entry: Log entry to check

        Returns:
            True if entry matches all filters (or no filters active).
            False if any filter doesn't match.
        """
        ...

    def is_active(self) -> bool:
        """Check if any filters are currently active."""
        return len(self._filters) > 0

    def active_filters(self) -> list[FieldFilter]:
        """Get list of active filters."""
        return list(self._filters.values())

    def format_status(self) -> str:
        """Format active filters for display.

        Returns:
            String like "Filters: app=myapp, db=prod" or "No field filters"
        """
        ...
```

---

## Field Name Resolution

```python
# Canonical field names and their aliases
FIELD_ALIASES: dict[str, str] = {
    # Alias -> Canonical
    "app": "application",
    "application": "application",
    "db": "database",
    "database": "database",
    "user": "user",
    "pid": "pid",
    "backend": "backend",
}

# Canonical name -> LogEntry attribute
FIELD_ATTRIBUTES: dict[str, str] = {
    "application": "application_name",
    "database": "database_name",
    "user": "user_name",
    "pid": "pid",
    "backend": "backend_type",
}


def resolve_field_name(name: str) -> str:
    """Resolve a field name or alias to canonical name.

    Args:
        name: Field name or alias (case-insensitive)

    Returns:
        Canonical field name

    Raises:
        ValueError: If name is not recognized
    """
    ...


def get_available_field_names() -> list[str]:
    """Get list of all available field names for filtering.

    Returns:
        List of canonical field names that can be filtered.
    """
    return list(FIELD_ATTRIBUTES.keys())
```

---

## Integration with Existing Filters

Field filtering integrates with the existing filter chain in `LogTailer._should_show()`:

```python
def _should_show(self, entry: LogEntry) -> bool:
    """Check if a log entry should be displayed.

    Filter order (cheapest first):
    1. Time filter - datetime comparison O(1)
    2. Level filter - set membership O(1)
    3. Field filter - string equality O(1)
    4. Regex filter - regex match O(n)
    """
    # Time filter
    if self._time_filter and not self._time_filter.matches(entry):
        return False

    # Level filter
    if self._active_levels and entry.level not in self._active_levels:
        return False

    # Field filter (NEW)
    if self._field_filter and not self._field_filter.matches(entry):
        return False

    # Regex filter
    if self._regex_state and self._regex_state.has_filters():
        if not self._regex_state.should_show(entry.raw):
            return False

    return True
```
