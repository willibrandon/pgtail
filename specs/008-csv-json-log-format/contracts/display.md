# Display Contract

**Module**: `pgtail_py/display.py`

## DisplayMode Enum

```python
from enum import Enum

class DisplayMode(Enum):
    """Log entry display modes."""
    COMPACT = "compact"  # Single line: timestamp [pid] level sql_state: message
    FULL = "full"        # All available fields with labels
    CUSTOM = "custom"    # User-selected fields only
```

---

## OutputFormat Enum

```python
class OutputFormat(Enum):
    """Output serialization formats."""
    TEXT = "text"   # Human-readable colored output (default)
    JSON = "json"   # Machine-readable JSON, one object per line
```

---

## DisplayState Class

```python
class DisplayState:
    """Manages display and output settings.

    Attributes:
        mode: Current display mode
        custom_fields: Fields to show in CUSTOM mode
        output_format: Current output format
    """

    def __init__(self) -> None:
        self._mode: DisplayMode = DisplayMode.COMPACT
        self._custom_fields: list[str] = []
        self._output_format: OutputFormat = OutputFormat.TEXT

    @property
    def mode(self) -> DisplayMode:
        """Get current display mode."""
        return self._mode

    def set_compact(self) -> None:
        """Set display mode to compact."""
        self._mode = DisplayMode.COMPACT

    def set_full(self) -> None:
        """Set display mode to full."""
        self._mode = DisplayMode.FULL

    def set_custom(self, fields: list[str]) -> list[str]:
        """Set display mode to custom with specified fields.

        Args:
            fields: List of field names to display

        Returns:
            List of invalid field names (if any)
        """
        ...

    @property
    def custom_fields(self) -> list[str]:
        """Get custom field list."""
        return self._custom_fields

    @property
    def output_format(self) -> OutputFormat:
        """Get current output format."""
        return self._output_format

    def set_output_json(self) -> None:
        """Set output format to JSON."""
        self._output_format = OutputFormat.JSON

    def set_output_text(self) -> None:
        """Set output format to text."""
        self._output_format = OutputFormat.TEXT

    def format_status(self) -> str:
        """Format current display settings for status display.

        Returns:
            String like "Display: compact, Output: text"
        """
        ...
```

---

## Formatting Functions

```python
def format_entry_compact(entry: LogEntry) -> FormattedText:
    """Format entry in compact mode (single line).

    Format: {timestamp} [{pid}] {level} {sql_state}: {message}

    For structured formats, includes SQL state code.
    For text format, behaves like existing format_log_entry().

    Args:
        entry: Log entry to format

    Returns:
        FormattedText for prompt_toolkit
    """
    ...


def format_entry_full(entry: LogEntry) -> FormattedText:
    """Format entry in full mode (all fields).

    Shows primary line followed by indented secondary fields.

    Example:
        10:23:45.123 [12345] ERROR 42P01: relation "foo" does not exist
          Application: myapp
          Database: mydb
          User: postgres
          Query: SELECT * FROM foo
          Location: parse_relation.c:1234

    Args:
        entry: Log entry to format

    Returns:
        FormattedText for prompt_toolkit
    """
    ...


def format_entry_custom(entry: LogEntry, fields: list[str]) -> FormattedText:
    """Format entry with only specified fields.

    Args:
        entry: Log entry to format
        fields: Field names to include

    Returns:
        FormattedText for prompt_toolkit
    """
    ...


def format_entry_json(entry: LogEntry) -> str:
    """Format entry as JSON for machine-readable output.

    Outputs a single JSON object per line with all non-None fields.
    Timestamps are ISO 8601 format.

    Args:
        entry: Log entry to format

    Returns:
        JSON string (no trailing newline)
    """
    ...


def format_entry(
    entry: LogEntry,
    display_state: DisplayState,
) -> FormattedText | str:
    """Format entry according to current display settings.

    Args:
        entry: Log entry to format
        display_state: Current display settings

    Returns:
        FormattedText for text output, str for JSON output
    """
    if display_state.output_format == OutputFormat.JSON:
        return format_entry_json(entry)

    match display_state.mode:
        case DisplayMode.COMPACT:
            return format_entry_compact(entry)
        case DisplayMode.FULL:
            return format_entry_full(entry)
        case DisplayMode.CUSTOM:
            return format_entry_custom(entry, display_state.custom_fields)
```

---

## Field Display Order

For full mode, fields are displayed in this order:

```python
FULL_DISPLAY_ORDER: list[str] = [
    # Primary line fields (shown inline)
    "timestamp", "pid", "level", "sql_state", "message",
    # Secondary fields (shown indented)
    "application_name",
    "database_name",
    "user_name",
    "query",
    "detail",
    "hint",
    "context",
    "location",
    "backend_type",
    "session_id",
]
```

---

## Valid Field Names for Custom Display

```python
VALID_DISPLAY_FIELDS: set[str] = {
    "timestamp",
    "pid",
    "level",
    "message",
    "sql_state",
    "user",
    "database",
    "application",
    "query",
    "detail",
    "hint",
    "context",
    "location",
    "backend_type",
    "session_id",
    "command_tag",
}

def get_valid_display_fields() -> list[str]:
    """Get list of valid field names for custom display."""
    return sorted(VALID_DISPLAY_FIELDS)
```
