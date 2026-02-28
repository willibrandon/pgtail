"""Centralized permission fix advice for PostgreSQL log and config access errors.

Provides platform-aware (Windows, Linux, macOS) guidance for resolving
permission issues when accessing PostgreSQL log files and configuration.
"""

import sys


def get_log_permission_advice(
    *,
    rich_markup: bool = False,
    platform: str | None = None,
) -> list[str]:
    """Get advice for fixing log file permission errors.

    Returns platform-specific guidance for when log files exist but cannot
    be read due to OS permissions. Supports both plain text (REPL) and
    Rich markup (Textual) output.

    Args:
        rich_markup: If True, return lines with Rich markup tags.
        platform: Override platform detection (e.g. "win32", "linux", "darwin").
            Defaults to sys.platform.

    Returns:
        List of advice lines.
    """
    plat = platform or sys.platform
    if plat == "win32":
        return _windows_log_advice(rich_markup=rich_markup)
    elif plat == "darwin":
        return _unix_log_advice(
            log_dir_path="/usr/local/var/log/postgresql",
            rich_markup=rich_markup,
        )
    else:
        return _unix_log_advice(
            log_dir_path="/var/log/postgresql",
            rich_markup=rich_markup,
        )


def get_conf_permission_advice(
    conf_path: str,
    *,
    rich_markup: bool = False,
    platform: str | None = None,
) -> list[str]:
    """Get advice for fixing postgresql.conf permission errors.

    Returns platform-specific guidance for when postgresql.conf cannot
    be read or written due to OS permissions.

    Args:
        conf_path: Path to the postgresql.conf file that could not be accessed.
        rich_markup: If True, return lines with Rich markup tags.
        platform: Override platform detection (e.g. "win32", "linux", "darwin").
            Defaults to sys.platform.

    Returns:
        List of advice lines.
    """
    plat = platform or sys.platform
    if plat == "win32":
        return _windows_conf_advice(conf_path, rich_markup=rich_markup)
    else:
        return _unix_conf_advice(conf_path, rich_markup=rich_markup)


def get_logs_not_found_advice(
    *,
    rich_markup: bool = False,
    platform: str | None = None,
) -> list[str]:
    """Get advice for when log files cannot be found at all.

    Different from permission errors: this is for the case where logging
    may not be enabled or the log directory is inaccessible.

    Args:
        rich_markup: If True, return lines with Rich markup tags.
        platform: Override platform detection (e.g. "win32", "linux", "darwin").
            Defaults to sys.platform.

    Returns:
        List of advice lines.
    """
    plat = platform or sys.platform
    if plat == "win32":
        return _windows_logs_not_found_advice(rich_markup=rich_markup)
    elif plat == "darwin":
        return _unix_logs_not_found_advice(
            log_dir_path="/usr/local/var/log/postgresql",
            rich_markup=rich_markup,
        )
    else:
        return _unix_logs_not_found_advice(
            log_dir_path="/var/log/postgresql",
            rich_markup=rich_markup,
        )


# -- Windows advice ----------------------------------------------------------


def _windows_log_advice(*, rich_markup: bool = False) -> list[str]:
    """Windows-specific advice for log file permission errors."""
    if rich_markup:
        return [
            "[dim]Options to fix:[/]",
            "",
            "[dim]1. Run your terminal as Administrator (quick fix):[/]",
            "   [cyan]Right-click terminal → Run as administrator[/]",
            "",
            "[dim]2. Grant your user read access to the log directory:[/]",
            '   [cyan]icacls "C:\\...\\data\\log" /grant %USERNAME%:(OI)(CI)R[/]',
            "",
            "[dim]3. Or redirect logs to an accessible directory:[/]",
            "   [cyan]log_directory = 'C:/PgLogs'[/]  [dim]in postgresql.conf[/]",
            "   [dim]Then restart PostgreSQL via Services (services.msc)[/]",
        ]
    return [
        "Options to fix:",
        "",
        "1. Run your terminal as Administrator (quick fix):",
        "   Right-click terminal -> Run as administrator",
        "",
        "2. Grant your user read access to the log directory:",
        '   icacls "C:\\...\\data\\log" /grant %USERNAME%:(OI)(CI)R',
        "",
        "3. Or redirect logs to an accessible directory:",
        "   Set in postgresql.conf:",
        "     log_directory = 'C:/PgLogs'",
        "   Then restart PostgreSQL via Services (services.msc)",
    ]


def _windows_conf_advice(conf_path: str, *, rich_markup: bool = False) -> list[str]:
    """Windows-specific advice for postgresql.conf permission errors."""
    if rich_markup:
        return [
            "[dim]Options to fix:[/]",
            "",
            "[dim]1. Run your terminal as Administrator:[/]",
            "   [cyan]Right-click terminal → Run as administrator[/]",
            "",
            "[dim]2. Grant your user access to the config file:[/]",
            f'   [cyan]icacls "{conf_path}" /grant %USERNAME%:R[/]',
        ]
    return [
        "Options to fix:",
        "",
        "1. Run your terminal as Administrator:",
        "   Right-click terminal -> Run as administrator",
        "",
        "2. Grant your user access to the config file:",
        f'   icacls "{conf_path}" /grant %USERNAME%:R',
    ]


