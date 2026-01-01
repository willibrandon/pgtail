"""Display formatting for PostgreSQL log entries.

Supports multiple display modes (compact, full, custom) and output formats
(text, JSON) for rich error display with SQL state codes and extended fields.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Any

from prompt_toolkit.formatted_text import FormattedText, OneStyleAndTextTuple

from pgtail_py.sql_detector import detect_sql_content
from pgtail_py.sql_highlighter import highlight_sql

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


class DisplayMode(Enum):
    """Log entry display modes."""

    COMPACT = "compact"  # Single line: timestamp [pid] level sql_state: message
    FULL = "full"  # All available fields with labels
    CUSTOM = "custom"  # User-selected fields only


class OutputFormat(Enum):
    """Output serialization formats."""

    TEXT = "text"  # Human-readable colored output (default)
    JSON = "json"  # Machine-readable JSON, one object per line


# Field display order for full mode
FULL_DISPLAY_ORDER: list[str] = [
    # Primary line fields (shown inline)
    "timestamp",
    "pid",
    "level",
    "sql_state",
    "message",
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

# Valid field names for custom display (user-facing, with aliases)
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

# Mapping from user-facing field names to LogEntry attribute names
_FIELD_TO_ATTR: dict[str, str] = {
    "user": "user_name",
    "database": "database_name",
    "application": "application_name",
}

# Labels for secondary fields in full mode
_FIELD_LABELS: dict[str, str] = {
    "application_name": "Application",
    "database_name": "Database",
    "user_name": "User",
    "query": "Query",
    "detail": "Detail",
    "hint": "Hint",
    "context": "Context",
    "location": "Location",
    "backend_type": "Backend",
    "session_id": "Session",
}


def get_valid_display_fields() -> list[str]:
    """Get list of valid field names for custom display."""
    return sorted(VALID_DISPLAY_FIELDS)


def _format_message_with_sql(message: str, level_class: str) -> list[OneStyleAndTextTuple]:
    """Format a log message with SQL syntax highlighting if SQL is detected.

    Args:
        message: The log message to format.
        level_class: The style class for the log level (e.g., "class:error").

    Returns:
        List of (style, text) tuples for FormattedText.
    """
    # Try to detect SQL content in the message
    detection = detect_sql_content(message)

    if detection is None:
        # No SQL detected - return message with level styling
        return [(level_class, message)]

    # SQL detected - format with highlighting
    parts: list[OneStyleAndTextTuple] = []

    # Add prefix with level class
    if detection.prefix:
        parts.append((level_class, detection.prefix))

    # Add highlighted SQL
    sql_formatted = highlight_sql(detection.sql)
    parts.extend(list(sql_formatted))

    # Add suffix with level class
    if detection.suffix:
        parts.append((level_class, detection.suffix))

    return parts


class DisplayState:
    """Manages display and output settings.

    Attributes:
        mode: Current display mode
        custom_fields: Fields to show in CUSTOM mode
        output_format: Current output format
    """

    def __init__(self) -> None:
        """Initialize display state with defaults."""
        self._mode: DisplayMode = DisplayMode.COMPACT
        self._custom_fields: list[str] = []
        self._output_format: OutputFormat = OutputFormat.TEXT

    @property
    def mode(self) -> DisplayMode:
        """Get current display mode."""
        return self._mode

    @property
    def custom_fields(self) -> list[str]:
        """Get custom field list."""
        return self._custom_fields

    @property
    def output_format(self) -> OutputFormat:
        """Get current output format."""
        return self._output_format

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
        invalid = [f for f in fields if f not in VALID_DISPLAY_FIELDS]
        valid = [f for f in fields if f in VALID_DISPLAY_FIELDS]

        if valid:
            self._mode = DisplayMode.CUSTOM
            self._custom_fields = valid

        return invalid

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
        mode_str = self._mode.value
        if self._mode == DisplayMode.CUSTOM and self._custom_fields:
            mode_str = f"custom({','.join(self._custom_fields)})"

        return f"Display: {mode_str}, Output: {self._output_format.value}"


def format_entry_compact(entry: LogEntry) -> FormattedText:
    """Format entry in compact mode (single line).

    Format: {timestamp} [{pid}] {level} {sql_state}: {message}

    For structured formats, includes SQL state code.
    For text format, behaves like existing format_log_entry().
    SQL statements in messages are syntax-highlighted.

    Args:
        entry: Log entry to format

    Returns:
        FormattedText for prompt_toolkit
    """
    level_class = f"class:{entry.level.name.lower()}"
    parts: list[OneStyleAndTextTuple] = []

    # Timestamp
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(("class:timestamp", f"{ts_str} "))

    # PID
    if entry.pid:
        parts.append(("class:pid", f"[{entry.pid}] "))

    # Level name
    level_name = entry.level.name.ljust(7)  # Align level names

    # SQL state code (for structured formats)
    if entry.sql_state:
        parts.append((level_class, f"{level_name} {entry.sql_state}: "))
    else:
        parts.append((level_class, f"{level_name}: "))

    # Message with SQL highlighting
    message_parts = _format_message_with_sql(entry.message, level_class)
    parts.extend(message_parts)

    return FormattedText(parts)


def format_entry_full(entry: LogEntry) -> FormattedText:
    """Format entry in full mode (all fields).

    Shows primary line followed by indented secondary fields.
    SQL statements in messages are syntax-highlighted.

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
    level_class = f"class:{entry.level.name.lower()}"
    parts: list[OneStyleAndTextTuple] = []

    # Primary line (same as compact)
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
        parts.append(("class:timestamp", f"{ts_str} "))

    if entry.pid:
        parts.append(("class:pid", f"[{entry.pid}] "))

    level_name = entry.level.name.ljust(7)

    if entry.sql_state:
        parts.append((level_class, f"{level_name} {entry.sql_state}: "))
    else:
        parts.append((level_class, f"{level_name}: "))

    # Message with SQL highlighting
    message_parts = _format_message_with_sql(entry.message, level_class)
    parts.extend(message_parts)

    # Secondary fields (indented)
    secondary_fields = [
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

    for field_name in secondary_fields:
        value = getattr(entry, field_name, None)
        if value is not None:
            label = _FIELD_LABELS.get(field_name, field_name)
            parts.append(("", f"\n  {label}: "))
            # Check if the field might contain SQL (query, detail)
            if field_name in ("query", "detail"):
                field_parts = _format_message_with_sql(str(value), "class:detail")
                parts.extend(field_parts)
            else:
                parts.append(("class:detail", str(value)))

    return FormattedText(parts)


def format_entry_custom(entry: LogEntry, fields: list[str]) -> FormattedText:
    """Format entry with only specified fields.

    SQL statements in message and query fields are syntax-highlighted.

    Args:
        entry: Log entry to format
        fields: Field names to include

    Returns:
        FormattedText for prompt_toolkit
    """
    level_class = f"class:{entry.level.name.lower()}"
    parts: list[OneStyleAndTextTuple] = []
    first = True

    for field_name in fields:
        # Map user-facing names to attribute names
        attr_name = _FIELD_TO_ATTR.get(field_name, field_name)
        value = getattr(entry, attr_name, None)

        if value is None:
            continue

        if not first:
            parts.append(("", " "))
        first = False

        # Format based on field type
        if field_name == "timestamp" and entry.timestamp:
            ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]
            parts.append(("class:timestamp", ts_str))
        elif field_name == "pid" and entry.pid:
            parts.append(("class:pid", f"[{entry.pid}]"))
        elif field_name == "level":
            level_name = entry.level.name.ljust(7)
            parts.append((level_class, level_name))
        elif field_name == "sql_state" and entry.sql_state:
            parts.append((level_class, entry.sql_state))
        elif field_name == "message":
            # Apply SQL highlighting to message
            message_parts = _format_message_with_sql(entry.message, level_class)
            parts.extend(message_parts)
        elif field_name == "query":
            # Query field typically contains SQL
            query_parts = _format_message_with_sql(str(value), "")
            parts.extend(query_parts)
        elif field_name == "detail":
            # Detail field may contain SQL context
            detail_parts = _format_message_with_sql(str(value), "")
            parts.extend(detail_parts)
        else:
            parts.append(("", str(value)))

    return FormattedText(parts)


