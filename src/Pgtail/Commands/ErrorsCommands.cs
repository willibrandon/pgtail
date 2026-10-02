using System.Globalization;
using Pgtail.Detection;
using Pgtail.Filtering;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Statistics;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Commands;

/// <summary>
/// The <c>errors</c> command: error and warning statistics, trends, codes, and a live counter.
/// </summary>
internal static class ErrorsCommands
{
    private static readonly TextStyle s_yellow = StyleParser.Parse("ansiyellow");
    private static readonly TextStyle s_red = StyleParser.Parse("ansired");
    private static readonly TextStyle s_bold = StyleParser.Parse("bold");
    private static readonly TextStyle s_brightRed = StyleParser.Parse("ansibrightred");
    private static readonly TextStyle s_brightYellow = StyleParser.Parse("ansibrightyellow");

    /// <summary>
    /// The REPL command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the command has finished.</returns>
    public static async Task Repl(CommandInvocation invocation)
    {
        if (Parse(invocation) is not { } options)
        {
            return;
        }

        if (options.Live)
        {
            await LiveAsync(invocation);
            return;
        }

        Report(invocation, options);
    }

    /// <summary>
    /// Tail mode's command, which reports into the log; <c>--live</c> is not needed there.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Tail(CommandInvocation invocation)
    {
        if (Parse(invocation) is not { } options)
        {
            return Task.CompletedTask;
        }

        if (options.Clear || options.Trend || options.Code is not null || options.Since is not null)
        {
            Report(invocation, options);
            return Task.CompletedTask;
        }

        ErrorStats stats = invocation.Session.Errors;
        CommandOutput output = invocation.Output;
        output.Markup($"[bold cyan]Error Statistics[/bold cyan]  Total: [magenta]{stats.ErrorCount + stats.WarningCount}[/magenta]");
        IReadOnlyDictionary<LogLevel, int> byLevel = stats.GetByLevel();
        if (byLevel.Count > 0)
        {
            output.Markup("[dim]  By Level:[/dim]");
            foreach ((LogLevel level, int count) in byLevel.OrderByDescending(pair => pair.Value))
            {
                string color = level switch
                {
                    LogLevel.Panic => "bold red",
                    LogLevel.Fatal => "red",
                    LogLevel.Error => "yellow",
                    LogLevel.Warning => "cyan",
                    _ => "white",
                };

                output.Markup($"    [{color}]{level.ToName()}[/{color}]: [magenta]{count}[/magenta]");
            }
        }

        IReadOnlyList<KeyValuePair<string, int>> byCode = stats.GetByCode();
        if (byCode.Count > 0)
        {
            output.Markup("[dim]  By SQLSTATE:[/dim]");
            foreach ((string code, int count) in byCode.OrderByDescending(pair => pair.Value).Take(10))
            {
                output.Markup($"    [cyan]{code}[/cyan]: [magenta]{count}[/magenta]");
            }
        }

        return Task.CompletedTask;
    }

    private static (bool Clear, bool Trend, bool Live, string? Code, DateTime? Since)? Parse(CommandInvocation invocation)
    {
        IReadOnlyList<string> args = invocation.Args;
        CommandOutput output = invocation.Output;
        (bool clear, bool trend, bool live) = (false, false, false);
        string? code = null;
        DateTime? since = null;
        for (int i = 0; i < args.Count; i++)
        {
            switch (args[i])
            {
                case "clear":
                    clear = true;
                    break;
                case "--trend":
                    trend = true;
                    break;
                case "--live":
                    live = true;
                    break;
                case "--code" when i + 1 < args.Count:
                    code = args[++i];
                    break;
                case "--since" when i + 1 < args.Count:
                    try
                    {
                        since = TimeParser.Parse(args[++i]);
                    }
                    catch (FormatException exception)
                    {
                        output.Line($"Invalid time format: {exception.Message}", s_yellow);
                        return null;
                    }

                    break;
                default:
                    output.Line("Usage: errors [--trend] [--code CODE] [--since TIME] [--live] [clear]", s_yellow);
                    return null;
            }
        }

        string? conflict = (live, trend, code, since) switch
        {
            (true, true, _, _) => "Cannot use --live and --trend together.",
            (true, _, not null, _) => "Cannot use --live and --code together.",
            (true, _, _, not null) => "Cannot use --live and --since together.",
            (_, true, not null, _) => "Cannot use --trend and --code together.",
            _ => null,
        };

        if (conflict is not null)
        {
            output.Line(conflict, s_yellow);
            return null;
        }

        return (clear, trend, live, code, since);
    }

