"""Typer-based CLI entry point for pgtail.

Provides a modern CLI interface with automatic --help generation while
maintaining backward compatibility with the existing REPL interface.
"""

from __future__ import annotations

from typing import Annotated

import typer

from pgtail_py.detector import detect_all
from pgtail_py.terminal import enable_vt100_mode
from pgtail_py.version import check_update_sync, get_version

app = typer.Typer(
    name="pgtail",
    help="Interactive PostgreSQL log tailer with auto-detection and color output.",
    no_args_is_help=False,
    add_completion=True,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"pgtail {get_version()}")
        raise typer.Exit()


def check_update_callback(value: bool) -> None:
    """Check for updates and exit."""
    if value:
        _available, message = check_update_sync()
        typer.echo(message)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
    check_update: Annotated[
        bool,
        typer.Option(
            "--check-update",
            callback=check_update_callback,
            is_eager=True,
            help="Check for updates and exit.",
        ),
    ] = False,
) -> None:
    """Interactive PostgreSQL log tailer.

    When called without a command, starts the interactive REPL mode.
    Use --help with any command to see detailed usage.
    """
    if ctx.invoked_subcommand is None:
        # No subcommand provided - start REPL
        import sys

        # Check if stdin is a TTY - if not, exit gracefully
        # Exit silently because stdout may also be redirected/unavailable
        if not sys.stdin.isatty():
            raise SystemExit(0)

        # On Windows, detect if we were launched without an interactive parent shell
        # This catches: double-click launch, Start-Process, winget validation
        if sys.platform == "win32":
            try:
                import ctypes

                kernel32 = ctypes.windll.kernel32

                # Check console process list - if only 1 process (us), no shell is attached
                process_list = (ctypes.c_ulong * 16)()
                num_processes = kernel32.GetConsoleProcessList(process_list, 16)

                if num_processes == 1:
                    # Only our process is attached - no parent shell to provide input
                    # Exit silently (writing to stdout may hang on Windows new console)
                    raise SystemExit(0)

            except SystemExit:
                raise  # Re-raise SystemExit
            except Exception:
                pass  # If detection fails, continue with REPL

        from pgtail_py.cli import main as repl_main

        repl_main()


@app.command()
def list_instances(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed instance information."),
    ] = False,
) -> None:
    """List detected PostgreSQL instances."""
    enable_vt100_mode()

    instances = detect_all()

    if not instances:
        typer.echo("No PostgreSQL instances found.")
        raise typer.Exit(1)

    typer.echo(f"Found {len(instances)} instance(s):\n")
    typer.echo(f"{'ID':<4} {'Version':<10} {'Port':<6} {'Status':<8} {'Source'}")
    typer.echo("-" * 50)

    for inst in instances:
        status = "running" if inst.running else "stopped"
        typer.echo(
            f"{inst.id:<4} {inst.version or 'unknown':<10} "
            f"{inst.port or '-':<6} {status:<8} {inst.source.value}"
        )

    if verbose:
        typer.echo()
        for inst in instances:
            typer.echo(f"\n[Instance {inst.id}]")
            typer.echo(f"  Data directory: {inst.data_dir}")
            typer.echo(f"  Log path: {inst.log_path}")
            typer.echo(f"  Logging enabled: {inst.logging_enabled}")


@app.command()
def tail(
    instance_id: Annotated[int, typer.Argument(help="Instance ID to tail.")],
    since: Annotated[
        str | None,
        typer.Option("--since", "-s", help="Show entries from time (e.g., 5m, 1h, 14:30)."),
    ] = None,
    stream: Annotated[
        bool,
        typer.Option("--stream", help="Use legacy streaming mode instead of Textual UI."),
    ] = False,
) -> None:
    """Tail logs for a PostgreSQL instance.

    Enters the interactive tail mode with vim-style navigation and filtering.
    Press 'q' to quit, '?' for help.
    """
    enable_vt100_mode()

    instances = detect_all()

    if not instances:
        typer.echo("No PostgreSQL instances found.", err=True)
        raise typer.Exit(1)

    if instance_id < 0 or instance_id >= len(instances):
        typer.echo(
            f"Invalid instance ID: {instance_id}. Use 'pgtail list' to see instances.", err=True
        )
        raise typer.Exit(1)

    instance = instances[instance_id]

    if not instance.logging_enabled:
        typer.echo(f"Logging not enabled for instance {instance_id}.", err=True)
        typer.echo("Enable with: pgtail enable-logging", err=True)
        raise typer.Exit(1)

    if not instance.log_path or not instance.log_path.exists():
        typer.echo(f"Log file not found: {instance.log_path}", err=True)
        raise typer.Exit(1)

    # Import here to avoid circular imports and speed up CLI startup
    from pgtail_py.cli import AppState
    from pgtail_py.cli_core import tail_status_bar_mode, tail_stream_mode
    from pgtail_py.terminal import reset_terminal
    from pgtail_py.time_filter import TimeFilter, parse_time

    state = AppState()
    state.instances = instances

    if since:
        try:
            since_time = parse_time(since)
            state.time_filter = TimeFilter(since=since_time)
        except ValueError as e:
            typer.echo(f"Invalid time format: {e}", err=True)
            raise typer.Exit(1) from None

    state.current_instance = instance
    state.tailing = True

    try:
        if stream:
            tail_stream_mode(state, instance)
        else:
            tail_status_bar_mode(state, instance)
    except KeyboardInterrupt:
        pass
    finally:
        state.tailing = False
        state.current_instance = None
        reset_terminal()


@app.command()
def config(
    path: Annotated[
        bool,
        typer.Option("--path", "-p", help="Show config file path."),
    ] = False,
    edit: Annotated[
        bool,
        typer.Option("--edit", "-e", help="Open config in $EDITOR."),
    ] = False,
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset to defaults (creates backup)."),
    ] = False,
) -> None:
    """Show or manage configuration."""
    from pgtail_py.config import (
        create_default_config,
        get_config_path,
        load_config,
        reset_config,
    )

    config_path = get_config_path()

    if path:
        typer.echo(config_path)
        return

    if edit:
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "vi")
        if not config_path.exists():
            create_default_config()
        subprocess.run([editor, str(config_path)])
        return

    if reset:
        backup = reset_config()
        if backup:
            typer.echo(f"Config reset. Backup saved to: {backup}")
        else:
            typer.echo("No config file to reset.")
        return

    # Default: show config
    cfg = load_config()
    typer.echo(f"Config file: {config_path}")
    typer.echo()
    typer.echo("[default]")
    typer.echo(f"  levels = {cfg.default.levels}")
    typer.echo(f"  follow = {cfg.default.follow}")
    typer.echo()
    typer.echo("[slow]")
    typer.echo(f"  warn = {cfg.slow.warn}")
    typer.echo(f"  error = {cfg.slow.error}")
    typer.echo(f"  critical = {cfg.slow.critical}")
    typer.echo()
    typer.echo("[theme]")
    typer.echo(f"  name = {cfg.theme.name}")


def cli_main() -> None:
    """Entry point for the CLI."""
    app()
