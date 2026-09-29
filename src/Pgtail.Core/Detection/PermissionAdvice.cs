namespace Pgtail.Detection;

/// <summary>
/// Platform-specific advice for log and configuration files pgtail cannot read.
/// </summary>
/// <remarks>
/// Advice shown in tail mode is markup, so commands are highlighted; advice the REPL prints is plain.
/// </remarks>
public static class PermissionAdvice
{
    /// <summary>
    /// How to read a log file that exists but is not readable, as markup for tail mode.
    /// </summary>
    /// <param name="path">The log file.</param>
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> LogPermission(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (OperatingSystem.IsWindows())
        {
            return
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
            ];
        }

        // pg_ctlcluster writes a Debian or Ubuntu cluster's log readable by the adm group.
        if (path.StartsWith(PostgresConf.DebianLogDirectory + "/", StringComparison.Ordinal))
        {
            return
            [
                "[dim]Options to fix:[/]",
                "",
                "[dim]1. Join the adm group, which can read the server logs (recommended):[/]",
                "   [cyan]sudo usermod -aG adm $USER[/]",
                "   [dim](log out and back in)[/]",
                "",
                "[dim]2. Or run pgtail as the postgres user:[/]",
                "   [cyan]sudo -u postgres pgtail[/]",
            ];
        }

        return UnixLogAdvice(UnixLogDirectory, markup: true, prefix: []);
    }

    /// <summary>
    /// How to read or write a <c>postgresql.conf</c> that is not accessible.
    /// </summary>
    /// <param name="confPath">The configuration file.</param>
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> ConfPermission(string confPath)
    {
        ArgumentNullException.ThrowIfNull(confPath);
        return OperatingSystem.IsWindows()
            ?
            [
                "Options to fix:",
                "",
                "1. Run your terminal as Administrator:",
                "   Right-click terminal -> Run as administrator",
                "",
                "2. Grant your user access to the config file:",
                $"   icacls \"{confPath}\" /grant %USERNAME%:R",
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
    /// <returns>The advice lines.</returns>
    public static IReadOnlyList<string> LogsNotFound()
    {
        if (OperatingSystem.IsWindows())
        {
            return
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

        return UnixLogAdvice(UnixLogDirectory, markup: false, prefix: ["The log directory is inside a restricted data directory.", ""]);
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
