using System.Globalization;
using Pgtail.Sessions;
using Pgtail.Statistics;

namespace Pgtail.Commands;

/// <summary>
/// Slow query highlighting and query duration statistics: <c>slow</c> and <c>stats</c>.
/// </summary>
internal static class SlowCommands
{
    private const string Usage = "Usage: slow <warning> <slow> <critical>";
    private const string Example = "Example: slow 100 500 1000";

    /// <summary>
    /// The REPL's <c>slow</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Slow(CommandInvocation invocation)
    {
        CommandOutput output = invocation.Output;
        PgtailSession session = invocation.Session;
        IReadOnlyList<string> args = invocation.Args;
        if (args.Count == 0)
        {
            if (session.Slow.Enabled)
            {
                output.Line("Slow query highlighting: ENABLED");
                output.Line();
                output.Line("Thresholds:");
                output.Line(session.Slow.FormatThresholds());
            }
            else
            {
                output.Line("Slow query highlighting: DISABLED");
                output.Line();
                output.Line("Usage:");
                output.Line("  slow <warning> <slow> <critical>  Enable with thresholds (in ms)");
                output.Line("  slow off                          Disable highlighting");
                output.Line();
                output.Line(Example);
            }

            return Task.CompletedTask;
        }

        if (args[0].Equals("off", StringComparison.OrdinalIgnoreCase))
        {
            session.Slow.Enabled = false;
            output.Line("Slow query highlighting disabled");
            return Task.CompletedTask;
        }

        if (args.Count != 3)
        {
            output.Line("Error: Expected 3 threshold values or 'off'");
            output.Line(Usage);
            output.Line(Example);
            return Task.CompletedTask;
        }

        if (!TryNumber(args[0], out double warning) || !TryNumber(args[1], out double slow) || !TryNumber(args[2], out double critical))
        {
            output.Line("Error: Thresholds must be numbers");
            output.Line(Usage);
            output.Line(Example);
            return Task.CompletedTask;
        }

        if (SlowQueryConfig.Validate(warning, slow, critical) is { } error)
        {
            output.Line($"Error: {error}");
            return Task.CompletedTask;
        }

        session.Slow = new SlowQueryConfig { Enabled = true, WarningMs = warning, SlowMs = slow, CriticalMs = critical };
        output.Line("Slow query highlighting enabled");
        output.Line();
        output.Line("Thresholds:");
        output.Line(session.Slow.FormatThresholds());
        output.Line();
        output.Line("Note: PostgreSQL must have log_min_duration_statement enabled to log query durations.");
        const string sql = "\"ALTER SYSTEM SET log_min_duration_statement = 0; SELECT pg_reload_conf();\"";
        if (session.LastSource?.Instance?.Port is { } port)
        {
            output.Line($"  psql -p {port.ToString(CultureInfo.InvariantCulture)} -c {sql}");
        }
        else
        {
            output.Line($"  psql -p <port> -c {sql}");
            output.Line("  (Use 'list' to see instance ports)");
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Tail mode's <c>slow</c> command: one threshold, with slow and critical at twice and five times it.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailSlow(CommandInvocation invocation)
    {
        var host = (ITailHost)invocation.Host;
        PgtailSession session = invocation.Session;
        IReadOnlyList<string> args = invocation.Args;
        if (args.Count == 0)
        {
            invocation.Output.Markup("[bold red]✗[/] Usage: slow <milliseconds>");
            return Task.CompletedTask;
        }

        if (args[0].ToLowerInvariant() is "off" or "clear")
        {
            session.Slow.Enabled = false;
            host.RefreshStatus();
            host.Rebuild();
            return Task.CompletedTask;
        }

        if (!int.TryParse(args[0], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out int threshold) || threshold <= 0)
        {
            invocation.Output.Markup("[bold red]✗[/] Threshold must be a positive number of milliseconds");
            return Task.CompletedTask;
        }

        session.Slow = new SlowQueryConfig
        {
            Enabled = true,
            WarningMs = threshold,
            SlowMs = threshold * 2.0,
            CriticalMs = threshold * 5.0,
        };

        host.RefreshStatus();
        host.Rebuild();
        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL's <c>stats</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Stats(CommandInvocation invocation)
    {
        CommandOutput output = invocation.Output;
        DurationStats durations = invocation.Session.Durations;
        if (durations.IsEmpty)
        {
            output.Line("No query duration data collected yet.");
            output.Line();
            output.Line("Duration statistics are collected automatically while tailing logs.");
            output.Line("PostgreSQL must have log_min_duration_statement enabled to log query durations.");
            return Task.CompletedTask;
        }

        output.Line(durations.FormatSummary());
        return Task.CompletedTask;
    }

    private static bool TryNumber(string text, out double value) =>
        double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
}
