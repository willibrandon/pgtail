"""Typer-based CLI entry point for pgtail.

Provides a modern CLI interface with automatic --help generation while
maintaining backward compatibility with the existing REPL interface.
"""

from __future__ import annotations

from pathlib import Path
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

        # On Windows, wrap REPL startup to catch any initialization failures
        # (e.g., prompt_toolkit failing in non-interactive environments)
        if sys.platform == "win32":
            try:
                repl_main()
            except Exception:
                # Exit gracefully if REPL fails to start on Windows
                raise SystemExit(0) from None
        else:
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
    instance_id: Annotated[
        int | None,
        typer.Argument(help="Instance ID to tail (optional if --file is used)."),
    ] = None,
    file: Annotated[
        list[str] | None,
        typer.Option(
            "--file",
            "-f",
            help="Path or glob pattern to tail. Can specify multiple times.",
        ),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", "-s", help="Show entries from time (e.g., 5m, 1h, 14:30)."),
    ] = None,
    stream: Annotated[
        bool,
        typer.Option("--stream", help="Use legacy streaming mode instead of Textual UI."),
    ] = False,
) -> None:
    """Tail logs for a PostgreSQL instance or arbitrary log file(s).

    Enters the interactive tail mode with vim-style navigation and filtering.
    Press 'q' to quit, '?' for help.

    Examples:

        # Tail by instance ID
        pgtail tail 0

        # Tail arbitrary log file
        pgtail tail --file ./tmp_check/log/postmaster.log

        # Tail with glob pattern (multiple files)
        pgtail tail --file "*.log"

        # Tail multiple explicit files
        pgtail tail --file a.log --file b.log

        # Tail with time filter
        pgtail tail --file ./test.log --since 5m
    """
    from pgtail_py.cli_utils import validate_file_path, validate_tail_args

    enable_vt100_mode()

    # Convert single file to list format check
    file_path_str = file[0] if file and len(file) == 1 else None

    # T019: Validate mutual exclusivity (single file case)
    error = validate_tail_args(file_path=file_path_str, instance_id=instance_id)
    if error:
        typer.echo(error, err=True)
        raise typer.Exit(1)

    # Import here to avoid circular imports and speed up CLI startup
    from pgtail_py.cli import AppState
    from pgtail_py.cli_core import tail_status_bar_mode, tail_stream_mode
    from pgtail_py.multi_tailer import GlobPattern, is_glob_pattern
    from pgtail_py.tail_textual import TailApp
    from pgtail_py.terminal import reset_terminal
    from pgtail_py.time_filter import TimeFilter, parse_time

    state = AppState()

    # T073, T074: Handle --file option(s) with glob pattern support
    if file is not None:
        # File-only mode - skip instance detection
        resolved_paths: list[tuple[Path, str | None]] = []  # (path, glob_pattern_or_None)
        has_glob = False

        for file_arg in file:
            if is_glob_pattern(file_arg):
                # T073: Expand glob pattern
                has_glob = True
                glob = GlobPattern.from_path(file_arg)
                matches = glob.expand()

                if not matches:
                    # T074: Handle "No files match pattern" error
                    typer.echo(f"No files match pattern: {file_arg}", err=True)
                    raise typer.Exit(1)

                # Warn if many files matched
                if len(matches) > 10:
                    typer.echo(f"Warning: Pattern matches {len(matches)} files", err=True)

                for path in matches:
                    resolved_paths.append((path, file_arg))
            else:
                # Single file path
                resolved_path, path_error = validate_file_path(file_arg)
                if path_error:
                    typer.echo(path_error, err=True)
                    raise typer.Exit(1)
                resolved_paths.append((resolved_path, None))

        # Apply time filter if provided
        if since:
            try:
                since_time = parse_time(since)
                state.time_filter = TimeFilter(since=since_time)
            except ValueError as e:
                typer.echo(f"Invalid time format: {e}", err=True)
                raise typer.Exit(1) from None

        # Determine display name
        if len(resolved_paths) == 1:
            display_name = resolved_paths[0][0].name
        elif has_glob:
            display_name = f"{len(resolved_paths)} files"
        else:
            display_name = f"{len(resolved_paths)} files"

        # T022, T023: Set state and launch tail mode
        state.current_file_path = resolved_paths[0][0]  # Primary file
        state.tailing = True

        try:
            if stream:
                # Legacy stream mode - only supports single file
                if len(resolved_paths) > 1:
                    typer.echo("--stream mode only supports single file. Use without --stream for multiple files.", err=True)
                    raise typer.Exit(1)
                from pgtail_py.instance import Instance

                file_instance = Instance.file_only(resolved_paths[0][0])
                tail_stream_mode(state, file_instance)
            else:
                # Determine glob pattern for dynamic file watching
                glob_pattern_str = next((p[1] for p in resolved_paths if p[1]), None)

                # T022: Call TailApp with file paths
                TailApp.run_tail_mode(
                    state=state,
                    instance=None,
                    log_path=resolved_paths[0][0],
                    filename=display_name,
                    multi_file_paths=[p[0] for p in resolved_paths] if len(resolved_paths) > 1 else None,
                    glob_pattern=glob_pattern_str,
                )
        except KeyboardInterrupt:
            pass
        finally:
            state.tailing = False
            state.current_file_path = None
            reset_terminal()
        return

    # Standard instance-based tailing
    instances = detect_all()
    state.instances = instances

    if not instances:
        typer.echo("No PostgreSQL instances found.", err=True)
        raise typer.Exit(1)

    # If no instance ID and no --file, require explicit ID
    if instance_id is None:
        if len(instances) == 1:
            instance_id = 0
        else:
            typer.echo("Multiple instances found. Specify an ID or use --file.", err=True)
            typer.echo("Use 'pgtail list' to see available instances.", err=True)
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
