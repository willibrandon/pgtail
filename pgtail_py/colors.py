"""Color output for PostgreSQL log entries using prompt_toolkit styles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from pgtail_py.filter import LogLevel
from pgtail_py.parser import LogEntry
from pgtail_py.slow_query import SlowQueryLevel
from pgtail_py.utils import is_color_disabled

if TYPE_CHECKING:
    from pgtail_py.theme import ThemeManager

# Style definitions for each log level
# Using ANSI color names that work across terminals
# NOTE: This is the fallback style when no ThemeManager is available
LEVEL_STYLES = {
    LogLevel.PANIC: "bold fg:white bg:red",
    LogLevel.FATAL: "bold fg:red",
    LogLevel.ERROR: "fg:red",
    LogLevel.WARNING: "fg:yellow",
    LogLevel.NOTICE: "fg:cyan",
    LogLevel.LOG: "fg:ansidefault",
    LogLevel.INFO: "fg:green",
    LogLevel.DEBUG1: "fg:ansibrightblack",
    LogLevel.DEBUG2: "fg:ansibrightblack",
    LogLevel.DEBUG3: "fg:ansibrightblack",
    LogLevel.DEBUG4: "fg:ansibrightblack",
    LogLevel.DEBUG5: "fg:ansibrightblack",
}

# Build the style object from level styles
# Note: Style keys don't have "class:" prefix - that's only for FormattedText tuples
_STYLE_RULES = [(level.name.lower(), style) for level, style in LEVEL_STYLES.items()]
_STYLE_RULES.extend(
    [
        ("timestamp", "fg:ansibrightblack"),
        ("pid", "fg:ansibrightblack"),
        ("highlight", "fg:black bg:yellow"),  # Yellow background for highlights
        ("slow_warning", "fg:yellow"),
        ("slow_slow", "fg:yellow bold"),
        ("slow_critical", "fg:red bold"),
        ("detail", "fg:ansidefault"),  # Secondary fields in full mode
    ]
)
LOG_STYLE = Style(_STYLE_RULES)


def get_style(theme_manager: ThemeManager | None = None) -> Style:
    """Get the current style from ThemeManager or fallback.

    Args:
        theme_manager: Optional ThemeManager instance.

    Returns:
        Style from theme manager if available, else LOG_STYLE fallback.
    """
    if theme_manager is not None:
        return theme_manager.get_style()
    return LOG_STYLE


# Standalone highlight style for direct use
HIGHLIGHT_STYLE = "fg:black bg:yellow"

# Slow query severity styles
# Using ANSI colors for maximum terminal compatibility
SLOW_QUERY_STYLES = {
    SlowQueryLevel.WARNING: "fg:yellow",
    SlowQueryLevel.SLOW: "fg:yellow bold",
    SlowQueryLevel.CRITICAL: "fg:red bold",
}


def format_log_entry(entry: LogEntry) -> FormattedText:
    """Format a log entry with appropriate styling.

    Args:
        entry: The log entry to format.

    Returns:
        FormattedText suitable for print_formatted_text().
    """
    level_class = f"class:{entry.level.name.lower()}"
    parts: list[tuple[str, str]] = []

    # Timestamp
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(("class:timestamp", f"{ts_str} "))

    # PID
    if entry.pid:
        parts.append(("class:pid", f"[{entry.pid}] "))

    # Level and message
    level_name = entry.level.name.ljust(7)  # Align level names
    parts.append((level_class, f"{level_name}: {entry.message}"))

    return FormattedText(parts)


def format_log_entry_with_highlights(
    entry: LogEntry,
    highlight_spans: list[tuple[int, int]],
) -> FormattedText:
    """Format a log entry with highlighted spans.

    Applies yellow background highlighting to specified character ranges
    in the message portion of the log entry.

    Args:
        entry: The log entry to format.
        highlight_spans: List of (start, end) tuples for highlight positions
                        relative to the message text.

    Returns:
        FormattedText suitable for print_formatted_text().
    """
    level_class = f"class:{entry.level.name.lower()}"
    parts: list[tuple[str, str]] = []

    # Timestamp
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(("class:timestamp", f"{ts_str} "))

    # PID
    if entry.pid:
        parts.append(("class:pid", f"[{entry.pid}] "))

    # Level name
    level_name = entry.level.name.ljust(7)
    parts.append((level_class, f"{level_name}: "))

    # Message with highlights applied
    message = entry.message
    if not highlight_spans:
        parts.append((level_class, message))
    else:
        # Sort spans and apply highlights
        sorted_spans = sorted(highlight_spans, key=lambda x: x[0])
        pos = 0
        for start, end in sorted_spans:
            # Skip invalid or overlapping spans
            if start < pos or start >= len(message):
                continue
            end = min(end, len(message))

            # Text before highlight
            if start > pos:
                parts.append((level_class, message[pos:start]))

            # Highlighted text
            parts.append(("class:highlight", message[start:end]))
            pos = end

        # Remaining text after last highlight
        if pos < len(message):
            parts.append((level_class, message[pos:]))

    return FormattedText(parts)


def format_slow_query_entry(entry: LogEntry, level: SlowQueryLevel) -> FormattedText:
    """Format a log entry with slow query styling.

    Applies the appropriate slow query color to the entire line based on
    the severity level (warning, slow, or critical).

    Args:
        entry: The log entry to format.
        level: The slow query severity level.

    Returns:
        FormattedText suitable for print_formatted_text().
    """
    style_class = f"class:slow_{level.value}"
    parts: list[tuple[str, str]] = []

    # Timestamp
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(("class:timestamp", f"{ts_str} "))

    # PID
    if entry.pid:
        parts.append(("class:pid", f"[{entry.pid}] "))

    # Level name and message - all in slow query style
    level_name = entry.level.name.ljust(7)
    parts.append((style_class, f"{level_name}: {entry.message}"))

    return FormattedText(parts)


def print_log_entry(entry: LogEntry, style: Style | None = None) -> None:
    """Print a log entry with color-coded styling.

    Uses prompt_toolkit's print_formatted_text for proper terminal handling.
    Respects NO_COLOR environment variable.

    Args:
        entry: The log entry to print.
        style: Optional custom style. Uses LOG_STYLE if not provided.
    """
    if is_color_disabled():
        # Plain output when NO_COLOR is set
        print(entry.raw)
        return

    formatted = format_log_entry(entry)
    print_formatted_text(formatted, style=style or LOG_STYLE)