    private static void Report(CommandInvocation invocation, (bool Clear, bool Trend, bool Live, string? Code, DateTime? Since) options)
    {
        PgtailSession session = invocation.Session;
        CommandOutput output = invocation.Output;
        if (options.Clear)
        {
            session.Errors.Clear();
            output.Line("Error statistics cleared.");
        }
        else if (options.Code is { } code)
        {
            ByCode(session, output, code, options.Since);
        }
        else if (options.Trend)
        {
            Trend(session, output, options.Since);
        }
        else
        {
            Summary(session, output, options.Since);
        }
    }

    private static void Summary(PgtailSession session, CommandOutput output, DateTime? since)
    {
        ErrorStats stats = session.Errors;
        if (stats.IsEmpty)
        {
            output.Line("No errors recorded in this session.");
            return;
        }

        IReadOnlyList<ErrorEvent> events = since is { } bound ? stats.GetEventsSince(bound) : stats.GetEvents();
        if (events.Count == 0)
        {
            output.Line($"No errors recorded {Describe(since!.Value)}.");
            return;
        }

        int errors = events.Count(item => ErrorStats.IsError(item.Level));
        output.Line($"Error Statistics{(since is { } start ? $" ({Describe(start)})" : "")}", s_bold);
        output.Line("─────────────────────────────");
        output.Line(new StyledText("Errors: ").Append(errors.ToString(CultureInfo.InvariantCulture), s_red)
            .Append("  Warnings: ").Append((events.Count - errors).ToString(CultureInfo.InvariantCulture), s_yellow));
        var byCode = events.GroupBy(item => item.SqlState ?? "UNKNOWN")
            .Select(group => (Code: group.Key, Count: group.Count()))
            .OrderByDescending(pair => pair.Count)
            .Take(10)
            .ToList();
        output.Line();
        output.Line("By type:");
        foreach ((string code, int count) in byCode)
        {
            string name = SqlStates.GetName(code);
            output.Line(name != code
                ? $"  {code} {name,-25} {count,5}"
                : $"  {code,-31} {count,5}");
        }

        output.Line();
        output.Line("By level:");
        foreach (IGrouping<LogLevel, ErrorEvent>? group in events.GroupBy(item => item.Level).OrderBy(group => group.Key))
        {
            output.Line($"  {group.Key.ToName(),-9} {group.Count(),5}");
        }
    }

    private static void Trend(PgtailSession session, CommandOutput output, DateTime? since)
    {
        ErrorStats stats = session.Errors;
        if (stats.IsEmpty)
        {
            output.Line("No errors recorded in this session.");
            return;
        }

        IReadOnlyList<int> buckets;
        string label;
        if (since is { } bound)
        {
            IReadOnlyList<ErrorEvent> events = stats.GetEventsSince(bound);
            if (events.Count == 0)
            {
                output.Line($"No errors recorded {Describe(bound)}.");
                return;
            }

            int minutes = (int)Math.Clamp((DateTime.UtcNow - LogTimestamps.ToUtc(bound)).TotalMinutes, 1, 60);
            buckets = ErrorTrend.Bucket(events, minutes);
            label = Describe(bound);
        }
        else
        {
            buckets = stats.GetTrendBuckets(60);
            label = "Last 60 min";
        }

        int total = buckets.Sum();
        double average = buckets.Count > 0 ? (double)total / buckets.Count : 0;
        string spike = "";
        if (average > 0 && buckets.Max() is var peak && peak > average * 2)
        {
            int index = buckets.ToList().IndexOf(peak);
            spike = $"  ← spike {buckets.Count - index - 1}m ago ({peak}/min)";
        }

        output.Line("Error rate (per minute):");
        output.Line();
        output.Line(string.Create(CultureInfo.InvariantCulture,
            $"{label}: {ErrorTrend.Sparkline(buckets)}  total {total}, avg {average:F1}/min{spike}"));
    }

