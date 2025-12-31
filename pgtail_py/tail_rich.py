"""Rich text formatting for log entries in Textual tail mode.

This module provides functions to convert LogEntry objects to Rich Text
for styled display in Textual widgets. Handles log level coloring,
timestamp formatting, SQL syntax highlighting, and secondary field
formatting (DETAIL, HINT, CONTEXT, STATEMENT).

Functions:
    format_entry_as_rich: Convert LogEntry to styled Rich Text object.
    format_entry_compact: Convert LogEntry to plain string for Log widget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from pgtail_py.filter import LogLevel

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry


# Rich styles for log levels - maps LogLevel to Rich style string
LEVEL_STYLES: dict[LogLevel, str] = {
    LogLevel.PANIC: "bold white on red",
    LogLevel.FATAL: "bold red reverse",
    LogLevel.ERROR: "bold red",
    LogLevel.WARNING: "yellow",
    LogLevel.NOTICE: "cyan",
    LogLevel.LOG: "green",
    LogLevel.INFO: "blue",
    LogLevel.DEBUG1: "dim",
    LogLevel.DEBUG2: "dim",
    LogLevel.DEBUG3: "dim",
    LogLevel.DEBUG4: "dim",
    LogLevel.DEBUG5: "dim",
}


def format_entry_as_rich(entry: LogEntry) -> Text:
    """Convert LogEntry to styled Rich Text object.

    Formats a log entry with Rich styling for display in Textual widgets.
    Includes timestamp, PID, log level (with color), SQL state code,
    and message. Secondary fields (DETAIL, HINT, CONTEXT, STATEMENT)
    are formatted on subsequent lines with indentation.

    Args:
        entry: Parsed log entry to format.

    Returns:
        Rich Text object with styled content.
    """
    text = Text()

    # Timestamp (dim)
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        text.append(ts_str, style="dim")
        text.append(" ")

    # PID (dim)
    if entry.pid:
        text.append(f"[{entry.pid}]", style="dim")
        text.append(" ")

    # Level with color
    level_style = LEVEL_STYLES.get(entry.level, "")
    level_name = entry.level.name.ljust(7)  # Align level names
    text.append(level_name, style=level_style)
    text.append(" ")

    # SQLSTATE code
    if entry.sql_state:
        text.append(entry.sql_state, style="cyan")
        text.append(": ")
    else:
        text.append(": ")

    # Message
    text.append(entry.message)

    # Secondary fields (indented on new lines)
    secondary_fields = [
        ("detail", "DETAIL"),
        ("hint", "HINT"),
        ("context", "CONTEXT"),
        ("statement", "STATEMENT"),
    ]

    for attr, label in secondary_fields:
        value = getattr(entry, attr, None)
        if value:
            text.append(f"\n  {label}: ", style="dim bold")
            text.append(str(value), style="dim")

    return text


def format_entry_compact(entry: LogEntry) -> str:
    """Convert LogEntry to plain string for Textual Log widget.

    Formats a log entry as a single-line plain string suitable for
    the Textual Log widget's write_line() method. Uses a compact
    format: timestamp [pid] LEVEL sql_state: message

    Args:
        entry: Parsed log entry to format.

    Returns:
        Plain text string representation of the entry.
    """
    parts: list[str] = []

    # Timestamp
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(ts_str)

    # PID
    if entry.pid:
        parts.append(f"[{entry.pid}]")

    # Level name (padded for alignment)
    level_name = entry.level.name.ljust(7)
    parts.append(level_name)

    # SQL state code and message
    if entry.sql_state:
        parts.append(f"{entry.sql_state}:")
    else:
        parts.append(":")

    parts.append(entry.message)

    return " ".join(parts)
