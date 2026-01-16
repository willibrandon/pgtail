"""Runtime configuration for semantic highlighting.

Provides:
- HighlightingConfig: Runtime state for highlighting settings
- Enable/disable individual highlighters
- Duration threshold configuration
- Custom highlighter management
- Serialization to/from dict for TOML persistence
- Persistence to/from config.toml
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import tomlkit
from tomlkit.exceptions import TOMLKitError

# =============================================================================
# Default Highlighter Names
# =============================================================================

# All 29 built-in highlighter names (from data-model.md)
BUILTIN_HIGHLIGHTER_NAMES = [
    # Structural (100-199)
    "timestamp",
    "pid",
    "context",
    # Diagnostic (200-299)
    "sqlstate",
    "error_name",
    # Performance (300-399)
    "duration",
    "memory",
    "statistics",
    # Objects (400-499)
    "identifier",
    "relation",
    "schema",
    # WAL (500-599)
    "lsn",
    "wal_segment",
    "txid",
    # Connection (600-699)
    "connection",
    "ip",
    "backend",
    # SQL (700-799)
    "sql_keyword",
    "sql_string",
    "sql_number",
    "sql_param",
    "sql_operator",
    # Lock (800-899)
    "lock_type",
    "lock_wait",
    # Checkpoint (900-999)
    "checkpoint",
    "recovery",
    # Misc (1000+)
    "boolean",
    "null",
    "oid",
    "path",
]


# =============================================================================
# CustomHighlighter Dataclass
# =============================================================================


@dataclass
class CustomHighlighter:
    """User-defined regex-based highlighter.

    Attributes:
        name: Unique identifier (must not conflict with built-in names).
        pattern: Regex pattern.
        style: Style to apply (color name or theme key).
        priority: Processing priority (default 1050, after built-ins).
        enabled: Whether this highlighter is active.
    """

    name: str
    pattern: str
    style: str = "yellow"
    priority: int = 1050
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for TOML export.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "pattern": self.pattern,
            "style": self.style,
            "priority": self.priority,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CustomHighlighter:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with custom highlighter fields.

        Returns:
            CustomHighlighter instance.

        Raises:
            ValueError: If required fields are missing.
        """
        if "name" not in data:
            raise ValueError("Custom highlighter missing 'name'")
        if "pattern" not in data:
            raise ValueError("Custom highlighter missing 'pattern'")

        return cls(
            name=str(data["name"]),
            pattern=str(data["pattern"]),
            style=str(data.get("style", "yellow")),
            priority=int(data.get("priority", 1050)),
            enabled=bool(data.get("enabled", True)),
        )


# =============================================================================
# HighlightingConfig
# =============================================================================


