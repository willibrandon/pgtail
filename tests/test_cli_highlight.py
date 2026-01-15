"""Tests for highlight CLI commands.

Tests cover:
- highlight list command
- highlight enable/disable commands
- Highlighter name validation with suggestions
- Configuration persistence
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from pgtail_py.cli_highlight import (
    format_highlight_list,
    format_highlight_list_rich,
    handle_highlight_enable,
    handle_highlight_disable,
    handle_highlight_command,
    validate_highlighter_name,
    get_all_highlighter_names,
)
from pgtail_py.highlighting_config import HighlightingConfig, BUILTIN_HIGHLIGHTER_NAMES


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def highlighting_config():
    """Create a fresh HighlightingConfig for testing."""
    return HighlightingConfig()


@pytest.fixture
def mock_registry():
    """Mock the highlighter registry with test highlighters."""
    with patch("pgtail_py.cli_highlight.get_registry") as mock:
        registry = MagicMock()

        # Create mock highlighters
        timestamp_hl = MagicMock()
        timestamp_hl.name = "timestamp"
        timestamp_hl.priority = 100
        timestamp_hl.description = "Timestamps with date, time, ms, tz"

        pid_hl = MagicMock()
        pid_hl.name = "pid"
        pid_hl.priority = 110
        pid_hl.description = "Process IDs in brackets"

        duration_hl = MagicMock()
        duration_hl.name = "duration"
        duration_hl.priority = 300
        duration_hl.description = "Query durations with threshold coloring"

        # Set up registry methods
        registry.all_names.return_value = ["timestamp", "pid", "duration"]
        registry.all_categories.return_value = ["structural", "performance"]
        registry.get_by_category.side_effect = lambda cat: {
            "structural": [timestamp_hl, pid_hl],
            "performance": [duration_hl],
        }.get(cat, [])
        registry.get_category.side_effect = lambda name: {
            "timestamp": "structural",
            "pid": "structural",
            "duration": "performance",
        }.get(name)

        mock.return_value = registry
        yield registry


# =============================================================================
# Test Highlighter Name Validation
# =============================================================================


class TestValidateHighlighterName:
    """Tests for highlighter name validation."""

    def test_valid_name(self, mock_registry):
        """Valid highlighter name is accepted."""
        is_valid, suggestion = validate_highlighter_name("timestamp")
        assert is_valid is True
        assert suggestion is None

    def test_invalid_name_with_suggestion(self, mock_registry):
        """Invalid name with close match provides suggestion."""
        is_valid, suggestion = validate_highlighter_name("timestam")
        assert is_valid is False
        assert suggestion == "timestamp"

    def test_invalid_name_without_suggestion(self, mock_registry):
        """Invalid name with no close match has no suggestion."""
        is_valid, suggestion = validate_highlighter_name("xyz123")
        assert is_valid is False
        assert suggestion is None


class TestGetAllHighlighterNames:
    """Tests for getting all highlighter names."""

    def test_returns_all_names(self, mock_registry):
        """Returns all highlighter names (registry + built-in)."""
        names = get_all_highlighter_names()
        # Should include all 29 built-in names plus any registry names
        assert "timestamp" in names
        assert "pid" in names
        assert "duration" in names
        # Should have at least 29 built-in highlighters
        assert len(names) >= 29


# =============================================================================
# Test Highlight List Command
# =============================================================================


class TestHighlightList:
    """Tests for highlight list command."""

    def test_format_list_shows_all_highlighters(self, mock_registry, highlighting_config):
        """List shows all registered highlighters with status."""
        result = format_highlight_list(highlighting_config)

        # Should be FormattedText
        assert hasattr(result, "__iter__")

        # Convert to string for easier testing
        text = "".join(t[1] for t in result)

        assert "Semantic Highlighting:" in text
        assert "enabled" in text
        assert "timestamp" in text
        assert "pid" in text
        assert "duration" in text

    def test_format_list_shows_disabled_highlighter(self, mock_registry, highlighting_config):
        """List shows disabled status for disabled highlighters."""
        highlighting_config.disable_highlighter("timestamp")

        result = format_highlight_list(highlighting_config)
        text = "".join(t[1] for t in result)

        assert "timestamp" in text
        # The output contains the disabled status
        assert "off" in text

    def test_format_list_rich_output(self, mock_registry, highlighting_config):
        """Rich format produces valid markup."""
        result = format_highlight_list_rich(highlighting_config)

        assert isinstance(result, str)
        assert "Semantic Highlighting:" in result
        assert "timestamp" in result
        assert "[green]" in result or "[red]" in result  # Status colors

    def test_format_list_with_global_disabled(self, mock_registry, highlighting_config):
        """List shows global disabled status."""
        highlighting_config.enabled = False

        result = format_highlight_list(highlighting_config)
        text = "".join(t[1] for t in result)

        assert "disabled" in text


# =============================================================================
# Test Highlight Enable/Disable Commands
# =============================================================================


class TestHighlightEnableDisable:
    """Tests for highlight enable/disable commands."""

    def test_enable_valid_highlighter(self, mock_registry, highlighting_config):
        """Enable command enables a valid highlighter."""
        # First disable it
        highlighting_config.disable_highlighter("timestamp")
        assert not highlighting_config.is_highlighter_enabled("timestamp")

        # Patch save to avoid actual file I/O
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("timestamp", highlighting_config)

        assert success is True
        assert "Enabled" in message
        assert "timestamp" in message
        assert highlighting_config.is_highlighter_enabled("timestamp")

    def test_disable_valid_highlighter(self, mock_registry, highlighting_config):
        """Disable command disables a valid highlighter."""
        assert highlighting_config.is_highlighter_enabled("timestamp")

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("timestamp", highlighting_config)

        assert success is True
        assert "Disabled" in message
        assert "timestamp" in message
        assert not highlighting_config.is_highlighter_enabled("timestamp")

    def test_enable_invalid_name_with_suggestion(self, mock_registry, highlighting_config):
        """Enable with typo provides suggestion."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("timestam", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "Did you mean" in message
        assert "timestamp" in message

    def test_disable_invalid_name_with_suggestion(self, mock_registry, highlighting_config):
        """Disable with typo provides suggestion."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("timestam", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "Did you mean" in message

    def test_enable_invalid_name_without_suggestion(self, mock_registry, highlighting_config):
        """Enable with completely wrong name shows error."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("xyz123", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "highlight list" in message

    def test_disable_invalid_name_without_suggestion(self, mock_registry, highlighting_config):
        """Disable with completely wrong name shows error."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("xyz123", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message


# =============================================================================
# Test Command Dispatcher
# =============================================================================


class TestHighlightCommandDispatcher:
    """Tests for highlight command dispatcher."""

    def test_no_args_shows_list(self, mock_registry, highlighting_config):
        """No arguments shows the list."""
        success, result = handle_highlight_command([], highlighting_config)

        assert success is True
        # Result should be FormattedText
        text = "".join(t[1] for t in result)
        assert "Semantic Highlighting:" in text

    def test_list_subcommand(self, mock_registry, highlighting_config):
        """'list' subcommand shows the list."""
        success, result = handle_highlight_command(["list"], highlighting_config)

        assert success is True
        text = "".join(t[1] for t in result)
        assert "Semantic Highlighting:" in text

    def test_enable_subcommand_requires_name(self, mock_registry, highlighting_config):
        """'enable' without name shows usage."""
        success, message = handle_highlight_command(["enable"], highlighting_config)

        assert success is False
        assert "Usage:" in message

    def test_disable_subcommand_requires_name(self, mock_registry, highlighting_config):
        """'disable' without name shows usage."""
        success, message = handle_highlight_command(["disable"], highlighting_config)

        assert success is False
        assert "Usage:" in message

    def test_enable_with_name(self, mock_registry, highlighting_config):
        """'enable <name>' enables the highlighter."""
        highlighting_config.disable_highlighter("timestamp")

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_command(
                ["enable", "timestamp"], highlighting_config
            )

        assert success is True
        assert "Enabled" in message

    def test_disable_with_name(self, mock_registry, highlighting_config):
        """'disable <name>' disables the highlighter."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_command(
                ["disable", "timestamp"], highlighting_config
            )

        assert success is True
        assert "Disabled" in message

    def test_unknown_subcommand(self, mock_registry, highlighting_config):
        """Unknown subcommand shows error."""
        success, message = handle_highlight_command(["foo"], highlighting_config)

        assert success is False
        assert "Unknown subcommand" in message


