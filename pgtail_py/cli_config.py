"""Configuration management commands."""

from __future__ import annotations

import contextlib
import os
import subprocess
from typing import TYPE_CHECKING

from pgtail_py.cli_utils import find_instance, warn
from pgtail_py.config import (
    SETTINGS_SCHEMA,
    ConfigSchema,
    create_default_config,
    delete_config_key,
    get_config_path,
    get_default_value,
    load_config,
    parse_value,
    reset_config,
    save_config,
    validate_key,
)
from pgtail_py.enable_logging import enable_logging
from pgtail_py.filter import LogLevel
from pgtail_py.slow_query import SlowQueryConfig

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def _get_config_value(state: AppState, key: str) -> object:
    """Get a config value by dotted key path.

    Handles both 2-level (slow.warn) and 3-level (highlighting.duration.slow) keys.

    Args:
        state: Current application state.
        key: Dotted key path.

    Returns:
        Current value from config.
    """
    parts = key.split(".")

    # Handle 3-level keys (e.g., highlighting.duration.slow)
    if len(parts) == 3 and parts[0] == "highlighting":
        if parts[1] == "duration":
            return getattr(state.config.highlighting_duration, parts[2])
        elif parts[1] == "enabled_highlighters":
            return getattr(state.config.highlighting_enabled, parts[2])

    # Standard 2-level keys
    section = getattr(state.config, parts[0])
    return getattr(section, parts[1])


def _set_config_value(state: AppState, key: str, value: object) -> None:
    """Set a config value by dotted key path.

    Handles both 2-level (slow.warn) and 3-level (highlighting.duration.slow) keys.

    Args:
        state: Current application state.
        key: Dotted key path.
        value: Value to set.
    """
    parts = key.split(".")

    # Handle 3-level keys (e.g., highlighting.duration.slow)
    if len(parts) == 3 and parts[0] == "highlighting":
        if parts[1] == "duration":
            setattr(state.config.highlighting_duration, parts[2], value)
            return
        elif parts[1] == "enabled_highlighters":
            setattr(state.config.highlighting_enabled, parts[2], value)
            return

    # Standard 2-level keys
    section = getattr(state.config, parts[0])
    setattr(section, parts[1], value)


def set_command(state: AppState, args: list[str]) -> None:
    """Handle the 'set' command - set or display a config value.

    Args:
        state: Current application state.
        args: Command arguments: [key] or [key, value...].
    """
    # No args - show usage
    if not args:
        print("Usage: set <key> [value]")
        print()
        print("Available settings:")
        for key in SETTINGS_SCHEMA:
            default = get_default_value(key)
            print(f"  {key} (default: {default!r})")
        return

    key = args[0]

    # Validate key
    if not validate_key(key):
        print(f"Unknown setting: {key}")
        print()
        print("Available settings:")
        for k in SETTINGS_SCHEMA:
            print(f"  {k}")
        return

    # No value - display current value
    if len(args) == 1:
        # Get current value from config
        current = _get_config_value(state, key)
        default = get_default_value(key)
        print(f"{key} = {current!r}")
        if current != default:
            print(f"  (default: {default!r})")
        return

    # Parse and validate value
    raw_value = args[1:]
    try:
        value = parse_value(key, raw_value if len(raw_value) > 1 else raw_value[0])
    except ValueError as e:
        print(f"Invalid value for {key}: {e}")
        return

    # Validate the value using schema validator
    _, validator, _ = SETTINGS_SCHEMA[key]
    try:
        validated = validator(value)
    except ValueError as e:
        print(f"Invalid value for {key}: {e}")
        return

    # Save to config file (creates file/dirs if needed)
    if not save_config(key, validated, warn_func=warn):
        print("Failed to save configuration")
        return

    # Update in-memory config
    _set_config_value(state, key, validated)

    # Apply changes immediately
    apply_setting(state, key)

    print(f"{key} = {validated!r}")
    print(f"Saved to {get_config_path()}")