@dataclass
class HighlightingConfig:
    """Runtime configuration state for highlighting.

    Manages global enabled state, per-highlighter toggles,
    duration thresholds, and custom highlighters.
    """

    # Global settings
    enabled: bool = True
    max_length: int = 10240

    # Duration thresholds (milliseconds)
    duration_slow: int = 100
    duration_very_slow: int = 500
    duration_critical: int = 5000

    # Per-highlighter enabled state
    enabled_highlighters: dict[str, bool] = field(default_factory=dict)

    # Custom highlighters
    custom_highlighters: list[CustomHighlighter] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Initialize default enabled states for all highlighters."""
        # Set all built-in highlighters to enabled by default
        for name in BUILTIN_HIGHLIGHTER_NAMES:
            if name not in self.enabled_highlighters:
                self.enabled_highlighters[name] = True

    def is_highlighter_enabled(self, name: str) -> bool:
        """Check if a specific highlighter is enabled.

        Args:
            name: Highlighter name.

        Returns:
            True if enabled, False if disabled.
        """
        # Global toggle takes precedence
        if not self.enabled:
            return False
        return self.enabled_highlighters.get(name, True)

    def enable_highlighter(self, name: str) -> None:
        """Enable a specific highlighter.

        Args:
            name: Highlighter name.
        """
        self.enabled_highlighters[name] = True

    def disable_highlighter(self, name: str) -> None:
        """Disable a specific highlighter.

        Args:
            name: Highlighter name.
        """
        self.enabled_highlighters[name] = False

    def get_duration_severity(self, ms: float) -> str:
        """Get severity level for a duration value.

        Args:
            ms: Duration in milliseconds.

        Returns:
            Severity level: "fast", "slow", "very_slow", or "critical".
        """
        if ms >= self.duration_critical:
            return "critical"
        if ms >= self.duration_very_slow:
            return "very_slow"
        if ms >= self.duration_slow:
            return "slow"
        return "fast"

    def add_custom(self, config: CustomHighlighter) -> None:
        """Add a custom highlighter.

        Args:
            config: Custom highlighter configuration.

        Raises:
            ValueError: If name conflicts with built-in or existing custom.
        """
        # Check for conflict with built-in names
        if config.name in BUILTIN_HIGHLIGHTER_NAMES:
            raise ValueError(
                f"Cannot use name '{config.name}': conflicts with built-in highlighter"
            )

        # Check for conflict with existing custom highlighters
        for existing in self.custom_highlighters:
            if existing.name == config.name:
                raise ValueError(f"Custom highlighter '{config.name}' already exists")

        self.custom_highlighters.append(config)

    def remove_custom(self, name: str) -> bool:
        """Remove a custom highlighter.

        Args:
            name: Custom highlighter name.

        Returns:
            True if removed, False if not found.
        """
        for i, custom in enumerate(self.custom_highlighters):
            if custom.name == name:
                del self.custom_highlighters[i]
                return True
        return False

    def get_custom(self, name: str) -> CustomHighlighter | None:
        """Get a custom highlighter by name.

        Args:
            name: Custom highlighter name.

        Returns:
            CustomHighlighter if found, None otherwise.
        """
        for custom in self.custom_highlighters:
            if custom.name == name:
                return custom
        return None

    def reset(self) -> None:
        """Reset all settings to defaults.

        Clears custom highlighters, resets thresholds,
        and enables all built-in highlighters.
        """
        self.enabled = True
        self.max_length = 10240
        self.duration_slow = 100
        self.duration_very_slow = 500
        self.duration_critical = 5000
        self.enabled_highlighters.clear()
        self.custom_highlighters.clear()

        # Re-enable all built-in highlighters
        for name in BUILTIN_HIGHLIGHTER_NAMES:
            self.enabled_highlighters[name] = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for TOML export.

        Returns:
            Dictionary representation suitable for TOML.
        """
        # Build enabled_highlighters dict (only include non-default values)
        enabled_hl: dict[str, bool] = {}
        for name in BUILTIN_HIGHLIGHTER_NAMES:
            # Only include if explicitly disabled
            if name in self.enabled_highlighters and not self.enabled_highlighters[name]:
                enabled_hl[name] = False

        result: dict[str, Any] = {
            "enabled": self.enabled,
            "max_length": self.max_length,
            "duration": {
                "slow": self.duration_slow,
                "very_slow": self.duration_very_slow,
                "critical": self.duration_critical,
            },
        }

        if enabled_hl:
            result["enabled_highlighters"] = enabled_hl

        if self.custom_highlighters:
            result["custom"] = [c.to_dict() for c in self.custom_highlighters]

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HighlightingConfig:
        """Deserialize from dictionary.

        Args:
            data: Dictionary with highlighting config fields.

        Returns:
            HighlightingConfig instance.
        """
        config = cls()

        # Global settings
        if "enabled" in data:
            config.enabled = bool(data["enabled"])
        if "max_length" in data:
            config.max_length = int(data["max_length"])

        # Duration thresholds
        duration = data.get("duration", {})
        if "slow" in duration:
            config.duration_slow = int(duration["slow"])
        if "very_slow" in duration:
            config.duration_very_slow = int(duration["very_slow"])
        if "critical" in duration:
            config.duration_critical = int(duration["critical"])

        # Per-highlighter toggles
        enabled_hl = data.get("enabled_highlighters", {})
        for name, value in enabled_hl.items():
            config.enabled_highlighters[str(name)] = bool(value)

        # Custom highlighters
        custom_list = data.get("custom", [])
        for custom_data in custom_list:
            try:
                custom = CustomHighlighter.from_dict(custom_data)
                config.custom_highlighters.append(custom)
            except (ValueError, TypeError):
                # Skip invalid custom highlighters
                pass

        return config


# =============================================================================
# Persistence Functions
# =============================================================================


def get_config_path() -> Path:
    """Get the config file path.

    Returns:
        Path to config.toml file.
    """
    from pgtail_py.config import get_config_path as _get_config_path

    return _get_config_path()


def load_highlighting_config(
    warn_func: Callable[[str], None] | None = None,
) -> HighlightingConfig:
    """Load highlighting configuration from config.toml.

    If config file doesn't exist or contains errors, returns defaults.

    Args:
        warn_func: Optional function to call with warning messages.

    Returns:
        HighlightingConfig with loaded or default values.
    """
    config_path = get_config_path()

    if not config_path.exists():
        return HighlightingConfig()

    try:
        content = config_path.read_text()
        doc = tomlkit.parse(content)
    except (OSError, TOMLKitError) as e:
        if warn_func:
            warn_func(f"Config parse error: {e}. Using highlighting defaults.")
        return HighlightingConfig()

    # Extract highlighting section
    highlighting_data: dict[str, Any] = {}

    if "highlighting" in doc:
        hl_section = dict(doc["highlighting"])
        highlighting_data["enabled"] = hl_section.get("enabled", True)
        highlighting_data["max_length"] = hl_section.get("max_length", 10240)

        # Duration subsection
        if "duration" in hl_section:
            highlighting_data["duration"] = dict(hl_section["duration"])

        # Enabled highlighters subsection
        if "enabled_highlighters" in hl_section:
            highlighting_data["enabled_highlighters"] = dict(hl_section["enabled_highlighters"])

        # Custom highlighters array
        if "custom" in hl_section:
            highlighting_data["custom"] = list(hl_section["custom"])

    return HighlightingConfig.from_dict(highlighting_data)


