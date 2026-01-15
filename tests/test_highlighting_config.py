"""Tests for highlighting_config.py (T033).

Tests cover:
- HighlightingConfig initialization
- is_highlighter_enabled/enable_highlighter/disable_highlighter
- get_duration_severity with thresholds
- add_custom/remove_custom for custom highlighters
- to_dict/from_dict serialization
- CustomHighlighter dataclass
"""

from __future__ import annotations

from typing import Any

import pytest

from pgtail_py.highlighting_config import (
    BUILTIN_HIGHLIGHTER_NAMES,
    CustomHighlighter,
    HighlightingConfig,
)


# =============================================================================
# Test HighlightingConfig Initialization
# =============================================================================


class TestInitialization:
    """Tests for HighlightingConfig initialization."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        config = HighlightingConfig()

        assert config.enabled is True
        assert config.max_length == 10240
        assert config.duration_slow == 100
        assert config.duration_very_slow == 500
        assert config.duration_critical == 5000
        assert len(config.custom_highlighters) == 0

    def test_builtin_highlighters_enabled_by_default(self) -> None:
        """All built-in highlighters should be enabled by default."""
        config = HighlightingConfig()

        for name in BUILTIN_HIGHLIGHTER_NAMES:
            assert config.is_highlighter_enabled(name)

    def test_custom_initialization(self) -> None:
        """Custom initialization values should be preserved."""
        config = HighlightingConfig(
            enabled=False,
            max_length=5000,
            duration_slow=50,
            duration_very_slow=200,
            duration_critical=1000,
        )

        assert config.enabled is False
        assert config.max_length == 5000
        assert config.duration_slow == 50
        assert config.duration_very_slow == 200
        assert config.duration_critical == 1000


# =============================================================================
# Test Highlighter Enable/Disable
# =============================================================================


class TestHighlighterToggle:
    """Tests for is_highlighter_enabled/enable/disable methods."""

    def test_is_highlighter_enabled_default(self) -> None:
        """Unknown highlighters should be enabled by default."""
        config = HighlightingConfig()
        assert config.is_highlighter_enabled("unknown_highlighter")

    def test_disable_highlighter(self) -> None:
        """Disabling a highlighter should make it disabled."""
        config = HighlightingConfig()
        config.disable_highlighter("timestamp")

        assert not config.is_highlighter_enabled("timestamp")

    def test_enable_highlighter(self) -> None:
        """Enabling a highlighter after disabling should work."""
        config = HighlightingConfig()
        config.disable_highlighter("timestamp")
        config.enable_highlighter("timestamp")

        assert config.is_highlighter_enabled("timestamp")

    def test_global_toggle_overrides(self) -> None:
        """Global toggle should override per-highlighter settings."""
        config = HighlightingConfig()
        config.enable_highlighter("timestamp")
        config.enabled = False

        assert not config.is_highlighter_enabled("timestamp")


# =============================================================================
# Test Duration Severity
# =============================================================================


class TestDurationSeverity:
    """Tests for get_duration_severity method."""

    def test_fast_duration(self) -> None:
        """Duration below slow threshold should be 'fast'."""
        config = HighlightingConfig()
        assert config.get_duration_severity(50) == "fast"
        assert config.get_duration_severity(99) == "fast"

    def test_slow_duration(self) -> None:
        """Duration at or above slow threshold should be 'slow'."""
        config = HighlightingConfig()
        assert config.get_duration_severity(100) == "slow"
        assert config.get_duration_severity(250) == "slow"
        assert config.get_duration_severity(499) == "slow"

    def test_very_slow_duration(self) -> None:
        """Duration at or above very_slow threshold should be 'very_slow'."""
        config = HighlightingConfig()
        assert config.get_duration_severity(500) == "very_slow"
        assert config.get_duration_severity(2500) == "very_slow"
        assert config.get_duration_severity(4999) == "very_slow"

    def test_critical_duration(self) -> None:
        """Duration at or above critical threshold should be 'critical'."""
        config = HighlightingConfig()
        assert config.get_duration_severity(5000) == "critical"
        assert config.get_duration_severity(10000) == "critical"
        assert config.get_duration_severity(1000000) == "critical"

    def test_custom_thresholds(self) -> None:
        """Custom thresholds should be respected."""
        config = HighlightingConfig(
            duration_slow=10,
            duration_very_slow=50,
            duration_critical=100,
        )

        assert config.get_duration_severity(5) == "fast"
        assert config.get_duration_severity(10) == "slow"
        assert config.get_duration_severity(50) == "very_slow"
        assert config.get_duration_severity(100) == "critical"


# =============================================================================
# Test Custom Highlighters
# =============================================================================


class TestCustomHighlighters:
    """Tests for add_custom/remove_custom/get_custom methods."""

    def test_add_custom(self) -> None:
        """Adding a custom highlighter should work."""
        config = HighlightingConfig()
        custom = CustomHighlighter(
            name="request_id",
            pattern=r"REQ-\d+",
            style="yellow",
        )
        config.add_custom(custom)

        assert len(config.custom_highlighters) == 1
        assert config.custom_highlighters[0].name == "request_id"

    def test_add_custom_builtin_conflict(self) -> None:
        """Adding custom with built-in name should raise."""
        config = HighlightingConfig()
        custom = CustomHighlighter(
            name="timestamp",  # Conflicts with built-in
            pattern=r"xxx",
            style="yellow",
        )

        with pytest.raises(ValueError, match="conflicts with built-in"):
            config.add_custom(custom)

    def test_add_custom_duplicate(self) -> None:
        """Adding duplicate custom name should raise."""
        config = HighlightingConfig()
        custom1 = CustomHighlighter(name="test", pattern=r"a", style="yellow")
        custom2 = CustomHighlighter(name="test", pattern=r"b", style="red")

        config.add_custom(custom1)

        with pytest.raises(ValueError, match="already exists"):
            config.add_custom(custom2)

    def test_remove_custom(self) -> None:
        """Removing a custom highlighter should work."""
        config = HighlightingConfig()
        custom = CustomHighlighter(name="test", pattern=r"x", style="yellow")
        config.add_custom(custom)

        result = config.remove_custom("test")
        assert result is True
        assert len(config.custom_highlighters) == 0

    def test_remove_custom_not_found(self) -> None:
        """Removing non-existent custom should return False."""
        config = HighlightingConfig()
        result = config.remove_custom("unknown")
        assert result is False

    def test_get_custom(self) -> None:
        """Getting a custom highlighter by name should work."""
        config = HighlightingConfig()
        custom = CustomHighlighter(name="test", pattern=r"x", style="yellow")
        config.add_custom(custom)

        result = config.get_custom("test")
        assert result is custom

    def test_get_custom_not_found(self) -> None:
        """Getting non-existent custom should return None."""
        config = HighlightingConfig()
        assert config.get_custom("unknown") is None


# =============================================================================
# Test Reset
# =============================================================================


class TestReset:
    """Tests for reset method."""

    def test_reset_restores_defaults(self) -> None:
        """Reset should restore all default values."""
        config = HighlightingConfig(
            enabled=False,
            max_length=100,
            duration_slow=1,
            duration_very_slow=2,
            duration_critical=3,
        )
        config.disable_highlighter("timestamp")
        config.add_custom(
            CustomHighlighter(name="test", pattern=r"x", style="yellow")
        )

        config.reset()

        assert config.enabled is True
        assert config.max_length == 10240
        assert config.duration_slow == 100
        assert config.duration_very_slow == 500
        assert config.duration_critical == 5000
        assert config.is_highlighter_enabled("timestamp")
        assert len(config.custom_highlighters) == 0


# =============================================================================
# Test Serialization
# =============================================================================


class TestSerialization:
    """Tests for to_dict/from_dict serialization."""

    def test_to_dict_defaults(self) -> None:
        """Default config should produce minimal dict."""
        config = HighlightingConfig()
        data = config.to_dict()

        assert data["enabled"] is True
        assert data["max_length"] == 10240
        assert "enabled_highlighters" not in data  # All default, not included
        assert "custom" not in data  # No custom highlighters

    def test_to_dict_with_disabled(self) -> None:
        """Disabled highlighters should appear in dict."""
        config = HighlightingConfig()
        config.disable_highlighter("timestamp")
        config.disable_highlighter("pid")

        data = config.to_dict()
        assert data["enabled_highlighters"]["timestamp"] is False
        assert data["enabled_highlighters"]["pid"] is False

    def test_to_dict_with_custom(self) -> None:
        """Custom highlighters should appear in dict."""
        config = HighlightingConfig()
        config.add_custom(
            CustomHighlighter(
                name="test",
                pattern=r"x",
                style="yellow",
                priority=1050,
                enabled=True,
            )
        )

        data = config.to_dict()
        assert len(data["custom"]) == 1
        assert data["custom"][0]["name"] == "test"
        assert data["custom"][0]["pattern"] == r"x"

    def test_from_dict_empty(self) -> None:
        """Empty dict should produce default config."""
        config = HighlightingConfig.from_dict({})

        assert config.enabled is True
        assert config.max_length == 10240

    def test_from_dict_with_values(self) -> None:
        """Dict with values should be parsed correctly."""
        data: dict[str, Any] = {
            "enabled": False,
            "max_length": 5000,
            "duration": {
                "slow": 50,
                "very_slow": 200,
                "critical": 1000,
            },
            "enabled_highlighters": {
                "timestamp": False,
            },
            "custom": [
                {
                    "name": "test",
                    "pattern": r"x",
                    "style": "yellow",
                    "priority": 1050,
                    "enabled": True,
                }
            ],
        }

        config = HighlightingConfig.from_dict(data)

        assert config.enabled is False
        assert config.max_length == 5000
        assert config.duration_slow == 50
        assert config.duration_very_slow == 200
        assert config.duration_critical == 1000
        assert not config.enabled_highlighters.get("timestamp", True)
        assert len(config.custom_highlighters) == 1
        assert config.custom_highlighters[0].name == "test"

    def test_round_trip(self) -> None:
        """Config should survive to_dict/from_dict round trip."""
        original = HighlightingConfig()
        original.enabled = False
        original.max_length = 5000
        original.duration_slow = 50
        original.disable_highlighter("timestamp")
        original.add_custom(
            CustomHighlighter(name="test", pattern=r"x", style="yellow")
        )

        data = original.to_dict()
        restored = HighlightingConfig.from_dict(data)

        assert restored.enabled == original.enabled
        assert restored.max_length == original.max_length
        assert restored.duration_slow == original.duration_slow
        assert not restored.enabled_highlighters.get("timestamp", True)
        assert len(restored.custom_highlighters) == 1


# =============================================================================
# Test CustomHighlighter Dataclass
# =============================================================================


class TestCustomHighlighter:
    """Tests for CustomHighlighter dataclass."""

    def test_default_values(self) -> None:
        """Default values should be set correctly."""
        custom = CustomHighlighter(name="test", pattern=r"x")

        assert custom.name == "test"
        assert custom.pattern == r"x"
        assert custom.style == "yellow"  # Default
        assert custom.priority == 1050  # Default
        assert custom.enabled is True  # Default

    def test_to_dict(self) -> None:
        """to_dict should return all fields."""
        custom = CustomHighlighter(
            name="test",
            pattern=r"x",
            style="red",
            priority=2000,
            enabled=False,
        )

        data = custom.to_dict()
        assert data["name"] == "test"
        assert data["pattern"] == r"x"
        assert data["style"] == "red"
        assert data["priority"] == 2000
        assert data["enabled"] is False

    def test_from_dict(self) -> None:
        """from_dict should create correct instance."""
        data: dict[str, Any] = {
            "name": "test",
            "pattern": r"x",
            "style": "blue",
            "priority": 1500,
            "enabled": False,
        }

        custom = CustomHighlighter.from_dict(data)
        assert custom.name == "test"
        assert custom.pattern == r"x"
        assert custom.style == "blue"
        assert custom.priority == 1500
        assert custom.enabled is False

    def test_from_dict_minimal(self) -> None:
        """from_dict with minimal fields should use defaults."""
        data = {"name": "test", "pattern": r"x"}

        custom = CustomHighlighter.from_dict(data)
        assert custom.name == "test"
        assert custom.pattern == r"x"
        assert custom.style == "yellow"  # Default
        assert custom.priority == 1050  # Default
        assert custom.enabled is True  # Default

    def test_from_dict_missing_name(self) -> None:
        """from_dict without name should raise."""
        with pytest.raises(ValueError, match="missing 'name'"):
            CustomHighlighter.from_dict({"pattern": r"x"})

    def test_from_dict_missing_pattern(self) -> None:
        """from_dict without pattern should raise."""
        with pytest.raises(ValueError, match="missing 'pattern'"):
            CustomHighlighter.from_dict({"name": "test"})
