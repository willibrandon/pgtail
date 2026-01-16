"""Highlight CLI command handlers.

Provides commands for managing semantic highlighting:
- highlight list: Show all highlighters with status
- highlight enable <name>: Enable a specific highlighter
- highlight disable <name>: Disable a specific highlighter
- highlight add <name> <pattern>: Add a custom regex highlighter
- highlight remove <name>: Remove a custom highlighter
- highlight export [--file <path>]: Export config as TOML
- highlight import <path>: Import config from TOML file
- highlight preview: Preview highlighting with sample log lines
"""

from __future__ import annotations

import contextlib
from difflib import get_close_matches
from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

from pgtail_py.highlighter_registry import get_registry
from pgtail_py.highlighting_config import (
    BUILTIN_HIGHLIGHTER_NAMES,
    CustomHighlighter,
    save_highlighter_state,
    save_highlighting_config,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pgtail_py.highlighting_config import HighlightingConfig
    from pgtail_py.theme import Theme


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
# Highlight Add/Remove Commands (Custom Highlighters)
# =============================================================================


def parse_add_args(args: list[str]) -> tuple[str | None, str | None, str, int | None]:
    """Parse arguments for 'highlight add' command.

    Expected format: <name> <pattern> [--style <style>] [--priority <num>]

    Args:
        args: Arguments after 'highlight add'.

    Returns:
        Tuple of (name, pattern, style, priority). Name or pattern may be None if missing.
        Priority is None if not specified (will use default).
    """
    if len(args) < 2:
        return None, None, "yellow", None

    name = args[0]
    pattern = args[1]
    style = "yellow"  # default
    priority: int | None = None

    # Look for --style and --priority flags
    i = 2
    while i < len(args):
        if args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
        elif args[i] == "--priority" and i + 1 < len(args):
            with contextlib.suppress(ValueError):
                priority = int(args[i + 1])
            i += 2
        else:
            i += 1

    return name, pattern, style, priority


def validate_custom_name(name: str, config: HighlightingConfig) -> tuple[bool, str | None]:
    """Validate a custom highlighter name.

    Checks:
    1. Name is not empty
    2. Name contains only alphanumeric and underscore
    3. Name does not conflict with built-in highlighters
    4. Name does not conflict with existing custom highlighters

    Args:
        name: Proposed highlighter name.
        config: Current highlighting configuration.

    Returns:
        Tuple of (is_valid, error_message).
    """
    import re

    if not name:
        return False, "Name cannot be empty"

    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return False, "Name must start with a letter and contain only lowercase letters, numbers, and underscores"

    if name in BUILTIN_HIGHLIGHTER_NAMES:
        return False, f"Name '{name}' conflicts with built-in highlighter"

    if config.get_custom(name):
        return False, f"Custom highlighter '{name}' already exists"

    return True, None


def handle_highlight_add(
    args: list[str],
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Handle 'highlight add <name> <pattern> [--style <style>]' command.

    Args:
        args: Command arguments after 'highlight add'.
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    from pgtail_py.highlighter import validate_custom_pattern

    name, pattern, style, priority = parse_add_args(args)

    if not name or not pattern:
        return False, "Usage: highlight add <name> <pattern> [--style <style>] [--priority <num>]"

    # Validate name
    name_valid, name_error = validate_custom_name(name, config)
    if not name_valid:
        return False, name_error or "Invalid name"

    # Validate pattern
    pattern_valid, pattern_error = validate_custom_pattern(pattern)
    if not pattern_valid:
        return False, pattern_error or "Invalid pattern"

    # Use provided priority or default (1050 + count)
    final_priority = priority if priority is not None else 1050 + len(config.custom_highlighters)

    # Create and add custom highlighter
    custom = CustomHighlighter(
        name=name,
        pattern=pattern,
        style=style,
        priority=final_priority,
        enabled=True,
    )

    try:
        config.add_custom(custom)
    except ValueError as e:
        return False, str(e)

    # Persist to config.toml
    save_highlighting_config(config, warn_func)

    return True, f"Added custom highlighter '{name}' with pattern '{pattern}'."


def handle_highlight_remove(
    name: str,
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Handle 'highlight remove <name>' command.

    Args:
        name: Custom highlighter name to remove.
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    # Check if it's a built-in highlighter
    if name in BUILTIN_HIGHLIGHTER_NAMES:
        return False, f"Cannot remove built-in highlighter '{name}'. Use 'highlight disable {name}' instead."

    # Try to remove custom highlighter
    if not config.remove_custom(name):
        # Check if it exists at all
        custom_names = [c.name for c in config.custom_highlighters]
        if custom_names:
            return False, f"Custom highlighter '{name}' not found. Available: {', '.join(custom_names)}"
        return False, f"Custom highlighter '{name}' not found. No custom highlighters defined."

    # Persist to config.toml
    save_highlighting_config(config, warn_func)

    return True, f"Removed custom highlighter '{name}'."


# =============================================================================
# Highlight Export/Import Commands (T138-T142)
# =============================================================================


def parse_export_args(args: list[str]) -> str | None:
    """Parse arguments for 'highlight export' command.

    Expected format: [--file <path>]

    Args:
        args: Arguments after 'highlight export'.

    Returns:
        File path if specified, None for stdout.
    """
    i = 0
    while i < len(args):
        if args[i] in ("--file", "-f") and i + 1 < len(args):
            return args[i + 1]
        i += 1
    return None


def handle_highlight_export(
    args: list[str],
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Handle 'highlight export [--file <path>]' command.

    Exports the highlighting configuration as TOML. If no file is specified,
    outputs to stdout (returned as the message).

    Args:
        args: Command arguments after 'highlight export'.
        config: Highlighting configuration to export.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message). If no file specified, message contains TOML.
    """
    import tomlkit

    file_path = parse_export_args(args)

    # Build TOML document
    doc = tomlkit.document()
    doc.add(tomlkit.comment("pgtail highlighting configuration"))
    doc.add(tomlkit.comment("Export generated by: highlight export"))
    doc.add(tomlkit.nl())

    # Add highlighting section
    hl_table = tomlkit.table()
    hl_table["enabled"] = config.enabled
    hl_table["max_length"] = config.max_length

    # Duration thresholds
    duration_table = tomlkit.table()
    duration_table["slow"] = config.duration_slow
    duration_table["very_slow"] = config.duration_very_slow
    duration_table["critical"] = config.duration_critical
    hl_table["duration"] = duration_table

    # Enabled highlighters (only include disabled ones to keep export clean)
    disabled_hl: dict[str, bool] = {}
    for name in BUILTIN_HIGHLIGHTER_NAMES:
        if name in config.enabled_highlighters and not config.enabled_highlighters[name]:
            disabled_hl[name] = False

    if disabled_hl:
        eh_table = tomlkit.table()
        for name, value in sorted(disabled_hl.items()):
            eh_table[name] = value
        hl_table["enabled_highlighters"] = eh_table

    # Custom highlighters
    if config.custom_highlighters:
        custom_array = tomlkit.array()
        custom_array.multiline(True)
        for custom in config.custom_highlighters:
            custom_table = tomlkit.inline_table()
            custom_table["name"] = custom.name
            custom_table["pattern"] = custom.pattern
            custom_table["style"] = custom.style
            custom_table["priority"] = custom.priority
            if not custom.enabled:
                custom_table["enabled"] = False
            custom_array.append(custom_table)
        hl_table["custom"] = custom_array

    doc["highlighting"] = hl_table

    toml_str = tomlkit.dumps(doc)

    if file_path:
        # Write to file
        from pathlib import Path

        path = Path(file_path).expanduser().resolve()

        try:
            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(toml_str)
            return True, f"Exported highlighting config to {path}"
        except OSError as e:
            return False, f"Failed to write to {path}: {e}"
    else:
        # Return TOML as the message (for stdout display)
        return True, toml_str


def parse_import_args(args: list[str]) -> str | None:
    """Parse arguments for 'highlight import' command.

    Expected format: <path>

    Args:
        args: Arguments after 'highlight import'.

    Returns:
        File path or None if missing.
    """
    if args:
        return args[0]
    return None


def validate_imported_config(
    data: dict[str, object],
) -> tuple[bool, str | None, list[str]]:
    """Validate an imported highlighting configuration.

    Checks:
    1. Required structure (highlighting section)
    2. Highlighter names are valid (built-in or existing custom)
    3. Custom patterns are valid regex
    4. Numeric values are reasonable

    Args:
        data: Parsed TOML data.

    Returns:
        Tuple of (is_valid, error_message, warnings).
        If valid, error_message is None.
    """
    from pgtail_py.highlighter import validate_custom_pattern

    warnings: list[str] = []

    # Check for highlighting section
    if "highlighting" not in data:
        return False, "Missing [highlighting] section", []

    hl_data = data["highlighting"]
    if not isinstance(hl_data, dict):
        return False, "[highlighting] section must be a table", []

    # Validate enabled_highlighters
    if "enabled_highlighters" in hl_data:
        eh_data = hl_data["enabled_highlighters"]
        if not isinstance(eh_data, dict):
            return False, "[highlighting.enabled_highlighters] must be a table", warnings

        for name in eh_data:
            if name not in BUILTIN_HIGHLIGHTER_NAMES:
                # Check for close match
                close_matches = get_close_matches(
                    str(name), BUILTIN_HIGHLIGHTER_NAMES, n=1, cutoff=0.6
                )
                if close_matches:
                    warnings.append(
                        f"Unknown highlighter '{name}'. Did you mean '{close_matches[0]}'?"
                    )
                else:
                    warnings.append(f"Unknown highlighter '{name}' - will be ignored")

    # Validate duration thresholds
    if "duration" in hl_data:
        dur_data = hl_data["duration"]
        if isinstance(dur_data, dict):
            for key in ("slow", "very_slow", "critical"):
                if key in dur_data:
                    value = dur_data[key]
                    if not isinstance(value, int) or value < 0:
                        return (
                            False,
                            f"Duration threshold '{key}' must be a non-negative integer",
                            warnings,
                        )
                    if value > 3600000:  # 1 hour in ms
                        warnings.append(
                            f"Duration threshold '{key}' ({value}ms) is very high"
                        )

    # Validate custom highlighters
    if "custom" in hl_data:
        custom_list = hl_data["custom"]
        if not isinstance(custom_list, list):
            return False, "[highlighting.custom] must be an array", warnings

        for i, custom_data in enumerate(custom_list):
            if not isinstance(custom_data, dict):
                return False, f"Custom highlighter {i} must be a table", warnings

            # Required fields
            if "name" not in custom_data:
                return False, f"Custom highlighter {i} missing 'name'", warnings
            if "pattern" not in custom_data:
                return (
                    False,
                    f"Custom highlighter '{custom_data.get('name', i)}' missing 'pattern'",
                    warnings,
                )

            name = str(custom_data["name"])
            pattern = str(custom_data["pattern"])

            # Validate name format
            import re

            if not re.match(r"^[a-z][a-z0-9_]*$", name):
                return (
                    False,
                    f"Custom highlighter name '{name}' must be lowercase alphanumeric with underscores",
                    warnings,
                )

            # Validate pattern
            pattern_valid, pattern_error = validate_custom_pattern(pattern)
            if not pattern_valid:
                return (
                    False,
                    f"Custom highlighter '{name}' has invalid pattern: {pattern_error}",
                    warnings,
                )

            # Check for conflict with built-in names
            if name in BUILTIN_HIGHLIGHTER_NAMES:
                return (
                    False,
                    f"Custom highlighter name '{name}' conflicts with built-in highlighter",
                    warnings,
                )

    return True, None, warnings


def handle_highlight_import(
    args: list[str],
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Handle 'highlight import <path>' command.

    Imports highlighting configuration from a TOML file.
    Validates the configuration before applying.

    Args:
        args: Command arguments after 'highlight import'.
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    import tomlkit
    from pathlib import Path
    from tomlkit.exceptions import TOMLKitError

    from pgtail_py.highlighting_config import HighlightingConfig

    file_path = parse_import_args(args)

    if not file_path:
        return False, "Usage: highlight import <path>"

    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        return False, f"File not found: {path}"

    if not path.is_file():
        return False, f"Not a file: {path}"

    # Read and parse TOML
    try:
        content = path.read_text()
    except OSError as e:
        return False, f"Failed to read {path}: {e}"

    try:
        data = tomlkit.parse(content)
    except TOMLKitError as e:
        return False, f"Invalid TOML: {e}"

    # Validate the imported configuration
    is_valid, error, warnings = validate_imported_config(dict(data))
    if not is_valid:
        return False, f"Invalid configuration: {error}"

    # Report warnings
    if warnings and warn_func:
        for warning in warnings:
            warn_func(f"Warning: {warning}")

    # Extract and apply configuration
    if "highlighting" not in data:
        return False, "Missing [highlighting] section"

    hl_data = dict(data["highlighting"])

    # Apply global settings
    if "enabled" in hl_data:
        config.enabled = bool(hl_data["enabled"])
    if "max_length" in hl_data:
        config.max_length = int(hl_data["max_length"])

    # Apply duration thresholds
    if "duration" in hl_data:
        dur_data = dict(hl_data["duration"])
        if "slow" in dur_data:
            config.duration_slow = int(dur_data["slow"])
        if "very_slow" in dur_data:
            config.duration_very_slow = int(dur_data["very_slow"])
        if "critical" in dur_data:
            config.duration_critical = int(dur_data["critical"])

    # Apply enabled_highlighters
    if "enabled_highlighters" in hl_data:
        eh_data = dict(hl_data["enabled_highlighters"])
        for name, value in eh_data.items():
            if name in BUILTIN_HIGHLIGHTER_NAMES:
                config.enabled_highlighters[str(name)] = bool(value)

    # Apply custom highlighters (replace existing)
    if "custom" in hl_data:
        config.custom_highlighters.clear()
        for custom_data in hl_data["custom"]:
            custom_dict = dict(custom_data)
            custom = CustomHighlighter.from_dict(custom_dict)
            # Only add if it doesn't conflict
            if custom.name not in BUILTIN_HIGHLIGHTER_NAMES:
                config.custom_highlighters.append(custom)

    # Persist the updated configuration
    save_highlighting_config(config, warn_func)

    # Build success message
    msg_parts = [f"Imported highlighting config from {path}"]
    if warnings:
        msg_parts.append(f" ({len(warnings)} warning(s))")

    return True, "".join(msg_parts)


# =============================================================================
# Highlight Preview Command (T144-T147)
# =============================================================================

# Sample log lines organized by highlighter category
# Each sample is a tuple of (highlighter_names, sample_line, description)
# The highlighter_names list shows which highlighters will match this line
PREVIEW_SAMPLES: list[tuple[list[str], str, str]] = [
    # Structural (timestamp, pid, context)
    (
        ["timestamp", "pid"],
        "2024-01-15 14:30:45.123 UTC [12345] LOG:  database system is ready",
        "Timestamp with timezone and process ID",
    ),
    (
        ["context"],
        "DETAIL:  Key (id)=(42) already exists.",
        "Context label (DETAIL:)",
    ),
    (
        ["context"],
        "HINT:  Use UPSERT to handle duplicates.",
        "Context label (HINT:)",
    ),
    # Diagnostic (sqlstate, error_name)
    (
        ["sqlstate"],
        'ERROR:  23505: duplicate key value violates unique constraint "users_pkey"',
        "SQLSTATE error code",
    ),
    (
        ["error_name"],
        "ERROR:  unique_violation: duplicate key value",
        "Error name (unique_violation)",
    ),
    # Performance (duration, memory, statistics)
    (
        ["duration"],
        "LOG:  duration: 45.123 ms  statement: SELECT * FROM users",
        "Fast query duration",
    ),
    (
        ["duration"],
        "LOG:  duration: 150.456 ms  statement: SELECT * FROM orders",
        "Slow query duration",
    ),
    (
        ["duration"],
        "LOG:  duration: 5500.789 ms  statement: SELECT * FROM large_table",
        "Critical query duration",
    ),
    (
        ["memory"],
        "LOG:  temporary file: 15 MB used for sort",
        "Memory/size value",
    ),
    (
        ["statistics"],
        "LOG:  checkpoint complete: wrote 1500 buffers (9.2%)",
        "Checkpoint statistics with percentage",
    ),
    # Objects (identifier, relation, schema)
    (
        ["identifier"],
        'ERROR:  column "user_name" does not exist',
        "Double-quoted identifier",
    ),
    (
        ["relation"],
        'ERROR:  relation "orders" does not exist',
        "Relation name",
    ),
    (
        ["schema"],
        "LOG:  autovacuum: analyzing public.users",
        "Schema-qualified name",
    ),
    # WAL (lsn, wal_segment, txid)
    (
        ["lsn"],
        "LOG:  redo starts at 0/1234ABCD",
        "Log sequence number (LSN)",
    ),
    (
        ["wal_segment"],
        "LOG:  archived transaction log file 000000010000000100000023",
        "WAL segment filename (24-char hex)",
    ),
    (
        ["txid"],
        "DETAIL:  xmin: 1234567, xmax: 1234570",
        "Transaction ID",
    ),
    # Connection (connection, ip, backend)
    (
        ["connection", "ip"],
        "LOG:  connection authorized: user=postgres database=mydb host=192.168.1.100 port=5432",
        "Connection info with IP address",
    ),
    (
        ["ip"],
        "LOG:  connection from 2001:db8::1 rejected",
        "IPv6 address",
    ),
    (
        ["backend"],
        "LOG:  autovacuum launcher started",
        "Backend process type",
    ),
    # SQL (sql_keyword, sql_string, sql_number, sql_param, sql_operator)
    (
        ["sql_keyword", "sql_string", "sql_number"],
        "LOG:  statement: SELECT id, 'hello' FROM users WHERE id = 42",
        "SQL keywords, strings, and numbers",
    ),
    (
        ["sql_param"],
        "LOG:  execute <unnamed>: SELECT * FROM users WHERE id = $1",
        "SQL parameter placeholder",
    ),
    (
        ["sql_operator"],
        "LOG:  statement: SELECT name || ' ' || email FROM users",
        "SQL operator (||)",
    ),
    # Lock (lock_type, lock_wait)
    (
        ["lock_type"],
        "LOG:  process 12345 acquired ShareLock on relation 16384",
        "Lock type name (ShareLock)",
    ),
    (
        ["lock_wait"],
        "LOG:  process 12345 still waiting for ExclusiveLock after 5000.123 ms",
        "Lock wait information",
    ),
    # Checkpoint (checkpoint, recovery)
    (
        ["checkpoint"],
        "LOG:  checkpoint starting: time",
        "Checkpoint message",
    ),
    (
        ["recovery"],
        "LOG:  redo done at 0/1234ABCD",
        "Recovery message",
    ),
    # Misc (boolean, null, oid, path)
    (
        ["boolean"],
        "LOG:  setting log_connections to on",
        "Boolean value (on)",
    ),
    (
        ["null"],
        "LOG:  parameter value is NULL",
        "NULL keyword",
    ),
    (
        ["oid"],
        "LOG:  dropping objects with OID 16384",
        "Object ID (OID)",
    ),
    (
        ["path"],
        "LOG:  redirecting log output to /var/log/postgresql/postgresql-17-main.log",
        "File path",
    ),
]


def get_preview_samples() -> list[tuple[list[str], str, str]]:
    """Return the list of preview samples.

    Returns:
        List of (highlighter_names, sample_line, description) tuples.
    """
    return PREVIEW_SAMPLES


def format_preview_rich(
    config: HighlightingConfig,
    theme: Theme | None = None,
) -> str:
    """Format preview output with highlighted samples for Rich/Textual.

    Args:
        config: Current highlighting configuration.
        theme: Current theme for style lookups. If None, uses default dark theme.

    Returns:
        Rich markup string for display.
    """
    from pgtail_py.tail_rich import get_highlighter_chain
    from pgtail_py.theme import ThemeManager

    # Get theme if not provided
    if theme is None:
        theme_manager = ThemeManager()
        theme = theme_manager.current_theme

    lines: list[str] = []

    # Header
    global_status = "enabled" if config.enabled else "disabled"
    global_color = "green" if config.enabled else "red"
    lines.append(f"[bold cyan]Highlight Preview[/] ([{global_color}]{global_status}[/])")
    lines.append("")

    if not config.enabled:
        lines.append("[dim]Highlighting is disabled. Run 'highlight on' to enable.[/]")
        lines.append("")

    # Get the highlighter chain (ensures highlighters are registered)
    chain = get_highlighter_chain(config)

    # Track which highlighters are disabled
    disabled_highlighters: set[str] = set()
    for name in BUILTIN_HIGHLIGHTER_NAMES:
        if not config.is_highlighter_enabled(name):
            disabled_highlighters.add(name)

    # Group samples by category
    categories: dict[str, list[tuple[list[str], str, str]]] = {
        "Structural": [],
        "Diagnostic": [],
        "Performance": [],
        "Objects": [],
        "WAL": [],
        "Connection": [],
        "SQL": [],
        "Lock": [],
        "Checkpoint": [],
        "Misc": [],
    }

    # Organize samples by category
    for highlighter_names, sample, desc in PREVIEW_SAMPLES:
        # Determine category from first highlighter name
        first_name = highlighter_names[0]
        category_map = {
            "timestamp": "Structural",
            "pid": "Structural",
            "context": "Structural",
            "sqlstate": "Diagnostic",
            "error_name": "Diagnostic",
            "duration": "Performance",
            "memory": "Performance",
            "statistics": "Performance",
            "identifier": "Objects",
            "relation": "Objects",
            "schema": "Objects",
            "lsn": "WAL",
            "wal_segment": "WAL",
            "txid": "WAL",
            "connection": "Connection",
            "ip": "Connection",
            "backend": "Connection",
            "sql_keyword": "SQL",
            "sql_string": "SQL",
            "sql_number": "SQL",
            "sql_param": "SQL",
            "sql_operator": "SQL",
            "lock_type": "Lock",
            "lock_wait": "Lock",
            "checkpoint": "Checkpoint",
            "recovery": "Checkpoint",
            "boolean": "Misc",
            "null": "Misc",
            "oid": "Misc",
            "path": "Misc",
        }
        category = category_map.get(first_name, "Misc")
        categories[category].append((highlighter_names, sample, desc))

    # Display samples by category
    category_order = [
        "Structural",
        "Diagnostic",
        "Performance",
        "Objects",
        "WAL",
        "Connection",
        "SQL",
        "Lock",
        "Checkpoint",
        "Misc",
    ]

    for category in category_order:
        samples = categories.get(category, [])
        if not samples:
            continue

        lines.append(f"[bold]{category}[/]")

        for highlighter_names, sample, desc in samples:
            # Check if any of the relevant highlighters are disabled
            disabled_for_sample = [
                name for name in highlighter_names if name in disabled_highlighters
            ]

            # Apply highlighting if enabled globally
            if config.enabled:
                highlighted = chain.apply_rich(sample, theme)
            else:
                # Escape brackets for display but no highlighting
                highlighted = sample.replace("[", "\\[")

            # Show the sample with description
            lines.append(f"  [dim]{desc}[/]")
            if disabled_for_sample:
                disabled_list = ", ".join(disabled_for_sample)
                lines.append(f"  [yellow]⚠ Disabled:[/] [dim]{disabled_list}[/]")
            lines.append(f"  {highlighted}")
            lines.append("")

    # Show disabled highlighters summary
    if disabled_highlighters:
        lines.append("[bold yellow]Disabled Highlighters[/]")
        for name in sorted(disabled_highlighters):
            lines.append(f"  [dim]• {name}[/]")
        lines.append("")
        lines.append(
            "[dim]Use 'highlight enable <name>' to enable disabled highlighters.[/]"
        )

    # Show custom highlighters
    if config.custom_highlighters:
        lines.append("")
        lines.append("[bold]Custom Highlighters[/]")
        for custom in config.custom_highlighters:
            status = "enabled" if custom.enabled else "disabled"
            status_color = "green" if custom.enabled else "red"
            pattern = custom.pattern.replace("[", "\\[")
            lines.append(
                f"  [{status_color}]{custom.name}[/]: {pattern} "
                f"[dim](style: {custom.style})[/]"
            )

    return "\n".join(lines)


def format_preview_text(
    config: HighlightingConfig,
    theme: Theme | None = None,
) -> FormattedText:
    """Format preview output with highlighted samples for prompt_toolkit.

    Args:
        config: Current highlighting configuration.
        theme: Current theme for style lookups. If None, uses default dark theme.

    Returns:
        FormattedText for REPL display.
    """
    from pgtail_py.tail_rich import get_highlighter_chain
    from pgtail_py.theme import ThemeManager

    # Get theme if not provided
    if theme is None:
        theme_manager = ThemeManager()
        theme = theme_manager.current_theme

    result: list[tuple[str, str]] = []

    # Header
    global_status = "enabled" if config.enabled else "disabled"
    global_style = "class:success" if config.enabled else "class:error"
    result.append(("class:bold", "Highlight Preview "))
    result.append(("", "("))
    result.append((global_style, global_status))
    result.append(("", ")\n\n"))

    if not config.enabled:
        result.append(
            ("class:dim", "Highlighting is disabled. Run 'highlight on' to enable.\n\n")
        )

    # Get the highlighter chain (ensures highlighters are registered)
    chain = get_highlighter_chain(config)

    # Track which highlighters are disabled
    disabled_highlighters: set[str] = set()
    for name in BUILTIN_HIGHLIGHTER_NAMES:
        if not config.is_highlighter_enabled(name):
            disabled_highlighters.add(name)

    # Group samples by category (same as Rich version)
    categories: dict[str, list[tuple[list[str], str, str]]] = {
        "Structural": [],
        "Diagnostic": [],
        "Performance": [],
        "Objects": [],
        "WAL": [],
        "Connection": [],
        "SQL": [],
        "Lock": [],
        "Checkpoint": [],
        "Misc": [],
    }

    # Organize samples by category
    for highlighter_names, sample, desc in PREVIEW_SAMPLES:
        first_name = highlighter_names[0]
        category_map = {
            "timestamp": "Structural",
            "pid": "Structural",
            "context": "Structural",
            "sqlstate": "Diagnostic",
            "error_name": "Diagnostic",
            "duration": "Performance",
            "memory": "Performance",
            "statistics": "Performance",
            "identifier": "Objects",
            "relation": "Objects",
            "schema": "Objects",
            "lsn": "WAL",
            "wal_segment": "WAL",
            "txid": "WAL",
            "connection": "Connection",
            "ip": "Connection",
            "backend": "Connection",
            "sql_keyword": "SQL",
            "sql_string": "SQL",
            "sql_number": "SQL",
            "sql_param": "SQL",
            "sql_operator": "SQL",
            "lock_type": "Lock",
            "lock_wait": "Lock",
            "checkpoint": "Checkpoint",
            "recovery": "Checkpoint",
            "boolean": "Misc",
            "null": "Misc",
            "oid": "Misc",
            "path": "Misc",
        }
        category = category_map.get(first_name, "Misc")
        categories[category].append((highlighter_names, sample, desc))

    # Display samples by category
    category_order = [
        "Structural",
        "Diagnostic",
        "Performance",
        "Objects",
        "WAL",
        "Connection",
        "SQL",
        "Lock",
        "Checkpoint",
        "Misc",
    ]

    for category in category_order:
        samples = categories.get(category, [])
        if not samples:
            continue

        result.append(("class:bold", f"{category}\n"))

        for highlighter_names, sample, desc in samples:
            disabled_for_sample = [
                name for name in highlighter_names if name in disabled_highlighters
            ]

            # Apply highlighting if enabled globally
            if config.enabled:
                highlighted = chain.apply(sample, theme)
                # highlighted is FormattedText - add description first
                result.append(("class:dim", f"  {desc}\n"))
                if disabled_for_sample:
                    disabled_list = ", ".join(disabled_for_sample)
                    result.append(("class:warning", f"  ⚠ Disabled: "))
                    result.append(("class:dim", f"{disabled_list}\n"))
                result.append(("", "  "))
                # Append the FormattedText tuples
                for style, text in highlighted:
                    result.append((style, text))
                result.append(("", "\n\n"))
            else:
                result.append(("class:dim", f"  {desc}\n"))
                if disabled_for_sample:
                    disabled_list = ", ".join(disabled_for_sample)
                    result.append(("class:warning", f"  ⚠ Disabled: "))
                    result.append(("class:dim", f"{disabled_list}\n"))
                result.append(("", f"  {sample}\n\n"))

    # Show disabled highlighters summary
    if disabled_highlighters:
        result.append(("class:warning", "Disabled Highlighters\n"))
        for name in sorted(disabled_highlighters):
            result.append(("class:dim", f"  • {name}\n"))
        result.append(("", "\n"))
        result.append(
            ("class:dim", "Use 'highlight enable <name>' to enable disabled highlighters.\n")
        )

    # Show custom highlighters
    if config.custom_highlighters:
        result.append(("", "\n"))
        result.append(("class:bold", "Custom Highlighters\n"))
        for custom in config.custom_highlighters:
            status_style = "class:success" if custom.enabled else "class:error"
            result.append((status_style, f"  {custom.name}"))
            result.append(("", ": "))
            result.append(("", custom.pattern))
            result.append(("class:dim", f" (style: {custom.style})\n"))

    return FormattedText(result)


def handle_highlight_preview(
    config: HighlightingConfig,
    theme: Theme | None = None,
    use_rich: bool = False,
) -> tuple[bool, str | FormattedText]:
    """Handle 'highlight preview' command.

    Shows sample log lines with current highlighting settings applied.
    Indicates which highlighters are disabled.

    Args:
        config: Current highlighting configuration.
        theme: Current theme for style lookups. If None, uses default theme.
        use_rich: If True, return Rich markup string; if False, return FormattedText.

    Returns:
        Tuple of (success, formatted_output).
    """
    if use_rich:
        return True, format_preview_rich(config, theme)
    else:
        return True, format_preview_text(config, theme)


# =============================================================================
# Command Dispatcher
# =============================================================================


def handle_highlight_on(
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Enable all highlighting globally.

    Args:
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    if config.enabled:
        return True, "Highlighting is already enabled."

    config.enabled = True
    save_highlighting_config(config, warn_func)
    return True, "Highlighting enabled."


def handle_highlight_off(
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Disable all highlighting globally.

    Args:
        config: Highlighting configuration to modify.
        warn_func: Optional function to call with warning messages.

    Returns:
        Tuple of (success, message).
    """
    if not config.enabled:
        return True, "Highlighting is already disabled."

    config.enabled = False
    save_highlighting_config(config, warn_func)
    return True, "Highlighting disabled."


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
        # No subcommand - show list (status display)
        return True, format_highlight_list(config)

    subcommand = args[0].lower()

    if subcommand == "list":
        return True, format_highlight_list(config)

    elif subcommand == "on":
        return handle_highlight_on(config)

    elif subcommand == "off":
        return handle_highlight_off(config)

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

    elif subcommand == "add":
        # highlight add <name> <pattern> [--style <style>]
        return handle_highlight_add(args[1:], config)

    elif subcommand == "remove":
        if len(args) < 2:
            return False, "Usage: highlight remove <name>"
        name = args[1]
        return handle_highlight_remove(name, config)

    elif subcommand == "export":
        return handle_highlight_export(args[1:], config)

    elif subcommand == "import":
        return handle_highlight_import(args[1:], config)

    elif subcommand == "preview":
        return handle_highlight_preview(config, use_rich=False)

    else:
        # Unknown subcommand
        return False, (
            f"Unknown subcommand '{subcommand}'. Available: "
            "list, on, off, enable, disable, add, remove, export, import, preview."
        )
