"""Configuration and platform-specific paths."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import tomlkit
from tomlkit.exceptions import TOMLKitError

APP_NAME = "pgtail"


# =============================================================================
# Platform-specific paths
# =============================================================================


def get_history_path() -> Path:
    """Return the platform-appropriate path for command history.

    Returns:
        - Linux: ~/.local/share/pgtail/history (XDG_DATA_HOME)
        - macOS: ~/Library/Application Support/pgtail/history
        - Windows: %APPDATA%/pgtail/history
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux and other Unix-like systems
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"

    return base / APP_NAME / "history"


def ensure_history_dir() -> Path:
    """Ensure the history directory exists and return the history file path."""
    history_path = get_history_path()
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return history_path


def get_config_path() -> Path:
    """Return the platform-appropriate path for configuration file.

    Returns:
        - Linux: ~/.config/pgtail/config.toml (XDG_CONFIG_HOME)
        - macOS: ~/Library/Application Support/pgtail/config.toml
        - Windows: %APPDATA%/pgtail/config.toml
    """
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
    else:
        # Linux and other Unix-like systems - use XDG_CONFIG_HOME
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            base = Path(xdg_config)
        else:
            base = Path.home() / ".config"

    return base / APP_NAME / "config.toml"


# =============================================================================
# Configuration schema dataclasses
# =============================================================================


@dataclass
class DefaultSection:
    """Default behavior settings."""

    levels: list[str] = field(default_factory=lambda: [])  # Empty = all levels
    follow: bool = True


@dataclass
class SlowSection:
    """Slow query threshold settings."""

    warn: int = 100
    error: int = 500
    critical: int = 1000


@dataclass
class DisplaySection:
    """Output formatting settings."""

    timestamp_format: str = "%H:%M:%S.%f"
    show_pid: bool = True
    show_level: bool = True


@dataclass
class ThemeSection:
    """Color theme settings."""

    name: str = "dark"


@dataclass
class NotificationsSection:
    """Desktop notification settings."""

    enabled: bool = False
    levels: list[str] = field(default_factory=lambda: ["FATAL", "PANIC"])
    patterns: list[str] = field(default_factory=lambda: [])
    error_rate: int | None = None  # Errors per minute threshold
    slow_query_ms: int | None = None  # Slow query threshold in ms
    quiet_hours: str | None = None


@dataclass
class BufferSection:
    """Buffer size limit settings."""

    tailer_max: int = 10000  # LogTailer entry buffer
    error_stats_max: int = 10000  # ErrorStats event buffer
    connection_stats_max: int = 10000  # ConnectionStats event buffer
    tail_log_max: int = 10000  # TailLog line buffer


@dataclass
class UpdatesSection:
    """Update checking settings."""

    check: bool = True  # Enable startup update check
    last_check: str = ""  # ISO 8601 timestamp of last check
    last_version: str = ""  # Latest version seen at last check


@dataclass
class HighlightingSection:
    """Semantic highlighting settings."""

    enabled: bool = True  # Global toggle
    max_length: int = 10240  # Depth limit in bytes


@dataclass
class HighlightingDurationSection:
    """Duration threshold settings for highlighting."""

    slow: int = 100  # Slow query threshold (ms)
    very_slow: int = 500  # Very slow query threshold (ms)
    critical: int = 5000  # Critical query threshold (ms)


@dataclass
class HighlightingEnabledHighlightersSection:
    """Per-highlighter enable/disable settings.

    All 29 highlighters default to True (enabled).
    """

    # Structural (100-199)
    timestamp: bool = True
    pid: bool = True
    context: bool = True
    # Diagnostic (200-299)
    sqlstate: bool = True
    error_name: bool = True
    # Performance (300-399)
    duration: bool = True
    memory: bool = True
    statistics: bool = True
    # Objects (400-499)
    identifier: bool = True
    relation: bool = True
    schema: bool = True
    # WAL (500-599)
    lsn: bool = True
    wal_segment: bool = True
    txid: bool = True
    # Connection (600-699)
    connection: bool = True
    ip: bool = True
    backend: bool = True
    # SQL (700-799)
    sql_keyword: bool = True
    sql_string: bool = True
    sql_number: bool = True
    sql_param: bool = True
    sql_operator: bool = True
    # Lock (800-899)
    lock_type: bool = True
    lock_wait: bool = True
    # Checkpoint (900-999)
    checkpoint: bool = True
    recovery: bool = True
    # Misc (1000+)
    boolean: bool = True
    null: bool = True
    oid: bool = True
    path: bool = True


