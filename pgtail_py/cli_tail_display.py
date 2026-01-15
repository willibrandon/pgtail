"""Display command handlers for tail mode.

This module provides handlers for display commands (errors, connections)
executed within the tail mode interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.formatted_text import FormattedText

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.tail_buffer import TailBuffer
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus


def handle_errors_command(
    args: list[str],
    buffer: TailBuffer | None,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'errors' command to show error summary.

    Args:
        args: Command arguments (e.g., ['--trend'])
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    error_stats = state.error_stats

    # Build summary
    lines: list[tuple[str, str]] = []

    total = error_stats.error_count + error_stats.warning_count
    lines.append(("", "Error Statistics (session)\n"))
    lines.append(("", f"  Total: {total}\n"))

    # By severity
    by_level = error_stats.get_by_level()
    if by_level:
        lines.append(("", "  By Level:\n"))
        for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True):
            lines.append(("", f"    {level.name}: {count}\n"))

    # By SQLSTATE
    by_code = error_stats.get_by_code()
    if by_code:
        lines.append(("", "  By SQLSTATE:\n"))
        for code, count in sorted(by_code.items(), key=lambda x: x[1], reverse=True)[:10]:
            lines.append(("", f"    {code}: {count}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled errors to log
        log_widget.write_line(
            f"[bold cyan]Error Statistics[/bold cyan]  Total: [magenta]{total}[/magenta]"
        )
        if by_level:
            log_widget.write_line("[dim]  By Level:[/dim]")
            for level, count in sorted(by_level.items(), key=lambda x: x[1], reverse=True):
                # Color by severity
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
    buffer: TailBuffer | None,
    state: AppState,
    log_widget: TailLog | None = None,
) -> bool:
    """Handle 'connections' command to show connection summary.

    Args:
        args: Command arguments
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    conn_stats = state.connection_stats

    # Build summary
    lines: list[tuple[str, str]] = []

    lines.append(("", "Connection Statistics (session)\n"))
    lines.append(("", f"  Active: {conn_stats.active_count()}\n"))
    lines.append(("", f"  Total connects: {conn_stats.connect_count}\n"))
    lines.append(("", f"  Total disconnects: {conn_stats.disconnect_count}\n"))

    # By database
    by_db = conn_stats.get_by_database()
    if by_db:
        lines.append(("", "  By Database:\n"))
        for db, count in sorted(by_db.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(("", f"    {db}: {count}\n"))

    # By user
    by_user = conn_stats.get_by_user()
    if by_user:
        lines.append(("", "  By User:\n"))
        for user, count in sorted(by_user.items(), key=lambda x: x[1], reverse=True)[:5]:
            lines.append(("", f"    {user}: {count}\n"))

    if buffer is not None:
        buffer.insert_command_output(FormattedText(lines))
    elif log_widget is not None:
        # Textual mode: write styled connections to log
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
    buffer: TailBuffer | None,
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
        buffer: TailBuffer instance (prompt_toolkit) or None (Textual)
        status: TailStatus instance
        state: AppState instance
        log_widget: TailLog widget (Textual) or None

    Returns:
        True if command was handled
    """
    from pgtail_py.cli_highlight import (
        format_highlight_list,
        format_highlight_list_rich,
        handle_highlight_add,
        handle_highlight_disable,
        handle_highlight_enable,
        handle_highlight_remove,
    )
    from pgtail_py.cli_utils import warn

    config = state.highlighting_config

    # No args or 'list' - show highlighter list
    if not args or (args and args[0].lower() == "list"):
        if buffer is not None:
            # prompt_toolkit mode
            buffer.insert_command_output(format_highlight_list(config))
        elif log_widget is not None:
            # Textual mode - use Rich markup
            output = format_highlight_list_rich(config)
            for line in output.split("\n"):
                if line:  # Skip empty lines
                    log_widget.write_line(line)
        return True

    subcommand = args[0].lower()

    # Handle 'enable' subcommand
    if subcommand == "enable":
        if len(args) < 2:
            msg = "Usage: highlight enable <name>"
            if buffer is not None:
                buffer.insert_command_output(FormattedText([("class:error", msg)]))
            elif log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_enable(name, config, warn)

        if buffer is not None:
            style = "" if success else "class:error"
            buffer.insert_command_output(FormattedText([(style, message)]))
        elif log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'disable' subcommand
    if subcommand == "disable":
        if len(args) < 2:
            msg = "Usage: highlight disable <name>"
            if buffer is not None:
                buffer.insert_command_output(FormattedText([("class:error", msg)]))
            elif log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_disable(name, config, warn)

        if buffer is not None:
            style = "" if success else "class:error"
            buffer.insert_command_output(FormattedText([(style, message)]))
        elif log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'add' subcommand
    if subcommand == "add":
        success, message = handle_highlight_add(args[1:], config, warn)

        if buffer is not None:
            style = "" if success else "class:error"
            buffer.insert_command_output(FormattedText([(style, message)]))
        elif log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Handle 'remove' subcommand
    if subcommand == "remove":
        if len(args) < 2:
            msg = "Usage: highlight remove <name>"
            if buffer is not None:
                buffer.insert_command_output(FormattedText([("class:error", msg)]))
            elif log_widget is not None:
                log_widget.write_line(f"[red]{msg}[/red]")
            return True

        name = args[1]
        success, message = handle_highlight_remove(name, config, warn)

        if buffer is not None:
            style = "" if success else "class:error"
            buffer.insert_command_output(FormattedText([(style, message)]))
        elif log_widget is not None:
            color = "green" if success else "red"
            log_widget.write_line(f"[{color}]{message}[/{color}]")
        return True

    # Unknown subcommand
    msg = f"Unknown subcommand: {subcommand}. Use: list, enable, disable, add, remove"
    if buffer is not None:
        buffer.insert_command_output(FormattedText([("class:error", msg)]))
    elif log_widget is not None:
        log_widget.write_line(f"[red]{msg}[/red]")
    return True
