"""Slow query detection and statistics commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pgtail_py.slow_query import SlowQueryConfig, validate_thresholds

if TYPE_CHECKING:
    from pgtail_py.cli import AppState


def slow_command(state: AppState, args: list[str]) -> None:
    """Handle the 'slow' command - configure slow query highlighting.

    Args:
        state: Current application state.
        args: Command arguments:
            - No args: Display current configuration
            - 'off': Disable slow query highlighting
            - Three numbers: Set warning/slow/critical thresholds in ms
    """
    # No args - display current configuration
    if not args:
        if state.slow_query_config.enabled:
            print("Slow query highlighting: ENABLED")
            print()
            print("Thresholds:")
            print(state.slow_query_config.format_thresholds())
        else:
            print("Slow query highlighting: DISABLED")
            print()
            print("Usage:")
            print("  slow <warning> <slow> <critical>  Enable with thresholds (in ms)")
            print("  slow off                          Disable highlighting")
            print()
            print("Example: slow 100 500 1000")
        return

    # Handle 'off' subcommand
    if args[0].lower() == "off":
        state.slow_query_config.enabled = False
        print("Slow query highlighting disabled")
        return

    # Three numeric arguments - set custom thresholds
    if len(args) != 3:
        print("Error: Expected 3 threshold values or 'off'")
        print("Usage: slow <warning> <slow> <critical>")
        print("Example: slow 100 500 1000")
        return

    # Parse threshold values
    try:
        warning = float(args[0])
        slow = float(args[1])
        critical = float(args[2])
    except ValueError:
        print("Error: Thresholds must be numbers")
        print("Usage: slow <warning> <slow> <critical>")
        print("Example: slow 100 500 1000")
        return

    # Validate thresholds
    error = validate_thresholds(warning, slow, critical)
    if error:
        print(f"Error: {error}")
        return

    # Apply new configuration
    state.slow_query_config = SlowQueryConfig(
        enabled=True,
        warning_ms=warning,
        slow_ms=slow,
        critical_ms=critical,
    )

    print("Slow query highlighting enabled")
    print()
    print("Thresholds:")
    print(state.slow_query_config.format_thresholds())
    print()
    print("Note: PostgreSQL must have log_min_duration_statement enabled to log query durations.")
    if state.current_instance and state.current_instance.port:
        port = state.current_instance.port
        print(
            f'  psql -p {port} -c "ALTER SYSTEM SET log_min_duration_statement = 0; SELECT pg_reload_conf();"'
        )
    else:
        print(
            '  psql -p <port> -c "ALTER SYSTEM SET log_min_duration_statement = 0; SELECT pg_reload_conf();"'
        )
        print("  (Use 'list' to see instance ports)")


def stats_command(state: AppState) -> None:
    """Handle the 'stats' command - display query duration statistics.

    Args:
        state: Current application state.
    """
    # Handle empty stats
    if state.duration_stats.is_empty():
        print("No query duration data collected yet.")
        print()
        print("Duration statistics are collected automatically while tailing logs.")
        print("PostgreSQL must have log_min_duration_statement enabled to log query durations.")
        return

    # Display statistics summary
    print(state.duration_stats.format_summary())