@dataclass
class ConfigSchema:
    """Complete configuration schema with all sections."""

    default: DefaultSection = field(default_factory=DefaultSection)
    slow: SlowSection = field(default_factory=SlowSection)
    display: DisplaySection = field(default_factory=DisplaySection)
    theme: ThemeSection = field(default_factory=ThemeSection)
    notifications: NotificationsSection = field(default_factory=NotificationsSection)
    buffer: BufferSection = field(default_factory=BufferSection)
    updates: UpdatesSection = field(default_factory=UpdatesSection)
    highlighting: HighlightingSection = field(default_factory=HighlightingSection)
    highlighting_duration: HighlightingDurationSection = field(
        default_factory=HighlightingDurationSection
    )
    highlighting_enabled: HighlightingEnabledHighlightersSection = field(
        default_factory=HighlightingEnabledHighlightersSection
    )


# =============================================================================
# Validation helpers
# =============================================================================


# Valid log level names for validation
VALID_LOG_LEVELS = {
    "DEBUG",
    "DEBUG1",
    "DEBUG2",
    "DEBUG3",
    "DEBUG4",
    "DEBUG5",
    "LOG",
    "INFO",
    "NOTICE",
    "WARNING",
    "ERROR",
    "FATAL",
    "PANIC",
}


def validate_log_levels(value: Any) -> list[str]:
    """Validate log level list."""
    if not isinstance(value, list):
        raise ValueError("must be a list of log levels")
    result: list[str] = []
    for item in cast(list[Any], value):
        if not isinstance(item, str):
            raise ValueError(f"invalid log level: {item}")
        level = item.upper()
        if level not in VALID_LOG_LEVELS:
            valid = ", ".join(sorted(VALID_LOG_LEVELS))
            raise ValueError(f"invalid log level: {item}. Valid: {valid}")
        result.append(level)
    return result


def validate_bool(value: Any) -> bool:
    """Validate boolean value."""
    if isinstance(value, bool):
        return value
    raise ValueError("must be true or false")


def validate_positive_int(value: Any) -> int:
    """Validate positive integer."""
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    raise ValueError("must be a positive integer")


def validate_string(value: Any) -> str:
    """Validate string value."""
    if isinstance(value, str):
        return value
    raise ValueError("must be a string")


VALID_THEME_NAMES = {
    "dark",
    "light",
    "high-contrast",
    "monokai",
    "solarized-dark",
    "solarized-light",
}


def validate_theme(value: Any) -> str:
    """Validate theme name.

    Accepts built-in theme names or any string (for custom themes).
    """
    # Accept built-in themes or custom theme names (alphanumeric with hyphens)
    if isinstance(value, str) and (
        value in VALID_THEME_NAMES or value.replace("-", "").replace("_", "").isalnum()
    ):
        return value
    valid_list = ", ".join(sorted(VALID_THEME_NAMES))
    raise ValueError(f"must be a valid theme name. Built-in: {valid_list}")


def validate_strftime(value: Any) -> str:
    """Validate strftime format string."""
    if not isinstance(value, str):
        raise ValueError("must be a strftime format string")
    # Try to use the format to validate it
    try:
        datetime.now().strftime(value)
    except ValueError as e:
        raise ValueError(f"invalid strftime format: {e}") from None
    return value


