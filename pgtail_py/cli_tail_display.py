"""Display command handlers for tail mode.

This module provides handlers for display commands (errors, connections)
executed within the tail mode interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus


def handle_errors_command(
    args: list[str],
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'errors' command to show error summary.

    Args:
        args: Command arguments (e.g., ['--trend'])
        state: AppState instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    error_stats = state.error_stats

    total = error_stats.error_count + error_stats.warning_count
    by_level = error_stats.get_by_level()
    by_code = error_stats.get_by_code()

    if log_widget is not None:
        log_widget.write_line(
            f"[bold cyan]Error Statistics[/bold cyan]  Total: [magenta]{total}[/magenta]"
        )
        if by_level:
            log_widget.write_line("[dim]  By Level:[/dim]")
            for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True):
                color = {
                    "PANIC": "bold red",
                    "FATAL": "red",
                    "ERROR": "yellow",
                    "WARNING": "cyan",
                }.get(level.name, "white")
                log_widget.write_line(
                    f"    [{color}]{level.name}[/{color}]: [magenta]{count}[/magenta]"
                )
        if by_code:
            log_widget.write_line("[dim]  By SQLSTATE:[/dim]")
            for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:10]:
                log_widget.write_line(f"    [cyan]{code}[/cyan]: [magenta]{count}[/magenta]")
    return True


def handle_connections_command(
    args: list[str],
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'connections' command to show connection summary.

    Args:
        args: Command arguments
        state: AppState instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    conn_stats = state.connection_stats

    by_db = conn_stats.get_by_database()
    by_user = conn_stats.get_by_user()

    if log_widget is not None:
        log_widget.write_line("[bold cyan]Connection Statistics[/bold cyan]")
        log_widget.write_line(
            f"  Active: [magenta]{conn_stats.active_count()}[/magenta]  "
            f"Connects: [green]{conn_stats.connect_count}[/green]  "
            f"Disconnects: [red]{conn_stats.disconnect_count}[/red]"
        )
        if by_db:
            log_widget.write_line("[dim]  By Database:[/dim]")
            for db, count in sorted(by_db.items(), key=lambda x: x[1], reverse=True)[:5]:
                log_widget.write_line(f"    [cyan]{db}[/cyan]: [magenta]{count}[/magenta]")
        if by_user:
            log_widget.write_line("[dim]  By User:[/dim]")
            for user, count in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]:
                log_widget.write_line(f"    [cyan]{user}[/cyan]: [magenta]{count}[/magenta]")
    return True


def handle_highlight_command(
    args: list[str],
    status: TailStatus,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'highlight' command to manage semantic highlighters.

    Subcommands:
        list              Show all highlighters with status
        enable <name>     Enable a highlighter
        disable <name>    Disable a highlighter
        add <name> <pattern> [--style <style>]  Add custom highlighter
        remove <name>     Remove custom highlighter

    Args:
        args: Command arguments (e.g., ['list'], ['enable', 'timestamp'])
        status: TailStatus instance
        state: AppState instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    from pgtail_py.cli_highlight import (
        format_highlight_list_rich,
        handle_highlight_add,
        handle_highlight_disable,
        handle_highlight_enable,
        handle_highlight_export,
        handle_highlight_import,
        handle_highlight_off,
        handle_highlight_on,
        handle_highlight_remove,
    )
    from pgtail_py.cli_utils import warn

    config = state.highlighting_config

    # No args or 'list' - show highlighter list
    if not args or (args and args[0].lower() == "list"):
        if log_widget is not None:
            output = format_highlight_list_rich(config)
            for line in output.split("\n"):
                if line:  # Skip empty lines
                    log_widget.write_line(line)
        return True

    subcommand = args[0].lower()

    # Handle 'on' subcommand - enable all highlighting globally
    if subcommand == "on":
        success, message = handle_highlight_on(config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'off' subcommand - disable all highlighting globally
    if subcommand == "off":
        success, message = handle_highlight_off(config, warn)

        if log_widget is not None:
            color = "yellow" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'enable' subcommand
    if subcommand == "enable":
        if len(args) < 2:
            msg = "Usage: highlight enable <name>"
            if log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_enable(name, config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'disable' subcommand
    if subcommand == "disable":
        if len(args) < 2:
            msg = "Usage: highlight disable <name>"
            if log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_disable(name, config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'add' subcommand
    if subcommand == "add":
        success, message = handle_highlight_add(args[1:], config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'remove' subcommand
    if subcommand == "remove":
        if len(args) < 2:
            msg = "Usage: highlight remove <name>"
            if log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_remove(name, config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'export' subcommand
    if subcommand == "export":
        success, message = handle_highlight_export(args[1:], config, warn)

        if log_widget is not None:
            if success:
                # Check if message is TOML (stdout) or confirmation (file)
                if message.startswith("#") or message.startswith("["):
                    # TOML output - show in dim
                    for line in message.split("\n"):
                        log_widget.write_line(f"[dim]{line}[/dim]")
                else:
                    # File export confirmation - show in green
                    log_widget.write_line(f"[green]{message}[/green]")
            else:
                log_widget.write_line(f"[red]{message}[/red]")
        return True

    # Handle 'import' subcommand
    if subcommand == "import":
        success, message = handle_highlight_import(args[1:], config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'preview' subcommand
    if subcommand == "preview":
        from pgtail_py.cli_highlight import handle_highlight_preview

        if log_widget is not None:
            success, output = handle_highlight_preview(config, use_rich=True)
            # output is a Rich markup string
            for line in str(output).split("\n"):
                log_widget.write_line(line)
        return True

    # Handle 'reset' subcommand
    if subcommand == "reset":
        from pgtail_py.cli_highlight import handle_highlight_reset

        success, message = handle_highlight_reset(config, warn)

        if log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Unknown subcommand
    msg = f"Unknown subcommand: {subcommand}. Use: list, on, off, enable, disable, add, remove, export, import, preview, reset"
    if log_widget is not None:
        log_widget.write_line(f"[red]{msg}[/red]")
    return True


def handle_set_command(
    args: list[str],
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'set' command to configure settings in tail mode.

    Args:
        args: Command arguments (e.g., ['highlighting.duration.slow', '50'])
        state: AppState instance
        log_widget: TailLog widget or None

    Returns:
        True if command was handled
    """
    from pgtail_py.cli_config import _get_config_value, _set_config_value, apply_setting
    from pgtail_py.cli_utils import warn
    from pgtail_py.config import (
        SETTINGS_SCHEMA,
        get_default_value,
        parse_value,
        save_config,
        validate_key,
    )

    # No args - show usage and available settings
    if not args:
        if log_widget is not None:
            log_widget.write_line("[dim]Usage: set <key> [value][/dim]")
            log_widget.write_line("")
            log_widget.write_line("[bold]Available settings:[/bold]")
            for key in SETTINGS_SCHEMA:
                log_widget.write_line(f"  [cyan]{key}[/cyan]")
        return True

    key = args[0]

    # Validate key
    if not validate_key(key):
        msg = f"Unknown setting: {key}"
        if log_widget is not None:
            log_widget.write_line(f"[red]{msg}[/red]")
        return True

    # No value - display current value
    if len(args) == 1:
        current = _get_config_value(state, key)
        if log_widget is not None:
            default = get_default_value(key)
            msg = f"[cyan]{key}[/cyan] = [magenta]{current!r}[/magenta]"
            if current != default:
                msg += f" [dim](default: {default!r})[/dim]"
            log_widget.write_line(msg)
        return True

    # Parse and validate value
    raw_value = args[1:]
    try:
        value = parse_value(key, raw_value if len(raw_value) > 1 else raw_value[0])
    except ValueError as e:
        msg = f"Invalid value for {key}: {e}"
        if log_widget is not None:
            log_widget.write_line(f"[red]{msg}[/red]")
        return True

    # Validate the value using schema validator
    _, validator, _ = SETTINGS_SCHEMA[key]
    try:
        validated = validator(value)
    except ValueError as e:
        msg = f"Invalid value for {key}: {e}"
        if log_widget is not None:
            log_widget.write_line(f"[red]{msg}[/red]")
        return True

    # Save to config file
    if not save_config(key, validated, warn_func=warn):
        msg = "Failed to save configuration"
        if log_widget is not None:
            log_widget.write_line(f"[red]{msg}[/red]")
        return True

    # Update in-memory config
    _set_config_value(state, key, validated)

    # Apply changes immediately
    apply_setting(state, key)

    # Provide feedback
    if log_widget is not None:
        log_widget.write_line(
            f"[green]Set[/green] [cyan]{key}[/cyan] = [magenta]{validated!r}[/magenta]"
        )

    return True
