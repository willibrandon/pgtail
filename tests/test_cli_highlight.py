"""Tests for highlight CLI commands.

Tests cover:
- highlight list command
- highlight enable/disable commands
- Highlighter name validation with suggestions
- Configuration persistence
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from unittest.mock import patch, MagicMock

from pgtail_py.cli_highlight import (
    format_highlight_list,
    format_highlight_list_rich,
    handle_highlight_enable,
    handle_highlight_disable,
    handle_highlight_on,
    handle_highlight_off,
    handle_highlight_command,
    validate_highlighter_name,
    get_all_highlighter_names,
)
from pgtail_py.highlighting_config import HighlightingConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def highlighting_config() -> HighlightingConfig:
    """Create a fresh HighlightingConfig for testing."""
    return HighlightingConfig()


@pytest.fixture
def mock_registry() -> Generator[MagicMock, None, None]:
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
        registry.get_by_category.side_effect = lambda cat: {  # type: ignore[misc]
            "structural": [timestamp_hl, pid_hl],
            "performance": [duration_hl],
        }.get(cat, [])  # type: ignore[arg-type]
        registry.get_category.side_effect = lambda name: {  # type: ignore[misc]
            "timestamp": "structural",
            "pid": "structural",
            "duration": "performance",
        }.get(name)  # type: ignore[arg-type]

        mock.return_value = registry
        yield registry


# =============================================================================
# Test Highlighter Name Validation
# =============================================================================


class TestValidateHighlighterName:
    """Tests for highlighter name validation."""

    def test_valid_name(self, mock_registry: MagicMock) -> None:
        """Valid highlighter name is accepted."""
        is_valid, suggestion = validate_highlighter_name("timestamp")
        assert is_valid is True
        assert suggestion is None

    def test_invalid_name_with_suggestion(self, mock_registry: MagicMock) -> None:
        """Invalid name with close match provides suggestion."""
        is_valid, suggestion = validate_highlighter_name("timestam")
        assert is_valid is False
        assert suggestion == "timestamp"

    def test_invalid_name_without_suggestion(self, mock_registry: MagicMock) -> None:
        """Invalid name with no close match has no suggestion."""
        is_valid, suggestion = validate_highlighter_name("xyz123")
        assert is_valid is False
        assert suggestion is None


class TestGetAllHighlighterNames:
    """Tests for getting all highlighter names."""

    def test_returns_all_names(self, mock_registry: MagicMock) -> None:
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

    def test_format_list_shows_all_highlighters(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_format_list_shows_disabled_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """List shows disabled status for disabled highlighters."""
        highlighting_config.disable_highlighter("timestamp")

        result = format_highlight_list(highlighting_config)
        text = "".join(t[1] for t in result)

        assert "timestamp" in text
        # The output contains the disabled status
        assert "off" in text

    def test_format_list_rich_output(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Rich format produces valid markup."""
        result = format_highlight_list_rich(highlighting_config)

        assert isinstance(result, str)
        assert "Semantic Highlighting:" in result
        assert "timestamp" in result
        assert "[green]" in result or "[red]" in result  # Status colors

    def test_format_list_with_global_disabled(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_enable_valid_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_disable_valid_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Disable command disables a valid highlighter."""
        assert highlighting_config.is_highlighter_enabled("timestamp")

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("timestamp", highlighting_config)

        assert success is True
        assert "Disabled" in message
        assert "timestamp" in message
        assert not highlighting_config.is_highlighter_enabled("timestamp")

    def test_enable_invalid_name_with_suggestion(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Enable with typo provides suggestion."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("timestam", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "Did you mean" in message
        assert "timestamp" in message

    def test_disable_invalid_name_with_suggestion(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Disable with typo provides suggestion."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_disable("timestam", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "Did you mean" in message

    def test_enable_invalid_name_without_suggestion(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Enable with completely wrong name shows error."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_enable("xyz123", highlighting_config)

        assert success is False
        assert "Unknown highlighter" in message
        assert "highlight list" in message

    def test_disable_invalid_name_without_suggestion(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_no_args_shows_list(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """No arguments shows the list."""
        success, result = handle_highlight_command([], highlighting_config)

        assert success is True
        # Result should be FormattedText
        text = "".join(t[1] for t in result)
        assert "Semantic Highlighting:" in text

    def test_list_subcommand(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'list' subcommand shows the list."""
        success, result = handle_highlight_command(["list"], highlighting_config)

        assert success is True
        text = "".join(t[1] for t in result)
        assert "Semantic Highlighting:" in text

    def test_enable_subcommand_requires_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'enable' without name shows usage."""
        success, message = handle_highlight_command(["enable"], highlighting_config)

        assert success is False
        assert "Usage:" in message

    def test_disable_subcommand_requires_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'disable' without name shows usage."""
        success, message = handle_highlight_command(["disable"], highlighting_config)

        assert success is False
        assert "Usage:" in message

    def test_enable_with_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'enable <name>' enables the highlighter."""
        highlighting_config.disable_highlighter("timestamp")

        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_command(
                ["enable", "timestamp"], highlighting_config
            )

        assert success is True
        assert "Enabled" in message

    def test_disable_with_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'disable <name>' disables the highlighter."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state"):
            success, message = handle_highlight_command(
                ["disable", "timestamp"], highlighting_config
            )

        assert success is True
        assert "Disabled" in message

    def test_unknown_subcommand(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Unknown subcommand shows error."""
        success, message = handle_highlight_command(["foo"], highlighting_config)

        assert success is False
        assert "Unknown subcommand" in message


# =============================================================================
# Test Custom Highlighters
# =============================================================================


class TestCustomHighlighterCommands:
    """Tests for custom highlighter enable/disable."""

    def test_enable_custom_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_disable_custom_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
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

    def test_save_highlighter_state_called_on_enable(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """save_highlighter_state is called when enabling."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_enable("timestamp", highlighting_config)
            mock_save.assert_called_once_with("timestamp", True, None)

    def test_save_highlighter_state_called_on_disable(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """save_highlighter_state is called when disabling."""
        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_disable("timestamp", highlighting_config)
            mock_save.assert_called_once_with("timestamp", False, None)

    def test_warn_func_passed_to_save(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """warn_func is passed to save_highlighter_state."""
        warn_func = MagicMock()

        with patch("pgtail_py.cli_highlight.save_highlighter_state") as mock_save:
            handle_highlight_enable("timestamp", highlighting_config, warn_func)
            mock_save.assert_called_once_with("timestamp", True, warn_func)


# =============================================================================
# Test Highlight Add Command
# =============================================================================


class TestHighlightAddCommand:
    """Tests for highlight add command (T120)."""

    def test_add_valid_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Successfully add a custom highlighter with valid pattern."""
        from pgtail_py.cli_highlight import handle_highlight_add

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_add(
                ["request_id", r"REQ-\d+"], highlighting_config
            )

        assert success is True
        assert "Added custom highlighter 'request_id'" in message
        assert len(highlighting_config.custom_highlighters) == 1
        assert highlighting_config.custom_highlighters[0].name == "request_id"
        assert highlighting_config.custom_highlighters[0].pattern == r"REQ-\d+"

    def test_add_with_style(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Add highlighter with custom style."""
        from pgtail_py.cli_highlight import handle_highlight_add

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, _message = handle_highlight_add(
                ["mypattern", r"TEST-\d+", "--style", "bold red"], highlighting_config
            )

        assert success is True
        assert highlighting_config.custom_highlighters[0].style == "bold red"

    def test_add_requires_name_and_pattern(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Add command requires both name and pattern."""
        from pgtail_py.cli_highlight import handle_highlight_add

        success, message = handle_highlight_add([], highlighting_config)
        assert success is False
        assert "Usage:" in message

        success, message = handle_highlight_add(["name_only"], highlighting_config)
        assert success is False
        assert "Usage:" in message

    def test_add_rejects_builtin_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Cannot add highlighter with built-in name."""
        from pgtail_py.cli_highlight import handle_highlight_add

        success, message = handle_highlight_add(
            ["timestamp", r"TEST-\d+"], highlighting_config
        )

        assert success is False
        assert "conflicts with built-in" in message

    def test_add_rejects_duplicate_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Cannot add highlighter with existing custom name."""
        from pgtail_py.cli_highlight import handle_highlight_add

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            # First add
            handle_highlight_add(["mypattern", r"TEST-\d+"], highlighting_config)
            # Second add with same name
            success, message = handle_highlight_add(
                ["mypattern", r"ANOTHER-\d+"], highlighting_config
            )

        assert success is False
        assert "already exists" in message

    def test_add_rejects_invalid_name_format(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Name must be lowercase alphanumeric with underscores."""
        from pgtail_py.cli_highlight import handle_highlight_add

        # Uppercase
        success, message = handle_highlight_add(
            ["MyPattern", r"TEST-\d+"], highlighting_config
        )
        assert success is False
        assert "lowercase" in message

        # With hyphen
        success, message = handle_highlight_add(
            ["my-pattern", r"TEST-\d+"], highlighting_config
        )
        assert success is False

    def test_add_via_dispatcher(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Test add command through dispatcher."""
        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_command(
                ["add", "test_hl", r"TEST-\d+"], highlighting_config
            )

        assert success is True
        assert "Added" in message


# =============================================================================
# Test Highlight Remove Command
# =============================================================================


class TestHighlightRemoveCommand:
    """Tests for highlight remove command (T120)."""

    def test_remove_custom_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Successfully remove a custom highlighter."""
        from pgtail_py.cli_highlight import handle_highlight_add, handle_highlight_remove

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            # First add one
            handle_highlight_add(["mypattern", r"TEST-\d+"], highlighting_config)
            assert len(highlighting_config.custom_highlighters) == 1

            # Then remove it
            success, message = handle_highlight_remove("mypattern", highlighting_config)

        assert success is True
        assert "Removed" in message
        assert len(highlighting_config.custom_highlighters) == 0

    def test_remove_nonexistent_highlighter(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Remove fails for non-existent custom highlighter."""
        from pgtail_py.cli_highlight import handle_highlight_remove

        success, message = handle_highlight_remove("nonexistent", highlighting_config)

        assert success is False
        assert "not found" in message

    def test_remove_builtin_highlighter_rejected(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Cannot remove built-in highlighter."""
        from pgtail_py.cli_highlight import handle_highlight_remove

        success, message = handle_highlight_remove("timestamp", highlighting_config)

        assert success is False
        assert "Cannot remove built-in" in message
        assert "highlight disable" in message

    def test_remove_via_dispatcher(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Test remove command through dispatcher."""
        from pgtail_py.cli_highlight import handle_highlight_add

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            # First add one
            handle_highlight_add(["test_hl", r"TEST-\d+"], highlighting_config)

            # Then remove it via dispatcher
            success, message = handle_highlight_command(
                ["remove", "test_hl"], highlighting_config
            )

        assert success is True
        assert "Removed" in message

    def test_remove_requires_name(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Remove command requires name argument."""
        success, message = handle_highlight_command(["remove"], highlighting_config)

        assert success is False
        assert "Usage:" in message


# =============================================================================
# Test Invalid Regex Handling (T121)
# =============================================================================


class TestInvalidRegexHandling:
    """Tests for invalid regex pattern handling (T121)."""

    def test_add_rejects_invalid_regex(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Add rejects invalid regex pattern."""
        from pgtail_py.cli_highlight import handle_highlight_add

        success, message = handle_highlight_add(
            ["mypattern", r"[invalid"], highlighting_config
        )

        assert success is False
        assert "Invalid regex" in message

    def test_add_rejects_zero_length_match(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Add rejects pattern that matches zero-length string."""
        from pgtail_py.cli_highlight import handle_highlight_add

        success, message = handle_highlight_add(
            ["mypattern", r".*"], highlighting_config
        )

        assert success is False
        assert "zero-length" in message

    def test_add_rejects_empty_pattern(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Add rejects empty pattern."""
        from pgtail_py.cli_highlight import handle_highlight_add

        success, message = handle_highlight_add(
            ["mypattern", ""], highlighting_config
        )

        assert success is False
        assert "empty" in message.lower() or "Usage" in message

    def test_validate_custom_pattern_direct(self) -> None:
        """Test validate_custom_pattern function directly."""
        from pgtail_py.highlighter import validate_custom_pattern

        # Valid pattern
        valid, error = validate_custom_pattern(r"REQ-\d+")
        assert valid is True
        assert error is None

        # Invalid regex
        valid, error = validate_custom_pattern(r"[invalid")
        assert valid is False
        assert error is not None
        assert "Invalid regex" in error

        # Zero-length match
        valid, error = validate_custom_pattern(r".*")
        assert valid is False
        assert error is not None
        assert "zero-length" in error

        # Empty pattern
        valid, error = validate_custom_pattern("")
        assert valid is False
        assert error is not None
        assert "empty" in error.lower()

    def test_registry_skips_invalid_custom_highlighter(
        self, highlighting_config: HighlightingConfig
    ) -> None:
        """Registry create_chain skips invalid custom highlighters silently."""
        from pgtail_py.highlighter_registry import get_registry
        from pgtail_py.highlighting_config import CustomHighlighter

        registry = get_registry()

        # Add invalid custom highlighter to config
        invalid_custom = CustomHighlighter(
            name="invalid",
            pattern=r"[invalid",  # Invalid regex
            style="yellow",
        )
        highlighting_config.custom_highlighters.append(invalid_custom)

        # Should not raise, just skip the invalid highlighter
        chain = registry.create_chain(highlighting_config)
        # The invalid highlighter should be skipped
        names = [h.name for h in chain.highlighters]
        assert "invalid" not in names


# =============================================================================
# Test Highlight On/Off Commands (T127)
# =============================================================================


class TestHighlightOnOff:
    """Tests for highlight on/off (global toggle) commands."""

    def test_on_enables_highlighting(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight on' enables highlighting when disabled."""
        highlighting_config.enabled = False
        assert not highlighting_config.enabled

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_on(highlighting_config)

        assert success is True
        assert "enabled" in message.lower()
        assert highlighting_config.enabled is True

    def test_on_when_already_enabled(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight on' shows message when already enabled."""
        assert highlighting_config.enabled is True

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_on(highlighting_config)

        assert success is True
        assert "already enabled" in message.lower()

    def test_off_disables_highlighting(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight off' disables highlighting when enabled."""
        assert highlighting_config.enabled is True

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_off(highlighting_config)

        assert success is True
        assert "disabled" in message.lower()
        assert highlighting_config.enabled is False

    def test_off_when_already_disabled(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight off' shows message when already disabled."""
        highlighting_config.enabled = False

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_off(highlighting_config)

        assert success is True
        assert "already disabled" in message.lower()

    def test_on_via_dispatcher(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Test 'on' command through dispatcher."""
        highlighting_config.enabled = False

        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_command(["on"], highlighting_config)

        assert success is True
        assert highlighting_config.enabled is True

    def test_off_via_dispatcher(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Test 'off' command through dispatcher."""
        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            success, message = handle_highlight_command(["off"], highlighting_config)

        assert success is True
        assert highlighting_config.enabled is False

    def test_on_persists_to_config(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight on' persists state to config."""
        highlighting_config.enabled = False

        with patch("pgtail_py.cli_highlight.save_highlighting_config") as mock_save:
            handle_highlight_on(highlighting_config)
            mock_save.assert_called_once_with(highlighting_config, None)

    def test_off_persists_to_config(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """'highlight off' persists state to config."""
        with patch("pgtail_py.cli_highlight.save_highlighting_config") as mock_save:
            handle_highlight_off(highlighting_config)
            mock_save.assert_called_once_with(highlighting_config, None)

    def test_warn_func_passed_to_save(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """warn_func is passed to save_highlighting_config for on/off."""
        warn_func = MagicMock()
        highlighting_config.enabled = False

        with patch("pgtail_py.cli_highlight.save_highlighting_config") as mock_save:
            handle_highlight_on(highlighting_config, warn_func)
            mock_save.assert_called_once_with(highlighting_config, warn_func)

    def test_global_disabled_affects_all_highlighters(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """When global is disabled, all highlighters report as disabled."""
        # All should be enabled by default
        assert highlighting_config.is_highlighter_enabled("timestamp") is True
        assert highlighting_config.is_highlighter_enabled("pid") is True

        # Disable globally
        highlighting_config.enabled = False

        # Now all should report as disabled
        assert highlighting_config.is_highlighter_enabled("timestamp") is False
        assert highlighting_config.is_highlighter_enabled("pid") is False

    def test_global_enabled_after_off_on_cycle(
        self, mock_registry: MagicMock, highlighting_config: HighlightingConfig
    ) -> None:
        """Highlighters work after off/on cycle."""
        with patch("pgtail_py.cli_highlight.save_highlighting_config"):
            # Turn off
            handle_highlight_off(highlighting_config)
            assert not highlighting_config.is_highlighter_enabled("timestamp")

            # Turn back on
            handle_highlight_on(highlighting_config)
            assert highlighting_config.is_highlighter_enabled("timestamp")