def validate_quiet_hours(value: Any) -> str | None:
    """Validate quiet hours format (HH:MM-HH:MM)."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("must be a time range like '22:00-08:00'")
    import re

    if not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", value):
        raise ValueError("must be in format 'HH:MM-HH:MM'")
    return value


def validate_patterns(value: Any) -> list[str]:
    """Validate notification patterns list."""
    if not isinstance(value, list):
        raise ValueError("must be a list of regex patterns")
    result: list[str] = []
    import re as re_module

    for item in cast(list[Any], value):
        if not isinstance(item, str):
            raise ValueError(f"invalid pattern: {item}")
        # Extract pattern from /pattern/ or /pattern/i syntax
        pattern_str = item
        if pattern_str.startswith("/"):
            # Strip leading / and trailing /[i]
            if pattern_str.endswith("/i"):
                pattern_str = pattern_str[1:-2]
            elif pattern_str.endswith("/"):
                pattern_str = pattern_str[1:-1]
        # Validate regex compiles
        try:
            re_module.compile(pattern_str)
        except re_module.error as e:
            raise ValueError(f"invalid regex pattern '{item}': {e}") from None
        result.append(item)
    return result


def validate_optional_positive_int(value: Any) -> int | None:
    """Validate optional positive integer."""
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    raise ValueError("must be a positive integer or null")


def validate_iso8601(value: Any) -> str:
    """Validate ISO 8601 datetime string.

    Accepts empty string or valid ISO 8601 datetime.
    """
    if not isinstance(value, str):
        raise ValueError("must be an ISO 8601 datetime string")
    if value == "":
        return ""
    try:
        # Normalize Z suffix to +00:00 for fromisoformat
        normalized = value.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
    except ValueError as e:
        raise ValueError(f"invalid ISO 8601 datetime: {e}") from None
    return value


def validate_semver(value: Any) -> str:
    """Validate semantic version string.

    Accepts empty string or valid semver (e.g., "0.1.0", "1.0.0-beta.1").
    """
    import re

    if not isinstance(value, str):
        raise ValueError("must be a semver string")
    if value == "":
        return ""
    # Basic semver pattern
    pattern = r"^\d+\.\d+\.\d+(-[\w.]+)?$"
    if not re.match(pattern, value):
        raise ValueError("must be a valid semver string (e.g., 0.1.0)")
    return value


# Settings schema: maps dotted key to (default_value, validator, type_hint)
SettingDef = tuple[Any, Callable[[Any], Any], str]

SETTINGS_SCHEMA: dict[str, SettingDef] = {
    "default.levels": ([], validate_log_levels, "list"),
    "default.follow": (True, validate_bool, "bool"),
    "slow.warn": (100, validate_positive_int, "int"),
    "slow.error": (500, validate_positive_int, "int"),
    "slow.critical": (1000, validate_positive_int, "int"),
    "display.timestamp_format": ("%H:%M:%S.%f", validate_strftime, "str"),
    "display.show_pid": (True, validate_bool, "bool"),
    "display.show_level": (True, validate_bool, "bool"),
    "theme.name": ("dark", validate_theme, "str"),
    "notifications.enabled": (False, validate_bool, "bool"),
    "notifications.levels": (["FATAL", "PANIC"], validate_log_levels, "list"),
    "notifications.patterns": ([], validate_patterns, "list"),
    "notifications.error_rate": (None, validate_optional_positive_int, "int"),
    "notifications.slow_query_ms": (None, validate_optional_positive_int, "int"),
    "notifications.quiet_hours": (None, validate_quiet_hours, "str"),
    "buffer.tailer_max": (10000, validate_positive_int, "int"),
    "buffer.error_stats_max": (10000, validate_positive_int, "int"),
    "buffer.connection_stats_max": (10000, validate_positive_int, "int"),
    "buffer.tail_log_max": (10000, validate_positive_int, "int"),
    "updates.check": (True, validate_bool, "bool"),
    "updates.last_check": ("", validate_iso8601, "str"),
    "updates.last_version": ("", validate_semver, "str"),
    # Highlighting settings
    "highlighting.enabled": (True, validate_bool, "bool"),
    "highlighting.max_length": (10240, validate_positive_int, "int"),
    "highlighting.duration.slow": (100, validate_positive_int, "int"),
    "highlighting.duration.very_slow": (500, validate_positive_int, "int"),
    "highlighting.duration.critical": (5000, validate_positive_int, "int"),
    # Per-highlighter settings (29 highlighters)
    "highlighting.enabled_highlighters.timestamp": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.pid": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.context": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sqlstate": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.error_name": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.duration": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.memory": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.statistics": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.identifier": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.relation": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.schema": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.lsn": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.wal_segment": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.txid": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.connection": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.ip": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.backend": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sql_keyword": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sql_string": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sql_number": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sql_param": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.sql_operator": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.lock_type": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.lock_wait": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.checkpoint": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.recovery": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.boolean": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.null": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.oid": (True, validate_bool, "bool"),
    "highlighting.enabled_highlighters.path": (True, validate_bool, "bool"),
}

SETTING_KEYS = list(SETTINGS_SCHEMA.keys())


# =============================================================================
# Dotted key path helpers
# =============================================================================


def get_nested(data: dict[str, Any], key: str) -> Any | None:
    """Get value from nested dict using dotted key path.

    Args:
        data: Nested dictionary
        key: Dotted key path (e.g., "slow.warn")

    Returns:
        Value at key path, or None if not found
    """
    parts = key.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def set_nested(data: dict[str, Any], key: str, value: Any) -> None:
    """Set value in nested dict using dotted key path.

    Creates intermediate dicts as needed.

    Args:
        data: Nested dictionary to modify
        key: Dotted key path (e.g., "slow.warn")
        value: Value to set
    """
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def delete_nested(data: dict[str, Any], key: str) -> bool:
    """Delete value from nested dict using dotted key path.

    Args:
        data: Nested dictionary to modify
        key: Dotted key path (e.g., "slow.warn")

    Returns:
        True if key was deleted, False if not found
    """
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    if parts[-1] in current:
        del current[parts[-1]]
        return True
    return False


# =============================================================================
# Default config template
# =============================================================================


DEFAULT_CONFIG_TEMPLATE = """\
# pgtail configuration file
# https://github.com/willibrandon/pgtail#configuration