    private static void ByCode(PgtailSession session, CommandOutput output, string code, DateTime? since)
    {
        if (code.Length != 5)
        {
            output.Line("Invalid SQLSTATE code format. Expected 5 characters (e.g., 23505).", s_yellow);
            return;
        }

        IReadOnlyList<ErrorEvent> events = session.Errors.GetEventsByCode(code);
        if (since is { } bound)
        {
            DateTime utc = LogTimestamps.ToUtc(bound);
            events = [.. events.Where(item => LogTimestamps.ToUtc(item.Timestamp) >= utc)];
        }

        string window = since is { } start ? $" ({Describe(start)})" : "";
        if (events.Count == 0)
        {
            output.Line($"No errors with code {code} recorded{(since is { } s ? $" {Describe(s)}" : "")}.");
            return;
        }

        string name = SqlStates.GetName(code);
        output.Line(name != code ? $"{code} {name}{window}: {events.Count} occurrences" : $"{code}{window}: {events.Count} occurrences");
        output.Line();
        output.Line("Recent examples:");
        foreach (ErrorEvent? item in events.TakeLast(5))
        {
            string message = item.Message.Length > 60 ? item.Message[..60] + "..." : item.Message;
            output.Line($"  {LogTimestamps.ToLocal(item.Timestamp).ToString("HH:mm:ss", CultureInfo.InvariantCulture)} {message}");
        }
    }

    private static async Task LiveAsync(CommandInvocation invocation)
    {
        PgtailSession session = invocation.Session;
        CommandOutput output = invocation.Output;
        PostgresInstance? instance = session.LastSource?.Instance
            ?? session.Instances.FirstOrDefault(item => item.LogPath is { } log && File.Exists(log));
        if (instance?.LogPath is not { } path)
        {
            output.Line("No log file available. Use 'tail' first to select an instance.", s_yellow);
            return;
        }

        if (!File.Exists(path))
        {
            output.Line($"Log file not found: {path}", s_yellow);
            return;
        }

        await using var source = new LogTailer(
            path, fromStart: false, instance.DataDirectory, instance.LogDirectory, LogSources.PollInterval);
        source.Start();
        var header = new StyledText($"Live error counter - {Path.GetFileName(path)} (Ctrl+C to exit)");
        await CoreCommands.Repl(invocation).LiveAsync(() =>
        {
            while (source.Events.TryRead(out LogSourceEvent? item))
            {
                if (item.Entry is { } entry)
                {
                    session.Errors.Add(entry);
                }
            }

            ErrorStats stats = session.Errors;
            return
            [
                header,
                new StyledText(),
                new StyledText("Errors: ").Append(stats.ErrorCount.ToString(CultureInfo.InvariantCulture), s_brightRed)
                    .Append(" | Warnings: ").Append(stats.WarningCount.ToString(CultureInfo.InvariantCulture), s_brightYellow)
                    .Append($" | Last error: {Since(stats.LastErrorTime)}"),
            ];
        }, TimeSpan.FromMilliseconds(500));

        output.Line("Exited live mode.");
    }

    private static string Since(DateTime? last)
    {
        if (last is not { } time)
        {
            return "never";
        }

        int seconds = (int)(DateTime.UtcNow - LogTimestamps.ToUtc(time)).TotalSeconds;
        return seconds switch
        {
            < 60 => $"{seconds}s ago",
            < 3600 => $"{seconds / 60}m {seconds % 60}s ago",
            _ => $"{seconds / 3600}h {seconds % 3600 / 60}m ago",
        };
    }

    /// <summary>
    /// Describes a time window from its start, such as <c>last 5m</c>.
    /// </summary>
    /// <param name="since">The start.</param>
    /// <returns>The description.</returns>
    public static string Describe(DateTime since)
    {
        int seconds = (int)(DateTime.UtcNow - LogTimestamps.ToUtc(since)).TotalSeconds;
        return seconds switch
        {
            < 60 => $"last {seconds}s",
            < 3600 => $"last {seconds / 60}m",
            < 86400 => $"last {seconds / 3600}h",
            _ => $"since {LogTimestamps.ToLocal(since).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture)}",
        };
    }
}
