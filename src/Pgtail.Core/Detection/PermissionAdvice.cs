using Pgtail.Styling;

namespace Pgtail.Detection;

/// <summary>
/// Platform-specific advice for log and configuration files pgtail cannot read.
/// </summary>
/// <remarks>
/// Each method has a plain form for the REPL and a markup form for tail mode, where commands are highlighted.
/// </remarks>
public static class PermissionAdvice
{
    /// <summary>
    /// How to read log files that exist but are not readable.
    /// </summary>
    /// <param name="markup">True for the markup form.</param>
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> LogPermission(bool markup = false)
    {
        if (OperatingSystem.IsWindows())
        {
            return markup
                ?
                [
                    "[dim]Options to fix:[/]",
                    "",
                    "[dim]1. Run your terminal as Administrator (quick fix):[/]",
                    "   [cyan]Right-click terminal → Run as administrator[/]",
                    "",
                    "[dim]2. Grant your user read access to the log directory:[/]",
                    "   [cyan]icacls \"C:\\...\\data\\log\" /grant %USERNAME%:(OI)(CI)R[/]",
                    "",
                    "[dim]3. Or redirect logs to an accessible directory:[/]",
                    "   [cyan]log_directory = 'C:/PgLogs'[/]  [dim]in postgresql.conf[/]",
                    "   [dim]Then restart PostgreSQL via Services (services.msc)[/]",
                ]
                :
                [
                    "Options to fix:",
                    "",
                    "1. Run your terminal as Administrator (quick fix):",
                    "   Right-click terminal -> Run as administrator",
                    "",
                    "2. Grant your user read access to the log directory:",
                    "   icacls \"C:\\...\\data\\log\" /grant %USERNAME%:(OI)(CI)R",
                    "",
                    "3. Or redirect logs to an accessible directory:",
                    "   Set in postgresql.conf:",
                    "     log_directory = 'C:/PgLogs'",
                    "   Then restart PostgreSQL via Services (services.msc)",
                ];
        }

        return UnixLogAdvice(UnixLogDirectory, markup, prefix: []);
    }

    /// <summary>
    /// How to read or write a <c>postgresql.conf</c> that is not accessible.
    /// </summary>
    /// <param name="confPath">The configuration file.</param>
    /// <param name="markup">True for the markup form.</param>
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> ConfPermission(string confPath, bool markup = false)
    {
        ArgumentNullException.ThrowIfNull(confPath);
        if (OperatingSystem.IsWindows())
        {
            return markup
                ?
                [
                    "[dim]Options to fix:[/]",
                    "",
                    "[dim]1. Run your terminal as Administrator:[/]",
                    "   [cyan]Right-click terminal → Run as administrator[/]",
                    "",
                    "[dim]2. Grant your user access to the config file:[/]",
                    $"   [cyan]icacls \"{Markup.Escape(confPath)}\" /grant %USERNAME%:R[/]",
                ]
                :
                [
                    "Options to fix:",
                    "",
                    "1. Run your terminal as Administrator:",
                    "   Right-click terminal -> Run as administrator",
                    "",
                    "2. Grant your user access to the config file:",
                    $"   icacls \"{confPath}\" /grant %USERNAME%:R",
                ];
        }

        return markup
            ?
            [
                "[dim]Options to fix:[/]",
                "",
                "[dim]1. Edit as the postgres user:[/]",
                $"   [cyan]sudo -u postgres nano {Markup.Escape(confPath)}[/]",
                "",
                "[dim]2. Or run pgtail as the postgres user:[/]",
                "   [cyan]sudo -u postgres pgtail[/]",
            ]
            :
            [
                "Options to fix:",
                "",
                "1. Edit as the postgres user:",
                $"   sudo -u postgres nano {confPath}",
                "",
                "2. Or run pgtail as the postgres user:",
                "   sudo -u postgres pgtail",
            ];
    }

    /// <summary>
    /// What to do when an instance logs but its log files cannot be found.
    /// </summary>
    /// <param name="markup">True for the markup form.</param>
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> LogsNotFound(bool markup = false)
    {
        if (OperatingSystem.IsWindows())
        {
            return markup
                ?
                [
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
                :
                [
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
                ];
        }

        return UnixLogAdvice(UnixLogDirectory, markup,
            prefix: markup ? ["[dim]The log directory is inside a restricted data directory.[/]", ""]
                : ["The log directory is inside a restricted data directory.", ""]);
    }

    private static string UnixLogDirectory => OperatingSystem.IsMacOS() ? "/usr/local/var/log/postgresql" : "/var/log/postgresql";

    private static List<string> UnixLogAdvice(string logDirectory, bool markup, IReadOnlyList<string> prefix)
    {
        List<string> advice = markup
            ?
            [
                "[dim]Options to fix:[/]",
                "",
                "[dim]1. Make log files group-readable (recommended):[/]",
                "   [cyan]log_file_mode = 0640[/]  [dim]in postgresql.conf[/]",
                "   [cyan]sudo usermod -aG postgres $USER[/]",
                "   [dim](log out and back in, then restart PostgreSQL)[/]",
                "",
                "[dim]2. Or redirect logs to an accessible directory:[/]",
                $"   [cyan]log_directory = '{logDirectory}'[/]  [dim]in postgresql.conf[/]",
                "   [dim]Then restart PostgreSQL.[/]",
            ]
            :
            [
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
                $"     log_directory = '{logDirectory}'",
                "   Then restart PostgreSQL.",
            ];
        return [.. prefix, .. advice];
    }
}
