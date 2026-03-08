"""Command handler for tail mode commands.

Extracted from TailApp to keep tail_textual.py under the file size
constitution limit. Contains the command dispatch logic and export
command handler as top-level functions.
"""

from __future__ import annotations

import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pgtail_py.tail_rich import format_entry_compact

if TYPE_CHECKING:
    from pgtail_py.cli import AppState
    from pgtail_py.parser import LogEntry
    from pgtail_py.tail_log import TailLog
    from pgtail_py.tail_status import TailStatus
    from pgtail_py.tailer import LogTailer


@dataclass
class TailCommandContext:
    """Context for tail mode command execution.

    Bundles all the dependencies that command handlers need from TailApp,
    avoiding excessive parameter lists on each handler function.
    """

    status: TailStatus
    state: AppState
    tailer: LogTailer | None
    log_widget: TailLog
    entries: list[LogEntry]
    stop_callback: Callable[[], None]
    set_paused: Callable[[bool], None]
    rebuild_log: Callable[..., None]
    reset_to_anchor: Callable[[], None]
    update_status: Callable[[], None]
    entry_filter: Callable[[LogEntry], bool]


def handle_export_command(
    args: list[str],
    ctx: TailCommandContext,
) -> None:
    """Handle export command in tail mode.

    Exports currently displayed entries to a file.

    Args:
        args: Command arguments [path, --format <fmt>, --highlighted]
        ctx: Command execution context.
    """
    from pgtail_py.export import ExportFormat, export_to_file

    if not args:
        ctx.log_widget.write_line(
            "[bold red]✗[/] Usage: export <path> [--format text|json|csv] [--highlighted]"
        )
        return

    # Parse arguments
    path_str: str | None = None
    fmt = ExportFormat.TEXT
    preserve_markup = False

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--format" and i + 1 < len(args):
            try:
                fmt = ExportFormat.from_string(args[i + 1])
            except ValueError as e:
                ctx.log_widget.write_line(f"[bold red]✗[/] {e}")
                return
            i += 2
        elif arg == "--highlighted":
            preserve_markup = True
            i += 1
        elif not arg.startswith("-"):
            path_str = arg
            i += 1
        else:
            ctx.log_widget.write_line(f"[bold red]✗[/] Unknown option: {arg}")
            return

    if not path_str:
        ctx.log_widget.write_line("[bold red]✗[/] No output path specified")
        return

    # Expand ~ and resolve path
    path = Path(path_str).expanduser().resolve()

    # Get entries that match current filters
    filtered_entries = [e for e in ctx.entries if ctx.entry_filter(e)]

    if not filtered_entries:
        ctx.log_widget.write_line(
            "[yellow]⚠[/] No entries to export (buffer empty or all filtered)"
        )
        return

    # Export
    try:
        if preserve_markup and fmt == ExportFormat.TEXT:
            # For --highlighted in tail mode, export the Rich-formatted lines
            from pgtail_py.export import ensure_parent_dirs

            ensure_parent_dirs(path)
            count = 0
            with open(path, "w", encoding="utf-8") as f:
                for entry in filtered_entries:
                    formatted = format_entry_compact(
                        entry,
                        theme=ctx.state.theme_manager.current_theme,
                        highlighting_config=ctx.state.highlighting_config,
                    )
                    f.write(formatted + "\n")
                    count += 1
        else:
            # Standard export (strips markup for clean text/JSON/CSV)
            count = export_to_file(
                filtered_entries,
                path,
                fmt,
                append=False,
                preserve_markup=False,
            )
        ctx.log_widget.write_line(f"[bold green]✓[/] Exported {count} entries to [cyan]{path}[/]")
    except OSError as e:
        ctx.log_widget.write_line(f"[bold red]✗[/] Export failed: {e}")