def unset_command(state: AppState, args: list[str]) -> None:
    """Handle the 'unset' command - remove a config setting.

    Args:
        state: Current application state.
        args: Command arguments: [key].
    """
    # No args - show usage
    if not args:
        print("Usage: unset <key>")
        print()
        print("Remove a setting to revert to its default value.")
        print()
        print("Available settings:")
        for key in SETTINGS_SCHEMA:
            default = get_default_value(key)
            print(f"  {key} (default: {default!r})")
        return

    key = args[0]

    # Validate key exists in schema
    if not validate_key(key):
        print(f"Unknown setting: {key}")
        print()
        print("Available settings:")
        for k in SETTINGS_SCHEMA:
            print(f"  {k}")
        return

    # Get default value for confirmation message
    default = get_default_value(key)

    # Remove key from config file
    config_path = get_config_path()
    if config_path.exists():
        deleted = delete_config_key(key, warn_func=warn)
        if not deleted:
            print(f"{key} is not set in config file.")
            print(f"Current value is already the default: {default!r}")
            return
    else:
        print(f"{key} is not set (no config file exists).")
        print(f"Already using default: {default!r}")
        return

    # Revert in-memory value to default and apply
    _set_config_value(state, key, default)
    apply_setting(state, key)

    # Show confirmation with default value
    print(f"{key} reset to default: {default!r}")


def apply_setting(state: AppState, key: str) -> None:
    """Apply a single setting change to runtime state.

    Args:
        state: Current application state.
        key: The setting key that was changed.
    """
    if key == "default.levels":
        levels = state.config.default.levels
        if not levels:
            state.active_levels = LogLevel.all_levels()
        else:
            valid_levels: set[LogLevel] = set()
            for level_name in levels:
                with contextlib.suppress(ValueError):
                    valid_levels.add(LogLevel.from_string(level_name))
            state.active_levels = valid_levels if valid_levels else LogLevel.all_levels()
        # Update tailer if tailing
        if state.tailer:
            state.tailer.update_levels(state.active_levels)
    elif key.startswith("slow."):
        state.slow_query_config = SlowQueryConfig(
            enabled=True,
            warning_ms=state.config.slow.warn,
            slow_ms=state.config.slow.error,
            critical_ms=state.config.slow.critical,
        )
    elif key.startswith("highlighting.duration."):
        # Update highlighting config duration thresholds
        from pgtail_py.tail_rich import reset_highlighter_chain

        if key == "highlighting.duration.slow":
            state.highlighting_config.duration_slow = state.config.highlighting_duration.slow
        elif key == "highlighting.duration.very_slow":
            state.highlighting_config.duration_very_slow = (
                state.config.highlighting_duration.very_slow
            )
        elif key == "highlighting.duration.critical":
            state.highlighting_config.duration_critical = (
                state.config.highlighting_duration.critical
            )
        # Reset highlighter chain so new thresholds take effect
        reset_highlighter_chain()


def config_command(state: AppState, args: list[str]) -> None:
    """Handle the 'config' command - display or manage configuration.

    Args:
        state: Current application state.
        args: Subcommand (path, edit, reset) or empty to show config.
    """
    # Handle subcommands
    if args:
        subcommand = args[0].lower()
        if subcommand == "path":
            config_path_command()
            return
        elif subcommand == "edit":
            config_edit_command(state)
            return
        elif subcommand == "reset":
            config_reset_command(state)
            return
        else:
            print(f"Unknown subcommand: {subcommand}")
            print("Available: path, edit, reset")
            return

    # No subcommand - display current configuration
    config_path = get_config_path()
    file_exists = config_path.exists()

    # Header with file path
    if file_exists:
        print(f"# Config file: {config_path}")
    else:
        print(f"# Config file: {config_path} (not created yet)")
        print("# Showing default values")
    print()

    # Format as TOML-like output
    print("[default]")
    levels = state.config.default.levels
    print(f"levels = {levels!r}")
    print(f"follow = {str(state.config.default.follow).lower()}")
    print()

    print("[slow]")
    print(f"warn = {state.config.slow.warn}")
    print(f"error = {state.config.slow.error}")
    print(f"critical = {state.config.slow.critical}")
    print()

    print("[display]")
    print(f'timestamp_format = "{state.config.display.timestamp_format}"')
    print(f"show_pid = {str(state.config.display.show_pid).lower()}")
    print(f"show_level = {str(state.config.display.show_level).lower()}")
    print()

    print("[theme]")
    print(f'name = "{state.config.theme.name}"')
    print()

    print("[notifications]")
    print(f"enabled = {str(state.config.notifications.enabled).lower()}")
    print(f"levels = {state.config.notifications.levels!r}")
    if state.config.notifications.quiet_hours:
        print(f'quiet_hours = "{state.config.notifications.quiet_hours}"')
    else:
        print('# quiet_hours = "22:00-08:00"')


