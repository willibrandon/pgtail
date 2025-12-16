"""Configuration and platform-specific paths."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

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

    levels: list[str] = field(default_factory=list)  # Empty = all levels
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
    quiet_hours: str | None = None


@dataclass
class ConfigSchema:
    """Complete configuration schema with all sections."""

    default: DefaultSection = field(default_factory=DefaultSection)
    slow: SlowSection = field(default_factory=SlowSection)
    display: DisplaySection = field(default_factory=DisplaySection)
    theme: ThemeSection = field(default_factory=ThemeSection)
    notifications: NotificationsSection = field(default_factory=NotificationsSection)


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
    result = []
    for item in value:
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


def validate_theme(value: Any) -> str:
    """Validate theme name."""
    if isinstance(value, str) and value in ("dark", "light"):
        return value
    raise ValueError("must be 'dark' or 'light'")


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
    "notifications.quiet_hours": (None, validate_quiet_hours, "str"),
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
# https://github.com/user/pgtail#configuration

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
# name = "dark"  # Options: dark, light

[notifications]
# enabled = false                # Enable desktop notifications
# levels = ["FATAL", "PANIC"]    # Levels that trigger notifications
# quiet_hours = "22:00-08:00"    # Suppress notifications during these hours
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
    section_name, attr_name = parts[0], parts[1]

    section = getattr(config, section_name)
    setattr(section, attr_name, value)


def save_config(key: str, value: Any, warn_func: Callable[[str], None] | None = None) -> bool:
    """Save a configuration value, preserving comments.

    Args:
        key: Dotted key path (e.g., "slow.warn")
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
    section_name = parts[0]

    if section_name not in doc:
        doc[section_name] = tomlkit.table()

    section = doc[section_name]
    attr_name = parts[1]
    section[attr_name] = value

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))
        return True
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot save config: {e}")
        return False


def delete_config_key(key: str, warn_func: Callable[[str], None] | None = None) -> bool:
    """Delete a configuration key from the file.

    Args:
        key: Dotted key path to delete
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
    section_name, attr_name = parts[0], parts[1]

    if section_name not in doc:
        return False

    section = doc[section_name]
    if attr_name not in section:
        return False

    del section[attr_name]

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))
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

    _, validator, type_hint = SETTINGS_SCHEMA[key]

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