def save_highlighting_config(
    config: HighlightingConfig,
    warn_func: Callable[[str], None] | None = None,
) -> bool:
    """Save highlighting configuration to config.toml.

    Preserves other settings in the config file.

    Args:
        config: Highlighting configuration to save.
        warn_func: Optional function to call with warning messages.

    Returns:
        True if saved successfully, False otherwise.
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

    # Create or update highlighting section
    if "highlighting" not in doc:
        doc["highlighting"] = tomlkit.table()

    hl_section = cast(dict[str, Any], doc["highlighting"])

    # Update global settings
    hl_section["enabled"] = config.enabled
    hl_section["max_length"] = config.max_length

    # Update duration section
    if "duration" not in hl_section:
        hl_section["duration"] = tomlkit.table()
    duration_section = cast(dict[str, Any], hl_section["duration"])
    duration_section["slow"] = config.duration_slow
    duration_section["very_slow"] = config.duration_very_slow
    duration_section["critical"] = config.duration_critical

    # Update enabled_highlighters section (only store disabled ones)
    disabled_highlighters: dict[str, bool] = {}
    for name in BUILTIN_HIGHLIGHTER_NAMES:
        if name in config.enabled_highlighters and not config.enabled_highlighters[name]:
            disabled_highlighters[name] = False

    if disabled_highlighters:
        if "enabled_highlighters" not in hl_section:
            hl_section["enabled_highlighters"] = tomlkit.table()
        eh_section = cast(dict[str, Any], hl_section["enabled_highlighters"])

        # Remove all existing entries first, then add disabled ones
        for name in list(eh_section.keys()):
            del eh_section[name]
        for name, value in disabled_highlighters.items():
            eh_section[name] = value
    else:
        # No disabled highlighters - remove the section if it exists
        if "enabled_highlighters" in hl_section:
            del hl_section["enabled_highlighters"]

    # Update custom highlighters
    if config.custom_highlighters:
        custom_array = tomlkit.array()
        for custom in config.custom_highlighters:
            custom_table = tomlkit.inline_table()
            custom_table["name"] = custom.name
            custom_table["pattern"] = custom.pattern
            custom_table["style"] = custom.style
            custom_table["priority"] = custom.priority
            if not custom.enabled:
                custom_table["enabled"] = False
            custom_array.append(custom_table)
        hl_section["custom"] = custom_array
    else:
        # No custom highlighters - remove the key if it exists
        if "custom" in hl_section:
            del hl_section["custom"]

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))  # type: ignore[arg-type]
        return True
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot save config: {e}")
        return False


def save_highlighter_state(
    name: str,
    enabled: bool,
    warn_func: Callable[[str], None] | None = None,
) -> bool:
    """Save a single highlighter's enabled state to config.toml.

    This is more efficient than saving the entire config when
    only one highlighter's state has changed.

    Args:
        name: Highlighter name.
        enabled: Whether the highlighter is enabled.
        warn_func: Optional function to call with warning messages.

    Returns:
        True if saved successfully, False otherwise.
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

    # Create highlighting section if needed
    if "highlighting" not in doc:
        doc["highlighting"] = tomlkit.table()

    hl_section = cast(dict[str, Any], doc["highlighting"])

    # Create enabled_highlighters section if needed
    if "enabled_highlighters" not in hl_section:
        hl_section["enabled_highlighters"] = tomlkit.table()

    eh_section = cast(dict[str, Any], hl_section["enabled_highlighters"])

    # Update the specific highlighter
    if enabled:
        # Enabled is the default - remove from config to keep it clean
        if name in eh_section:
            del eh_section[name]
    else:
        # Store disabled state
        eh_section[name] = False

    # Clean up empty enabled_highlighters section
    if not eh_section:
        del hl_section["enabled_highlighters"]

    # Write back
    try:
        config_path.write_text(tomlkit.dumps(doc))  # type: ignore[arg-type]
        return True
    except OSError as e:
        if warn_func:
            warn_func(f"Cannot save config: {e}")
        return False
