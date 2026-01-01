"""Field-based filtering for structured log formats.

Provides filtering by field values like app=, db=, user= for CSV and JSON logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


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
    "host": "host",
    "ip": "host",
    "client": "host",
    "connection_from": "host",
}

# Canonical name -> LogEntry attribute name
FIELD_ATTRIBUTES: dict[str, str] = {
    "application": "application_name",
    "database": "database_name",
    "user": "user_name",
    "pid": "pid",
    "backend": "backend_type",
    "host": "connection_from",
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
    canonical = FIELD_ALIASES.get(name.lower())
    if canonical is None:
        valid_names = sorted(FIELD_ALIASES.keys())
        raise ValueError(f"Unknown field: {name}. Valid fields: {', '.join(valid_names)}")
    return canonical


def get_available_field_names() -> list[str]:
    """Get list of all available field names for filtering.

    Returns:
        List of canonical field names that can be filtered.
    """
    return list(FIELD_ATTRIBUTES.keys())


@dataclass(frozen=True)
class FieldFilter:
    """A single field filter condition.

    Attributes:
        field: Canonical field name (e.g., "application", "database")
        value: Value to match (case-insensitive exact match)
    """

    field: str
    value: str

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry matches this filter.

        Args:
            entry: Log entry to check

        Returns:
            True if entry's field value equals this filter's value (case-insensitive).
            False if field is not available in entry or doesn't match.
        """
        attr_name = FIELD_ATTRIBUTES.get(self.field)
        if attr_name is None:
            return False

        entry_value = getattr(entry, attr_name, None)
        if entry_value is None:
            return False

        # Case-insensitive comparison for string values
        if isinstance(entry_value, str):
            return entry_value.lower() == self.value.lower()

        # For non-string values (like pid), compare directly
        return str(entry_value) == self.value


class FieldFilterState:
    """Manages active field filters.

    Filters are combined with AND logic - an entry must match
    all active filters to pass.
    """

    def __init__(self) -> None:
        """Initialize with no active filters."""
        self._filters: dict[str, FieldFilter] = {}

    def add(self, field: str, value: str) -> None:
        """Add or update a filter for a field.

        Args:
            field: Canonical field name or alias
            value: Value to match

        Raises:
            ValueError: If field name is not recognized
        """
        canonical = resolve_field_name(field)
        self._filters[canonical] = FieldFilter(field=canonical, value=value)

    def remove(self, field: str) -> bool:
        """Remove filter for a field.

        Args:
            field: Canonical field name or alias

        Returns:
            True if filter was removed, False if no filter existed
        """
        try:
            canonical = resolve_field_name(field)
        except ValueError:
            return False

        if canonical in self._filters:
            del self._filters[canonical]
            return True
        return False

    def clear(self) -> None:
        """Remove all filters."""
        self._filters.clear()

    def matches(self, entry: LogEntry) -> bool:
        """Check if entry passes all active filters.

        Args:
            entry: Log entry to check

        Returns:
            True if entry matches all filters (or no filters active).
            False if any filter doesn't match.
        """
        if not self._filters:
            return True

        return all(f.matches(entry) for f in self._filters.values())

    def is_active(self) -> bool:
        """Check if any filters are currently active."""
        return len(self._filters) > 0

    def active_filters(self) -> list[FieldFilter]:
        """Get list of active filters."""
        return list(self._filters.values())

    def format_status(self) -> str:
        """Format active filters for display.

        Returns:
            String like "Field filters: app=myapp, db=prod" or "No field filters"
        """
        if not self._filters:
            return "No field filters"

        parts = [f"{f.field}={f.value}" for f in self._filters.values()]
        return f"Field filters: {', '.join(parts)}"