# =============================================================================
# Test Custom Highlighters
# =============================================================================


class TestCustomHighlighterCommands:
    """Tests for custom highlighter enable/disable."""

    def test_enable_custom_highlighter(self, mock_registry, highlighting_config):
        """Enable works for custom highlighters."""
        from pgtail_py.highlighting_config import CustomHighlighter

        custom = CustomHighlighter(
            name="my_pattern",
            pattern="TEST-\\d+",
            style="yellow",
            enabled=False,
        )
        highlighting_config.custom_highlighters.append(custom)

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("my_pattern", highlighting_config)

        assert success is True
        assert "custom highlighter" in message
        assert custom.enabled is True

    def test_disable_custom_highlighter(self, mock_registry, highlighting_config):
        """Disable works for custom highlighters."""
        from pgtail_py.highlighting_config import CustomHighlighter

        custom = CustomHighlighter(
            name="my_pattern",
            pattern="TEST-\\d+",
            style="yellow",
            enabled=True,
        )
        highlighting_config.custom_highlighters.append(custom)

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("my_pattern", highlighting_config)

        assert success is True
        assert "custom highlighter" in message
        assert custom.enabled is False


# =============================================================================
# Test Configuration Persistence
# =============================================================================


class TestConfigPersistence:
    """Tests for configuration persistence."""

    def test_save_highlighter_state_called_on_enable(self, mock_registry, highlighting_config):
        """save_highlighter_state is called when enabling."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_enable("timestamp", highlighting_config)
            mock_save.assert_called_once_with("timestamp", True, None)

    def test_save_highlighter_state_called_on_disable(self, mock_registry, highlighting_config):
        """save_highlighter_state is called when disabling."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_disable("timestamp", highlighting_config)
            mock_save.assert_called_once_with("timestamp", False, None)

    def test_warn_func_passed_to_save(self, mock_registry, highlighting_config):
        """warn_func is passed to save_highlighter_state."""
        warn_func = MagicMock()

        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_enable("timestamp", highlighting_config, warn_func)
            mock_save.assert_called_once_with("timestamp", True, warn_func)
