"""Rich text formatting for log entries in Textual tail mode.

This module provides functions to convert LogEntry objects to Rich Text
for styled display in Textual widgets. Handles log level coloring,
timestamp formatting, SQL syntax highlighting, semantic pattern highlighting,
and secondary field formatting (DETAIL, HINT, CONTEXT, STATEMENT).

Functions:
    format_entry_as_rich: Convert LogEntry to styled Rich Text object.
    format_entry_compact: Convert LogEntry to plain string for Log widget.
    get_highlighter_chain: Get (or create) the cached HighlighterChain.
    register_all_highlighters: Register all built-in highlighters with registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from pgtail_py.filter import LogLevel
from pgtail_py.highlighter import HighlighterChain
from pgtail_py.highlighter_registry import get_registry
from pgtail_py.highlighting_config import HighlightingConfig
from pgtail_py.sql_detector import detect_sql_content
from pgtail_py.sql_highlighter import highlight_sql_rich

if TYPE_CHECKING:
    from pgtail_py.parser import LogEntry
    from pgtail_py.theme import Theme


# Module-level cache for highlighter chain
_highlighter_chain: HighlighterChain | None = None
_highlighting_config: HighlightingConfig | None = None
_highlighters_registered: bool = False


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


# =============================================================================
# Highlighter Chain Management
# =============================================================================


def register_all_highlighters() -> None:
    """Register all built-in highlighters with the registry.

    This should be called once at startup. Subsequent calls are no-ops.
    """
    global _highlighters_registered

    if _highlighters_registered:
        return

    from pgtail_py.highlighters import get_all_highlighters

    registry = get_registry()

    # Category mapping by priority range
    highlighters = get_all_highlighters()
    for h in highlighters:
        priority = h.priority
        if priority < 200:
            category = "structural"
        elif priority < 300:
            category = "diagnostic"
        elif priority < 400:
            category = "performance"
        elif priority < 500:
            category = "objects"
        elif priority < 600:
            category = "wal"
        elif priority < 700:
            category = "connection"
        elif priority < 800:
            category = "sql"
        elif priority < 900:
            category = "lock"
        elif priority < 1000:
            category = "checkpoint"
        else:
            category = "misc"

        # Only register if not already present (avoids ValueError on duplicate)
        if registry.get(h.name) is None:
            registry.register(h, category)

    _highlighters_registered = True


def get_highlighter_chain(config: HighlightingConfig | None = None) -> HighlighterChain:
    """Get or create the highlighter chain.

    Uses a cached chain if config matches, otherwise creates a new one.

    Args:
        config: Highlighting configuration. If None, uses default config.

    Returns:
        HighlighterChain ready for use.
    """
    global _highlighter_chain, _highlighting_config

    # Ensure highlighters are registered
    register_all_highlighters()

    # Use default config if none provided
    if config is None:
        config = HighlightingConfig()

    # Reuse cached chain if config unchanged
    if _highlighter_chain is not None and _highlighting_config == config:
        return _highlighter_chain

    # Create new chain from registry
    registry = get_registry()
    _highlighter_chain = registry.create_chain(config)
    _highlighting_config = config

    return _highlighter_chain


def reset_highlighter_chain() -> None:
    """Reset the cached highlighter chain.

    Used when configuration changes or for testing.
    Also resets the _highlighters_registered flag so highlighters
    can be re-registered to a fresh registry.
    """
    global _highlighter_chain, _highlighting_config, _highlighters_registered
    _highlighter_chain = None
    _highlighting_config = None
    _highlighters_registered = False


# =============================================================================
# Entry Formatting
# =============================================================================


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


def format_entry_compact(
    entry: LogEntry,
    theme: Theme | None = None,
    use_semantic_highlighting: bool = True,
    highlighting_config: HighlightingConfig | None = None,
) -> str:
    """Convert LogEntry to Rich markup string for Textual Log widget.

    Formats a log entry as a single-line Rich markup string suitable for
    the Textual Log widget's write_line() method. Uses a compact
    format: [source_file] timestamp [pid] LEVEL sql_state: message

    When source_file is set (multi-file mode), shows the filename in
    brackets before the timestamp for easy identification. (T076)

    When use_semantic_highlighting is True (default), applies semantic
    pattern highlighting to the message content (durations, error names,
    WAL segments, lock types, etc.).

    Args:
        entry: Parsed log entry to format.
        theme: Theme for SQL highlighting. If None, uses default colors.
        use_semantic_highlighting: Whether to apply semantic highlighting.
        highlighting_config: Highlighting configuration with custom highlighters.
            If None, uses default config (no custom highlighters).

    Returns:
        Rich markup string representation of the entry.
    """
    parts: list[str] = []

    # T076: Source file indicator for multi-file mode (before timestamp)
    if entry.source_file:
        # Use magenta for source file to stand out
        parts.append(f"[magenta]\\[{entry.source_file}][/magenta]")

    # Timestamp (dim)
    if entry.timestamp:
        ts_str = entry.timestamp.strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm
        parts.append(f"[dim]{ts_str}[/dim]")

    # PID (dim) - escape brackets, pad to 5 digits for alignment
    if entry.pid:
        pid_str = str(entry.pid).ljust(5)  # Left-pad to 5 digits
        parts.append(f"[dim]\\[{pid_str}][/dim]")

    # Level name with color (padded for alignment) + colon
    # Combined into one part so " ".join() doesn't add space between level and colon
    level_style = LEVEL_MARKUP.get(entry.level, "")
    level_name = entry.level.name.ljust(7)

    if entry.sql_state:
        # Level + SQL state + colon
        if level_style:
            parts.append(f"[{level_style}]{level_name}[/][cyan]{entry.sql_state}[/]:")
        else:
            parts.append(f"{level_name}[cyan]{entry.sql_state}[/]:")
    else:
        # Level + colon
        if level_style:
            parts.append(f"[{level_style}]{level_name}[/]:")
        else:
            parts.append(f"{level_name}:")

    # Message - apply highlighting
    if use_semantic_highlighting and theme is not None:
        # Apply semantic highlighting via highlighter chain
        highlighted_message = _highlight_message(entry.message, theme, highlighting_config)
        parts.append(highlighted_message)
    else:
        # Fallback: detect and highlight SQL content only
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


def _highlight_message(
    message: str, theme: Theme, config: HighlightingConfig | None = None
) -> str:
    """Apply semantic highlighting to a log message.

    Uses the highlighter chain for pattern-based highlighting. SQL content
    is detected and highlighted using the specialized SQL highlighter
    for better accuracy.

    Args:
        message: Log message to highlight.
        theme: Current theme for style lookups.
        config: Highlighting configuration with custom highlighters.

    Returns:
        Rich markup string with highlighting.
    """
    # Get highlighter chain (with custom highlighters from config)
    chain = get_highlighter_chain(config)

    # Apply semantic highlighting
    return chain.apply_rich(message, theme)
