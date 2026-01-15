"""Highlight CLI command handlers.

Provides commands for managing semantic highlighting:
- highlight list: Show all highlighters with status
- highlight enable <name>: Enable a specific highlighter
- highlight disable <name>: Disable a specific highlighter
"""

from __future__ import annotations

from difflib import get_close_matches
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.highlighter_registry import get_registry
from pgtail_py.highlighting_config import BUILTIN_HIGHLIGHTER_NAMES, save_highlighter_state

if TYPE_CHECKING:
    from collections.abc import Callable

    from pgtail_py.highlighting_config import HighlightingConfig


# =============================================================================
# Highlighter Name Validation
# =============================================================================


def validate_highlighter_name(name: str) -> tuple[bool, str | None]:
    """Validate a highlighter name and suggest corrections for typos.

    Args:
        name: The highlighter name to validate.

    Returns:
        Tuple of (is_valid, suggestion).
        If valid, suggestion is None.
        If invalid, suggestion may contain a close match.
    """
    # Get names from registry (if highlighters are registered)
    registry = get_registry()
    registry_names = registry.all_names()

    # Combine with built-in names (in case registry is not populated)
    all_names = set(registry_names) | set(BUILTIN_HIGHLIGHTER_NAMES)

    # Check if the name exists
    if name in all_names:
        return True, None

    # Not found - look for close matches
    close_matches = get_close_matches(name, list(all_names), n=1, cutoff=0.6)
    if close_matches:
        return False, close_matches[0]

    return False, None


def get_all_highlighter_names() -> list[str]:
    """Get all registered highlighter names.

    Returns:
        Sorted list of all highlighter names.
    """
    # Get names from registry (if highlighters are registered)
    registry = get_registry()
    registry_names = registry.all_names()

    # Combine with built-in names (in case registry is not populated)
    all_names = set(registry_names) | set(BUILTIN_HIGHLIGHTER_NAMES)

    return sorted(all_names)


# =============================================================================
# Built-in Highlighter Metadata
# =============================================================================

# Category and description for each built-in highlighter
HIGHLIGHTER_METADATA: dict[str, tuple[str, str]] = {
    # Structural (100-199)
    "timestamp": ("structural", "Timestamps with date, time, ms, tz"),
    "pid": ("structural", "Process IDs in brackets"),
    "context": ("structural", "DETAIL:, HINT:, CONTEXT: labels"),
    # Diagnostic (200-299)
    "sqlstate": ("diagnostic", "SQLSTATE error codes"),
    "error_name": ("diagnostic", "Error names (unique_violation, etc.)"),
    # Performance (300-399)
    "duration": ("performance", "Query durations with threshold coloring"),
    "memory": ("performance", "Memory values (kB, MB, GB)"),
    "statistics": ("performance", "Checkpoint/vacuum statistics"),
    # Objects (400-499)
    "identifier": ("objects", "Double-quoted identifiers"),
    "relation": ("objects", "Table/index names"),
    "schema": ("objects", "Schema-qualified names"),
    # WAL (500-599)
    "lsn": ("wal", "Log sequence numbers"),
    "wal_segment": ("wal", "WAL segment filenames"),
    "txid": ("wal", "Transaction IDs"),
    # Connection (600-699)
    "connection": ("connection", "Connection info (host, port, user)"),
    "ip": ("connection", "IP addresses"),
    "backend": ("connection", "Backend process types"),
    # SQL (700-799)
    "sql_keyword": ("sql", "SQL keywords"),
    "sql_string": ("sql", "SQL strings"),
    "sql_number": ("sql", "SQL numbers"),
    "sql_param": ("sql", "SQL parameters ($1, $2)"),
    "sql_operator": ("sql", "SQL operators"),
    # Lock (800-899)
    "lock_type": ("lock", "Lock type names"),
    "lock_wait": ("lock", "Lock wait info"),
    # Checkpoint (900-999)
    "checkpoint": ("checkpoint", "Checkpoint messages"),
    "recovery": ("checkpoint", "Recovery messages"),
    # Misc (1000+)
    "boolean": ("misc", "Boolean values"),
    "null": ("misc", "NULL keyword"),
    "oid": ("misc", "Object IDs"),
    "path": ("misc", "File paths"),
}


# =============================================================================
# Highlight List Command
# =============================================================================


def format_highlight_list(config: HighlightingConfig) -> FormattedText:
    """Format the list of all highlighters with their status.

    Args:
        config: Current highlighting configuration.

    Returns:
        FormattedText for display in REPL mode.
    """
    result: list[tuple[str, str]] = []

    # Show global status
    global_status = "enabled" if config.enabled else "disabled"
    global_style = "class:success" if config.enabled else "class:error"
    result.append(("", "Semantic Highlighting: "))
    result.append((global_style, f"{global_status}\n"))
    result.append(("", "\n"))

    # Group highlighters by category
    categories: dict[str, list[str]] = {}
    for name, (category, _) in HIGHLIGHTER_METADATA.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(name)

    # Display order for categories
    category_order = [
        "structural",
        "diagnostic",
        "performance",
        "objects",
        "wal",
        "connection",
        "sql",
        "lock",
        "checkpoint",
        "misc",
    ]

    for category in category_order:
        if category not in categories:
            continue

        names = sorted(categories[category])

        # Category header
        result.append(("class:bold", f"{category.title()}\n"))

        for name in names:
            _, description = HIGHLIGHTER_METADATA[name]
            enabled = config.is_highlighter_enabled(name)
            status_text = "on" if enabled else "off"
            status_style = "class:success" if enabled else "class:error"

            # Format: "  [on ] timestamp    Timestamps with date, time, ms, tz"
            result.append(("", "  ["))
            result.append((status_style, f"{status_text:3}"))
            result.append(("", "] "))
            result.append(("class:highlight", f"{name:20}"))
            result.append(("class:dim", f" {description}\n"))

        result.append(("", "\n"))

    # Show custom highlighters if any
    if config.custom_highlighters:
        result.append(("class:bold", "Custom\n"))
        for custom in config.custom_highlighters:
            enabled = custom.enabled
            status_text = "on" if enabled else "off"
            status_style = "class:success" if enabled else "class:error"

            result.append(("", "  ["))
            result.append((status_style, f"{status_text:3}"))
            result.append(("", "] "))
            result.append(("class:highlight", f"{custom.name:20}"))
            result.append(("class:dim", f" Pattern: {custom.pattern}\n"))
        result.append(("", "\n"))

    return FormattedText(result)