def _windows_logs_not_found_advice(*, rich_markup: bool = False) -> list[str]:
    """Windows-specific advice when log files cannot be found."""
    if rich_markup:
        return [
            "[dim]Ensure logging is enabled in postgresql.conf:[/]",
            "   [cyan]logging_collector = on[/]",
            "",
            "[dim]Then restart PostgreSQL via Services (services.msc).[/]",
            "",
            "[dim]If logs still can't be read, try:[/]",
            "",
            "[dim]1. Run your terminal as Administrator:[/]",
            "   [cyan]Right-click terminal → Run as administrator[/]",
            "",
            "[dim]2. Or redirect logs to an accessible directory:[/]",
            "   [cyan]log_directory = 'C:/PgLogs'[/]  [dim]in postgresql.conf[/]",
            "   [dim]Then restart PostgreSQL via Services (services.msc)[/]",
        ]
    return [
        "Ensure logging is enabled in postgresql.conf:",
        "   logging_collector = on",
        "",
        "Then restart PostgreSQL via Services (services.msc).",
        "",
        "If logs still can't be read, try:",
        "",
        "1. Run your terminal as Administrator:",
        "   Right-click terminal -> Run as administrator",
        "",
        "2. Or redirect logs to an accessible directory:",
        "   Set in postgresql.conf:",
        "     log_directory = 'C:/PgLogs'",
        "   Then restart PostgreSQL via Services (services.msc)",
    ]


# -- Unix/macOS advice -------------------------------------------------------


def _unix_log_advice(log_dir_path: str, *, rich_markup: bool = False) -> list[str]:
    """Unix/macOS advice for log file permission errors."""
    if rich_markup:
        return [
            "[dim]Options to fix:[/]",
            "",
            "[dim]1. Make log files group-readable (recommended):[/]",
            "   [cyan]log_file_mode = 0640[/]  [dim]in postgresql.conf[/]",
            "   [cyan]sudo usermod -aG postgres $USER[/]",
            "   [dim](log out and back in, then restart PostgreSQL)[/]",
            "",
            "[dim]2. Or redirect logs to an accessible directory:[/]",
            f"   [cyan]log_directory = '{log_dir_path}'[/]  [dim]in postgresql.conf[/]",
            "   [dim]Then restart PostgreSQL.[/]",
        ]
    return [
        "Options to fix:",
        "",
        "1. Make log files group-readable (recommended):",
        "   Set in postgresql.conf:",
        "     log_file_mode = 0640",
        "   Then add your user to the postgres group:",
        "     sudo usermod -aG postgres $USER",
        "   (log out and back in, then restart PostgreSQL)",
        "",
        "2. Or redirect logs to an accessible directory:",
        "   Set in postgresql.conf:",
        f"     log_directory = '{log_dir_path}'",
        "   Then restart PostgreSQL.",
    ]


def _unix_conf_advice(conf_path: str, *, rich_markup: bool = False) -> list[str]:
    """Unix/macOS advice for postgresql.conf permission errors."""
    if rich_markup:
        return [
            "[dim]Options to fix:[/]",
            "",
            "[dim]1. Edit as the postgres user:[/]",
            f"   [cyan]sudo -u postgres nano {conf_path}[/]",
            "",
            "[dim]2. Or run pgtail as the postgres user:[/]",
            "   [cyan]sudo -u postgres pgtail[/]",
        ]
    return [
        "Options to fix:",
        "",
        "1. Edit as the postgres user:",
        f"   sudo -u postgres nano {conf_path}",
        "",
        "2. Or run pgtail as the postgres user:",
        "   sudo -u postgres pgtail",
    ]


def _unix_logs_not_found_advice(
    log_dir_path: str,
    *,
    rich_markup: bool = False,
) -> list[str]:
    """Unix/macOS advice when log files cannot be found."""
    if rich_markup:
        return [
            "[dim]The log directory is inside a restricted data directory.[/]",
            "",
            "[dim]Options to fix:[/]",
            "",
            "[dim]1. Make log files group-readable (recommended):[/]",
            "   [cyan]log_file_mode = 0640[/]  [dim]in postgresql.conf[/]",
            "   [cyan]sudo usermod -aG postgres $USER[/]",
            "   [dim](log out and back in, then restart PostgreSQL)[/]",
            "",
            "[dim]2. Or redirect logs to an accessible directory:[/]",
            f"   [cyan]log_directory = '{log_dir_path}'[/]  [dim]in postgresql.conf[/]",
            "   [dim]Then restart PostgreSQL.[/]",
        ]
    return [
        "The log directory is inside a restricted data directory.",
        "",
        "Options to fix:",
        "",
        "1. Make log files group-readable (recommended):",
        "   Set in postgresql.conf:",
        "     log_file_mode = 0640",
        "   Then add your user to the postgres group:",
        "     sudo usermod -aG postgres $USER",
        "   (log out and back in, then restart PostgreSQL)",
        "",
        "2. Or redirect logs to an accessible directory:",
        "   Set in postgresql.conf:",
        f"     log_directory = '{log_dir_path}'",
        "   Then restart PostgreSQL.",
    ]