def handle_command(command_text: str, ctx: TailCommandContext) -> None:
    """Handle a command entered in the tail mode input line.

    Args:
        command_text: The command text entered by the user.
        ctx: Command execution context.
    """
    from pgtail_py.cli_tail import handle_tail_command

    # Use shlex to properly handle quoted arguments
    try:
        parts = shlex.split(command_text.strip())
    except ValueError:
        # Unclosed quote or other parse error - fall back to simple split
        parts = command_text.strip().split()
    if not parts:
        return

    cmd = parts[0].lower()
    args = parts[1:]

    log_widget = ctx.log_widget

    # Guard against uninitialized state
    if ctx.status is None or ctx.tailer is None:
        return

    # Handle clear command specially for anchor behavior
    if cmd == "clear":
        if args and args[0].lower() == "force":
            # clear force: clear everything including anchor, start fresh
            ctx.entries.clear()
            handle_tail_command(
                cmd=cmd,
                args=[],
                status=ctx.status,
                state=ctx.state,
                tailer=ctx.tailer,
                stop_callback=ctx.stop_callback,
                log_widget=log_widget,
            )
        else:
            # clear: reset to anchor (initial filters when tail mode started)
            ctx.reset_to_anchor()
        ctx.update_status()
        return

    # Handle pause/follow commands to set explicit pause flag
    if cmd in ("pause", "p"):
        ctx.set_paused(True)
        ctx.status.set_follow_mode(False, 0)
        ctx.update_status()
        return

    if cmd in ("follow", "f"):
        ctx.set_paused(False)
        ctx.status.set_follow_mode(True, 0)
        # Rebuild log to include entries that arrived while paused
        ctx.rebuild_log(on_complete=lambda: log_widget.scroll_end())
        ctx.update_status()
        return

    # Handle theme command - switch theme and rebuild log with new colors
    if cmd == "theme":
        if not args:
            current = ctx.state.theme_manager.current_theme
            if current:
                log_widget.write_line(f"[dim]Current theme:[/] [bold cyan]{current.name}[/]")
            else:
                log_widget.write_line("[dim]No theme set[/]")
        else:
            theme_name = args[0]
            if ctx.state.theme_manager.switch_theme(theme_name):
                ctx.rebuild_log(
                    on_complete=lambda: log_widget.write_line(
                        f"[bold green]✓[/] Switched to theme [bold cyan]{theme_name}[/]"
                    )
                )
            else:
                available = ", ".join(sorted(ctx.state.theme_manager._themes.keys()))
                log_widget.write_line(
                    f"[bold red]✗[/] Unknown theme [bold yellow]{theme_name}[/]. "
                    f"Available: {available}"
                )
        ctx.update_status()
        return

    # Handle export command - needs access to entries
    if cmd == "export":
        handle_export_command(args, ctx)
        return

    # Check if this is a help request (don't rebuild log for help)
    is_help_request = args and args[0].lower() in ("help", "?")

    # Track if this is a filter command that needs log rebuild
    filter_commands = {"level", "filter", "since", "until", "between"}
    needs_rebuild = cmd in filter_commands and not is_help_request

    # Highlight commands that modify state need rebuild + cache reset
    highlight_modifies = {"enable", "disable", "add", "remove", "on", "off"}
    needs_highlight_rebuild = (
        cmd == "highlight"
        and args
        and args[0].lower() in highlight_modifies
        and not is_help_request
    )

    # Set commands that modify highlighting duration thresholds need rebuild
    needs_set_highlight_rebuild = (
        cmd == "set"
        and len(args) >= 2
        and args[0].startswith("highlighting.duration.")
        and not is_help_request
    )

    # Snapshot config state before command execution so we can detect
    # whether the command actually modified highlighting (avoids reporting
    # success for commands that were rejected by validation).
    hl_config = ctx.state.highlighting_config
    _hl_snapshot = (
        (
            hl_config.enabled,
            dict(hl_config.enabled_highlighters),
            [(c.name, c.enabled) for c in hl_config.custom_highlighters],
        )
        if needs_highlight_rebuild
        else None
    )
    _dur_snapshot = (
        (hl_config.duration_slow, hl_config.duration_very_slow, hl_config.duration_critical)
        if needs_set_highlight_rebuild
        else None
    )

    handle_tail_command(
        cmd=cmd,
        args=args,
        status=ctx.status,
        state=ctx.state,
        tailer=ctx.tailer,
        stop_callback=ctx.stop_callback,
        log_widget=log_widget,
    )

    # Rebuild log with new filters applied to stored entries
    if needs_rebuild:
        ctx.rebuild_log()

    # Highlight changes need cache reset and rebuild to re-render with new styles.
    # Only rebuild + show success feedback when the config actually changed;
    # on failure the handler already wrote an error to log_widget.
    if needs_highlight_rebuild and _hl_snapshot is not None:
        hl_after = (
            hl_config.enabled,
            dict(hl_config.enabled_highlighters),
            [(c.name, c.enabled) for c in hl_config.custom_highlighters],
        )
        if hl_after != _hl_snapshot:
            from pgtail_py.tail_rich import reset_highlighter_chain

            reset_highlighter_chain()
            # Build feedback message to show after rebuild completes
            subcommand = args[0].lower()
            feedback: str | None = None
            if subcommand == "add" and len(args) >= 2:
                feedback = f"[green]Added highlighter '{args[1]}'[/green]"
            elif subcommand == "remove" and len(args) >= 2:
                feedback = f"[green]Removed highlighter '{args[1]}'[/green]"
            elif subcommand == "enable" and len(args) >= 2:
                feedback = f"[green]Enabled highlighter '{args[1]}'[/green]"
            elif subcommand == "disable" and len(args) >= 2:
                feedback = f"[green]Disabled highlighter '{args[1]}'[/green]"
            elif subcommand == "on":
                feedback = "[green]Highlighting enabled[/green]"
            elif subcommand == "off":
                feedback = "[yellow]Highlighting disabled[/yellow]"
            if feedback:
                msg = feedback  # capture for closure
                ctx.rebuild_log(on_complete=lambda: log_widget.write_line(msg))
            else:
                ctx.rebuild_log()

    # Set highlighting.duration.* changes need cache reset and rebuild.
    # Only rebuild when the thresholds actually changed.
    if needs_set_highlight_rebuild and _dur_snapshot is not None:
        dur_after = (
            hl_config.duration_slow,
            hl_config.duration_very_slow,
            hl_config.duration_critical,
        )
        if dur_after != _dur_snapshot:
            from pgtail_py.tail_rich import reset_highlighter_chain

            reset_highlighter_chain()
            key = args[0]
            value = args[1] if len(args) > 1 else ""
            msg = f"[green]Set[/green] [cyan]{key}[/cyan] = [magenta]{value}[/magenta]"
            ctx.rebuild_log(on_complete=lambda: log_widget.write_line(msg))

    ctx.update_status()