def format_highlight_list_rich(config: HighlightingConfig) -> str:
    """Format the list of all highlighters with their status for Rich/Textual.

    Args:
        config: Current highlighting configuration.

    Returns:
        Rich markup string for display.
    """
    lines: list[str] = []

    # Show global status
    global_status = "enabled" if config.enabled else "disabled"
    global_color = "green" if config.enabled else "red"
    lines.append(f"Semantic Highlighting: [{global_color}]{global_status}[/]\n")

    # Group highlighters by category
    categories: dict[str, list[str]] = {}
    for name, (category, _) in HIGHLIGHTER_METADATA.items():
        if category not in categories:
            categories[category] = []
        categories[category].append(name)

    # Display order for categories
    category_order = [
        "structural",
        "diagnostic",
        "performance",
        "objects",
        "wal",
        "connection",
        "sql",
        "lock",
        "checkpoint",
        "misc",
    ]

    for category in category_order:
        if category not in categories:
            continue

        names = sorted(categories[category])

        # Category header
        lines.append(f"[bold]{category.title()}[/]")

        for name in names:
            _, description = HIGHLIGHTER_METADATA[name]
            enabled = config.is_highlighter_enabled(name)
            status_text = "on" if enabled else "off"
            status_color = "green" if enabled else "red"

            # Escape brackets in description
            desc = description.replace("[", "\\[")
            lines.append(
                f"  \\[[{status_color}]{status_text:3}[/]\\] "
                f"[cyan]{name:20}[/] [dim]{desc}[/]"
            )

        lines.append("")

    # Show custom highlighters if any
    if config.custom_highlighters:
        lines.append("[bold]Custom[/]")
        for custom in config.custom_highlighters:
            enabled = custom.enabled
            status_text = "on" if enabled else "off"
            status_color = "green" if enabled else "red"
            pattern = custom.pattern.replace("[", "\\[")

            lines.append(
                f"  \\[[{status_color}]{status_text:3}[/]\\] "
                f"[cyan]{custom.name:20}[/] [dim]Pattern: {pattern}[/]"
            )
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# Highlight Enable/Disable Commands
# =============================================================================


def handle_highlight_enable(
    name: str,
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Enable a highlighter by name.

    Args:
        name: Highlighter name to enable.
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    is_valid, suggestion = validate_highlighter_name(name)

    if not is_valid:
        # Check if it's a custom highlighter
        custom = config.get_custom(name)
        if custom:
            custom.enabled = True
            # Note: Custom highlighter persistence is handled by save_highlighting_config
            return True, f"Enabled custom highlighter '{name}'."

        if suggestion:
            return False, f"Unknown highlighter '{name}'. Did you mean '{suggestion}'?"
        return False, f"Unknown highlighter '{name}'. Use 'highlight list' to see available highlighters."

    config.enable_highlighter(name)

    # Persist to config.toml
    save_highlighter_state(name, True, warn_func)

    return True, f"Enabled highlighter '{name}'."


def handle_highlight_disable(
    name: str,
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Disable a highlighter by name.

    Args:
        name: Highlighter name to disable.
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    is_valid, suggestion = validate_highlighter_name(name)

    if not is_valid:
        # Check if it's a custom highlighter
        custom = config.get_custom(name)
        if custom:
            custom.enabled = False
            # Note: Custom highlighter persistence is handled by save_highlighting_config
            return True, f"Disabled custom highlighter '{name}'."

        if suggestion:
            return False, f"Unknown highlighter '{name}'. Did you mean '{suggestion}'?"
        return False, f"Unknown highlighter '{name}'. Use 'highlight list' to see available highlighters."

    config.disable_highlighter(name)

    # Persist to config.toml
    save_highlighter_state(name, False, warn_func)

    return True, f"Disabled highlighter '{name}'."


# =============================================================================
# Command Dispatcher
# =============================================================================


def handle_highlight_command(
    args: list[str],
    config: HighlightingConfig,
) -> tuple[bool, str | FormattedText]:
    """Handle highlight command with subcommands.

    Args:
        args: Command arguments after 'highlight'.
        config: Highlighting configuration.

    Returns:
        Tuple of (success, message or formatted output).
    """
    if not args:
        # No subcommand - show list
        return True, format_highlight_list(config)

    subcommand = args[0].lower()

    if subcommand == "list":
        return True, format_highlight_list(config)

    elif subcommand == "enable":
        if len(args) < 2:
            return False, "Usage: highlight enable <name>"
        name = args[1]
        return handle_highlight_enable(name, config)

    elif subcommand == "disable":
        if len(args) < 2:
            return False, "Usage: highlight disable <name>"
        name = args[1]
        return handle_highlight_disable(name, config)

    else:
        # Unknown subcommand - might be a highlighter name for status
        # Or a legacy regex highlight pattern
        return False, f"Unknown subcommand '{subcommand}'. Use 'highlight list', 'highlight enable <name>', or 'highlight disable <name>'."