[default]
# levels = ["ERROR", "WARNING", "FATAL"]  # Filter to specific log levels (empty = all)
# follow = true                            # Auto-follow new log entries

[slow]
# warn = 100      # Yellow highlight threshold (ms)
# error = 500     # Orange highlight threshold (ms)
# critical = 1000 # Red highlight threshold (ms)

[display]
# timestamp_format = "%H:%M:%S.%f"  # strftime format for timestamps
# show_pid = true                    # Show process ID in output
# show_level = true                  # Show log level in output

[theme]
# name = "dark"  # Options: dark, light, high-contrast, monokai, solarized-dark, solarized-light

[notifications]
# enabled = false                # Enable desktop notifications
# levels = ["FATAL", "PANIC"]    # Levels that trigger notifications
# patterns = ["/deadlock detected/"]  # Regex patterns that trigger notifications
# error_rate = 10                # Alert when errors/min exceeds this threshold
# slow_query_ms = 500            # Alert when query duration exceeds this (ms)
# quiet_hours = "22:00-08:00"    # Suppress notifications during these hours

[buffer]
# tailer_max = 10000           # Max entries in log tailer buffer
# error_stats_max = 10000      # Max events in error statistics
# connection_stats_max = 10000 # Max events in connection statistics
# tail_log_max = 10000         # Max lines in tail mode display

[updates]
# check = true                 # Enable startup update check (set to false to disable)
# last_check = ""              # Timestamp of last update check (managed automatically)
# last_version = ""            # Latest version seen (managed automatically)

[highlighting]
# enabled = true              # Enable semantic highlighting (global toggle)
# max_length = 10240          # Stop highlighting after this many bytes (depth limit)

[highlighting.duration]
# slow = 100                  # Slow query threshold (ms) - yellow
# very_slow = 500             # Very slow query threshold (ms) - orange
# critical = 5000             # Critical query threshold (ms) - red

[highlighting.enabled_highlighters]
# Toggle individual highlighters (all default to true)
# timestamp = true            # Timestamps with date, time, ms, timezone
# pid = true                  # Process IDs in brackets
# context = true              # DETAIL:, HINT:, CONTEXT: labels
# sqlstate = true             # SQLSTATE error codes
# error_name = true           # Error names (unique_violation, deadlock_detected)
# duration = true             # Query durations with threshold coloring
# memory = true               # Memory values (kB, MB, GB)
# statistics = true           # Checkpoint/vacuum statistics
# identifier = true           # Double-quoted identifiers
# relation = true             # Table/index names
# schema = true               # Schema-qualified names
# lsn = true                  # Log sequence numbers
# wal_segment = true          # WAL segment filenames
# txid = true                 # Transaction IDs
# connection = true           # Connection info (host, port, user)
# ip = true                   # IP addresses
# backend = true              # Backend process types
# sql_keyword = true          # SQL keywords
# sql_string = true           # SQL strings
# sql_number = true           # SQL numbers
# sql_param = true            # SQL parameters ($1, $2)
# sql_operator = true         # SQL operators
# lock_type = true            # Lock type names
# lock_wait = true            # Lock wait info
# checkpoint = true           # Checkpoint messages
# recovery = true             # Recovery messages
# boolean = true              # Boolean values
# null = true                 # NULL keyword
# oid = true                  # Object IDs
# path = true                 # File paths