def format_entry_json(entry: LogEntry) -> str:
    """Format entry as JSON for machine-readable output.

    Outputs a single JSON object per line with all non-None fields.
    Timestamps are ISO 8601 format.

    Args:
        entry: Log entry to format

    Returns:
        JSON string (no trailing newline)
    """
    data: dict[str, Any] = entry.to_dict()
    return json.dumps(data, separators=(",", ":"))


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

    if display_state.mode == DisplayMode.COMPACT:
        return format_entry_compact(entry)
    elif display_state.mode == DisplayMode.FULL:
        return format_entry_full(entry)
    elif display_state.mode == DisplayMode.CUSTOM:
        return format_entry_custom(entry, display_state.custom_fields)

    # Default fallback
    return format_entry_compact(entry)


def format_entry_as_rich(entry: LogEntry) -> str:
    """Format entry as Rich Text markup string for Textual widgets.

    Delegates to tail_rich.format_entry_compact() which returns a Rich
    console markup string with styled log levels, timestamps, and messages.

    This function provides integration between the display module and the
    Textual-based tail mode, allowing consistent formatting across both
    the legacy prompt_toolkit mode and the new Textual mode.

    Args:
        entry: Log entry to format.

    Returns:
        Rich console markup string with styled content.
    """
    from pgtail_py.tail_rich import format_entry_compact as format_rich

    return format_rich(entry)
