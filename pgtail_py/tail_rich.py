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
from pgtail_py.sql_detector import detect_sql_content
from pgtail_py.sql_highlighter import highlight_sql_rich

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry
    from pgtail_py.theme import Theme


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

# Rich markup tags for log levels (for console markup strings)
LEVEL_MARKUP: dict[LogLevel, str] = {
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


def format_entry_compact(entry: LogEntry, theme: Theme | None = None) -> str:
    """Convert LogEntry to Rich markup string for Textual Log widget.

    Formats a log entry as a single-line Rich markup string suitable for
    the Textual Log widget's write_line() method. Uses a compact
    format: timestamp [pid] LEVEL sql_state: message

    Args:
        entry: Parsed log entry to format.
        theme: Theme for SQL highlighting. If None, uses default colors.

    Returns:
        Rich markup string representation of the entry.
    """
    parts: list[str] = []

    # Timestamp (dim)
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(f"[dim]{ts_str}[/dim]")

    # PID (dim) - escape brackets
    if entry.pid:
        parts.append(f"[dim]\\[{entry.pid}][/dim]")

    # Level name with color (padded for alignment)
    level_style = LEVEL_MARKUP.get(entry.level, "")
    level_name = entry.level.name.ljust(7)
    if level_style:
        parts.append(f"[{level_style}]{level_name}[/]")
    else:
        parts.append(level_name)

    # SQL state code (cyan) and message
    if entry.sql_state:
        parts.append(f"[cyan]{entry.sql_state}[/]:")
    else:
        parts.append(":")

    # Message - detect and highlight SQL content
    detection = detect_sql_content(entry.message)
    if detection:
        # SQL detected: escape prefix, highlight SQL, escape suffix
        prefix = detection.prefix.replace("[", "\\[")
        highlighted_sql = highlight_sql_rich(detection.sql, theme=theme)
        suffix = detection.suffix.replace("[", "\\[")
        parts.append(f"{prefix}{highlighted_sql}{suffix}")
    else:
        # No SQL: just escape brackets to prevent Rich markup parsing
        safe_message = entry.message.replace("[", "\\[")
        parts.append(safe_message)

    return " ".join(parts)