def config_path_command() -> None:
    """Handle the 'config path' command - show config file location."""
    config_path = get_config_path()
    print(config_path)
    if config_path.exists():
        print("  (file exists)")
    else:
        print("  (file not created yet - use 'set' to create)")


def config_edit_command(state: AppState) -> None:
    """Handle the 'config edit' command - open config in $EDITOR.

    Args:
        state: Current application state.
    """
    # Check $EDITOR environment variable
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL")
    if not editor:
        print("No editor configured.")
        print()
        print("Set the EDITOR environment variable:")
        print("  export EDITOR=vim")
        print("  export EDITOR=nano")
        print("  export EDITOR='code --wait'")
        print()
        print(f"Or edit directly: {get_config_path()}")
        return

    config_path = get_config_path()

    # Create config file with template if it doesn't exist
    if not config_path.exists():
        print(f"Creating config file: {config_path}")
        if not create_default_config():
            print("Error: Could not create config file")
            return

    # Open editor and wait for exit
    print(f"Opening {config_path} in {editor}...")
    try:
        # Use shell=True to handle editors with arguments like "code --wait"
        result = subprocess.run(
            f'{editor} "{config_path}"',
            shell=True,
            check=False,
        )
        if result.returncode != 0:
            print(f"Editor exited with code {result.returncode}")
    except Exception as e:
        print(f"Error launching editor: {e}")
        return

    # Reload config after editor closes
    print("Reloading configuration...")
    state.config = load_config(warn_func=warn)
    _apply_config(state)
    print("Configuration reloaded.")


def config_reset_command(state: AppState) -> None:
    """Handle the 'config reset' command - reset to defaults with backup.

    Args:
        state: Current application state.
    """
    config_path = get_config_path()

    # Check if config file exists
    if not config_path.exists():
        print("No config file to reset.")
        print(f"Config path: {config_path}")
        print()
        print("Already using default settings.")
        return

    # Create backup and delete original
    backup_path = reset_config(warn_func=warn)

    if backup_path is None:
        print("Error: Could not reset config file")
        return

    # Reset in-memory config to defaults
    state.config = ConfigSchema()
    _apply_config(state)

    # Display confirmation
    print("Configuration reset to defaults.")
    print()
    print(f"Backup saved: {backup_path}")


def _apply_config(state: AppState) -> None:
    """Apply all configuration settings to state.

    Args:
        state: Current application state.
    """
    # Apply default.levels if configured
    if state.config.default.levels:
        valid_levels: set[LogLevel] = set()
        for level_name in state.config.default.levels:
            with contextlib.suppress(ValueError):
                valid_levels.add(LogLevel.from_string(level_name))
        if valid_levels:
            state.active_levels = valid_levels

    # Apply slow.* thresholds
    state.slow_query_config = SlowQueryConfig(
        enabled=True,
        warning_ms=state.config.slow.warn,
        slow_ms=state.config.slow.error,
        critical_ms=state.config.slow.critical,
    )


def enable_logging_command(state: AppState, args: list[str]) -> None:
    """Handle the 'enable-logging' command - enable logging_collector for an instance.

    Args:
        state: Current application state.
        args: Instance ID or path.
    """
    if not args:
        print("Usage: enable-logging <id|path>")
        print()
        print("Enables logging_collector in postgresql.conf")
        print("After running, you must restart PostgreSQL for changes to take effect.")
        return

    instance = find_instance(state, args[0])
    if instance is None:
        print(f"Instance not found: {args[0]}")
        print()
        print("Available instances:")
        for inst in state.instances:
            print(f"  {inst.id}: {inst.data_dir}")
        return

    # Check if logging is already enabled
    if instance.log_path and instance.log_path.exists():
        print(f"Logging is already enabled for instance {instance.id}")
        print(f"Log file: {instance.log_path}")
        return

    print(f"Enabling logging for instance {instance.id}...")
    print(f"Data directory: {instance.data_dir}")
    print()

    result = enable_logging(instance.data_dir)

    if result.changes:
        print("Changes made:")
        for change in result.changes:
            print(f"  • {change}")
        print()

    if result.success:
        print(result.message)
        print()
        print("⚠️  PostgreSQL must be restarted for changes to take effect:")
        if instance.running:
            print(f"    pg_ctl restart -D {instance.data_dir}")
        else:
            print(f"    pg_ctl start -D {instance.data_dir}")
        print()
        print("After restarting, run 'refresh' to update instance list.")
    else:
        print(f"Error: {result.message}")