# [[highlighting.custom]]
# name = "request_id"         # Custom highlighter name
# pattern = "REQ-[0-9]{10}"   # Regex pattern
# style = "yellow"            # Color to apply
# priority = 1050             # Processing order (higher = later)
"""


# =============================================================================
# Configuration loading and saving
# =============================================================================


def load_config(warn_func: Callable[[str], None] | None = None) -> ConfigSchema:
    """Load configuration from TOML file with graceful degradation.

    If config file doesn't exist or contains errors, returns defaults.
    Invalid individual values are skipped with warnings.

    Args:
        warn_func: Optional function to call with warning messages

    Returns:
        ConfigSchema with loaded or default values
    """
    config_path = get_config_path()

    if not config_path.exists():
        return ConfigSchema()

    try:
        content = config_path.read_text()
        doc = tomlkit.parse(content)
    except (OSError, TOMLKitError) as e:
        if warn_func:
            warn_func(f"Config parse error: {e}. Using defaults.")
        return ConfigSchema()

    # Build config from validated values
    config = ConfigSchema()

    for key, (_default, validator, _) in SETTINGS_SCHEMA.items():
        raw_value = get_nested(dict(doc), key)
        if raw_value is not None:
            try:
                validated = validator(raw_value)
                _apply_to_config(config, key, validated)
            except ValueError as e:
                if warn_func:
                    warn_func(f"Invalid value for {key}: {e}. Using default.")

    # Validate slow threshold ordering
    if config.slow.warn >= config.slow.error:
        if warn_func:
            warn_func(
                f"slow.error ({config.slow.error}) must be greater than "
                f"slow.warn ({config.slow.warn}). Using defaults."
            )
        config.slow = SlowSection()
    elif config.slow.error >= config.slow.critical:
        if warn_func:
            warn_func(
                f"slow.critical ({config.slow.critical}) must be greater than "
                f"slow.error ({config.slow.error}). Using defaults."
            )
        config.slow = SlowSection()

    return config


def _apply_to_config(config: ConfigSchema, key: str, value: Any) -> None:
    """Apply a validated value to the config object."""
    parts = key.split(".")

    # Handle nested highlighting settings (3+ levels)
    if parts[0] == "highlighting" and len(parts) >= 3:
        if parts[1] == "duration":
            # highlighting.duration.slow -> highlighting_duration.slow
            setattr(config.highlighting_duration, parts[2], value)
        elif parts[1] == "enabled_highlighters":
            # highlighting.enabled_highlighters.timestamp -> highlighting_enabled.timestamp
            setattr(config.highlighting_enabled, parts[2], value)
        return

    # Standard 2-level nesting
    section_name, attr_name = parts[0], parts[1]
    section = getattr(config, section_name)
    setattr(section, attr_name, value)


def save_config(key: str, value: Any, warn_func: Callable[[str], None] | None = None) -> bool:
    """Save a configuration value, preserving comments.

    Args:
        key: Dotted key path (e.g., "slow.warn" or "highlighting.duration.slow")
        value: Value to save
        warn_func: Optional function to call with warning messages

    Returns:
        True if saved successfully, False otherwise
    """
    config_path = get_config_path()

    # Load existing document or create new one
    if config_path.exists():
        try:
            content = config_path.read_text()
            doc = tomlkit.parse(content)
        except (OSError, TOMLKitError):
            doc = tomlkit.document()
    else:
        doc = tomlkit.document()

    # Ensure parent directories exist
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot create config directory: {e}")
        return False

    # Set the value using tomlkit to preserve formatting
    parts = key.split(".")

    if len(parts) == 2:
        # Standard 2-level keys (e.g., slow.warn)
        section_name = parts[0]
        if section_name not in doc:
            doc[section_name] = tomlkit.table()
        section = cast(dict[str, Any], doc[section_name])
        section[parts[1]] = value
    elif len(parts) == 3:
        # 3-level keys (e.g., highlighting.duration.slow)
        section_name = parts[0]
        if section_name not in doc:
            doc[section_name] = tomlkit.table()
        section = cast(dict[str, Any], doc[section_name])
        subsection_name = parts[1]
        if subsection_name not in section:
            section[subsection_name] = tomlkit.table()
        subsection = cast(dict[str, Any], section[subsection_name])
        subsection[parts[2]] = value

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))  # type: ignore[arg-type]
        return True
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot save config: {e}")
        return False


def delete_config_key(key: str, warn_func: Callable[[str], None] | None = None) -> bool:
    """Delete a configuration key from the file.

    Args:
        key: Dotted key path to delete (e.g., "slow.warn" or "highlighting.duration.slow")
        warn_func: Optional function to call with warning messages

    Returns:
        True if deleted successfully, False if not found or error
    """
    config_path = get_config_path()

    if not config_path.exists():
        return False

    try:
        content = config_path.read_text()
        doc = tomlkit.parse(content)
    except (OSError, TOMLKitError):
        return False

    parts = key.split(".")

    if len(parts) == 2:
        # Standard 2-level keys (e.g., slow.warn)
        section_name, attr_name = parts[0], parts[1]
        if section_name not in doc:
            return False
        section = cast(dict[str, Any], doc[section_name])
        if attr_name not in section:
            return False
        del section[attr_name]
    elif len(parts) == 3:
        # 3-level keys (e.g., highlighting.duration.slow)
        section_name, subsection_name, attr_name = parts[0], parts[1], parts[2]
        if section_name not in doc:
            return False
        section = cast(dict[str, Any], doc[section_name])
        if subsection_name not in section:
            return False
        subsection = cast(dict[str, Any], section[subsection_name])
        if attr_name not in subsection:
            return False
        del subsection[attr_name]
    else:
        return False

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))  # type: ignore[arg-type]
        return True
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot save config: {e}")
        return False


def reset_config(warn_func: Callable[[str], None] | None = None) -> str | None:
    """Reset configuration to defaults, creating a backup.

    Args:
        warn_func: Optional function to call with warning messages

    Returns:
        Backup file path if created, None if no config existed
    """
    config_path = get_config_path()

    if not config_path.exists():
        return None

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_suffix(f".toml.bak.{timestamp}")

    try:
        backup_path.write_text(config_path.read_text())
        config_path.unlink()
        return str(backup_path)
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot reset config: {e}")
        return None


def create_default_config() -> bool:
    """Create config file with default template.

    Returns:
        True if created successfully, False otherwise
    """
    config_path = get_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(DEFAULT_CONFIG_TEMPLATE)
        return True
    except OSError:
        return False


def parse_value(key: str, raw: str | list[str]) -> Any:
    """Parse command-line value to correct type for a config key.

    Args:
        key: Config key to determine type
        raw: Raw value(s) from command line

    Returns:
        Parsed value of correct type

    Raises:
        ValueError: If key unknown or value invalid
    """
    if key not in SETTINGS_SCHEMA:
        raise ValueError(f"Unknown setting: {key}")

    _, _validator, type_hint = SETTINGS_SCHEMA[key]

    if type_hint == "bool":
        if isinstance(raw, list):
            raw = raw[0] if raw else "true"
        return raw.lower() in ("true", "1", "yes")

    elif type_hint == "int":
        if isinstance(raw, list):
            raw = raw[0] if raw else "0"
        try:
            return int(raw)
        except ValueError:
            raise ValueError("must be an integer") from None

    elif type_hint == "list":
        if isinstance(raw, str):
            raw = [raw]
        # For log levels, uppercase them
        if "levels" in key:
            return [item.upper() for item in raw]
        return list(raw)

    else:  # str
        if isinstance(raw, list):
            raw = " ".join(raw) if raw else ""
        return raw


def get_default_value(key: str) -> Any:
    """Get the default value for a config key.

    Args:
        key: Config key

    Returns:
        Default value

    Raises:
        ValueError: If key unknown
    """
    if key not in SETTINGS_SCHEMA:
        raise ValueError(f"Unknown setting: {key}")
    return SETTINGS_SCHEMA[key][0]


def validate_key(key: str) -> bool:
    """Check if a key is valid.

    Args:
        key: Config key to check

    Returns:
        True if valid, False otherwise
    """
    return key in SETTINGS_SCHEMA
