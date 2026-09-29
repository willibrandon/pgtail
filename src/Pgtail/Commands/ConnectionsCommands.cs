using System.Globalization;
using System.Runtime.CompilerServices;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Statistics;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Commands;

/// <summary>
/// The <c>connections</c> command: active connections, history sparklines, and a live event stream.
/// </summary>
internal static class ConnectionsCommands
{
    private static readonly TextStyle Yellow = StyleParser.Parse("ansiyellow");
    private static readonly TextStyle Green = StyleParser.Parse("ansigreen");
    private static readonly TextStyle BrightGreen = StyleParser.Parse("ansibrightgreen");
    private static readonly TextStyle BrightYellow = StyleParser.Parse("ansibrightyellow");
    private static readonly TextStyle BrightRed = StyleParser.Parse("ansibrightred");
    private static readonly TextStyle Red = StyleParser.Parse("ansired");
    private static readonly TextStyle Bold = StyleParser.Parse("bold");

    private static readonly string[] NoData =
    [
        "No connection data available.",
        "Start tailing a log with `tail` to begin tracking connections.",
        "Note: PostgreSQL must have log_connections=on and log_disconnections=on",
    ];

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

        if (options.Watch)
        {
            await WatchAsync(invocation, options.Filter);
            return;
        }

        Report(invocation, options);
    }

    /// <summary>
    /// Tail mode's command, which reports into the log; the tail log already shows events as they arrive.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Tail(CommandInvocation invocation)
    {
        if (Parse(invocation) is not { } options)
        {
            return Task.CompletedTask;
        }

        if (options.Clear || options.History || !options.Filter.IsEmpty)
        {
            Report(invocation, options);
            return Task.CompletedTask;
        }

        var stats = invocation.Session.Connections;
        var output = invocation.Output;
        output.Markup("[bold cyan]Connection Statistics[/bold cyan]");
        output.Markup($"  Active: [magenta]{stats.ActiveCount}[/magenta]  Connects: [green]{stats.ConnectCount}[/green]  "
            + $"Disconnects: [red]{stats.DisconnectCount}[/red]");
        foreach (var (title, counts) in new[] { ("By Database", stats.GetByDatabase()), ("By User", stats.GetByUser()) })
        {
            if (counts.Count == 0)
            {
                continue;
            }

            output.Markup($"[dim]  {title}:[/dim]");
            foreach (var (name, count) in counts.OrderByDescending(pair => pair.Value).Take(5))
            {
                output.Markup($"    [cyan]{Markup.Escape(name)}[/cyan]: [magenta]{count}[/magenta]");
            }
        }

        return Task.CompletedTask;
    }

    private static (bool Clear, bool History, bool Watch, ConnectionFilter Filter)? Parse(CommandInvocation invocation)
    {
        var args = invocation.Args;
        var output = invocation.Output;
        if (args.Contains("clear"))
        {
            if (args.Count > 1)
            {
                output.Line("Warning: clear ignores other options", Yellow);
            }

            return (true, false, false, new ConnectionFilter());
        }

        var (history, watch) = (false, false);
        string? database = null, user = null, application = null;
        foreach (var argument in args)
        {
            switch (argument)
            {
                case "--history":
                    history = true;
                    break;
                case "--watch":
                    watch = true;
                    break;
                case var db when db.StartsWith("--db=", StringComparison.Ordinal):
                    database = db[5..];
                    break;
                case var name when name.StartsWith("--user=", StringComparison.Ordinal):
                    user = name[7..];
                    break;
                case var app when app.StartsWith("--app=", StringComparison.Ordinal):
                    application = app[6..];
                    break;
                default:
                    output.Line("Usage: connections [--history] [--watch] [--db=NAME] [--user=NAME] [--app=NAME] [clear]", Yellow);
                    return null;
            }
        }

        if (history && watch)
        {
            output.Line("Cannot use --history and --watch together.", Yellow);
            return null;
        }

        return (false, history, watch, new ConnectionFilter(database, user, application));
    }

    private static void Report(CommandInvocation invocation, (bool Clear, bool History, bool Watch, ConnectionFilter Filter) options)
    {
        var session = invocation.Session;
        var output = invocation.Output;
        if (options.Clear)
        {
            session.Connections.Clear();
            output.Line("Connection statistics cleared.");
        }
        else if (options.History)
        {
            History(session, output, options.Filter);
        }
        else
        {
            Summary(session, output, options.Filter);
        }
    }

    private static string Describe(ConnectionFilter filter)
    {
        var parts = new List<string>();
        if (filter.Database is { } database)
        {
            parts.Add($"db='{database}'");
        }

        if (filter.User is { } user)
        {
            parts.Add($"user='{user}'");
        }

        if (filter.Application is { } application)
        {
            parts.Add($"app='{application}'");
        }

        return string.Join(", ", parts);
    }

    private static void Summary(PgtailSession session, CommandOutput output, ConnectionFilter filter)
    {
        var stats = session.Connections;
        if (stats.IsEmpty)
        {
            output.Lines(NoData);
            return;
        }

        var active = stats.GetActiveConnections(filter);
        var header = filter.IsEmpty ? new StyledText("Active connections:", Bold) : new StyledText("Active connections", Bold)
            .Append($" (filter: {Describe(filter)}):");
        output.Line(header.Append(" ").Append(active.Count.ToString(CultureInfo.InvariantCulture), Green));
        output.Line();
        foreach (var (title, key) in new (string, Func<ConnectionEvent, string>)[]
        {
            ("By database:", item => item.Database ?? "unknown"),
            ("By user:", item => item.User ?? "unknown"),
            ("By application:", item => item.Application),
        })
        {
            var groups = active.GroupBy(key).Select(group => (Name: group.Key, Count: group.Count()))
                .OrderByDescending(pair => pair.Count).ToList();
            if (groups.Count == 0)
            {
                continue;
            }

            output.Line(title);
            foreach (var (name, count) in groups)
            {
                output.Line($"  {name,-15} {count,5}");
            }

            output.Line();
        }

        var totals = $"Session totals: {stats.ConnectCount} connects, {stats.DisconnectCount} disconnects";
        output.Line(stats.FailedCount > 0 ? $"{totals}, {stats.FailedCount} failed" : totals);
    }

    private static void History(PgtailSession session, CommandOutput output, ConnectionFilter filter)
    {
        var stats = session.Connections;
        if (stats.IsEmpty)
        {
            output.Lines(NoData);
            return;
        }

        const int minutes = 60;
        const int bucketSize = 15;
        const int count = minutes / bucketSize;
        var connects = new int[count];
        var disconnects = new int[count];
        var now = DateTime.UtcNow;
        foreach (var item in stats.GetEvents())
        {
            if (!filter.IsEmpty && !filter.Matches(item))
            {
                continue;
            }

            var ago = (now - LogTimestamps.ToUtc(item.Timestamp)).TotalMinutes;
            if (ago is < 0 or >= minutes)
            {
                continue;
            }

            var index = Math.Clamp(count - 1 - (int)(ago / bucketSize), 0, count - 1);
            if (item.Type == ConnectionEventType.Connect)
            {
                connects[index]++;
            }
            else if (item.Type == ConnectionEventType.Disconnect)
            {
                disconnects[index]++;
            }
        }

        var totalConnects = connects.Sum();
        var totalDisconnects = disconnects.Sum();
        var net = totalConnects - totalDisconnects;
        var filterText = filter.IsEmpty ? "" : $" (filter: {Describe(filter)})";
        output.Line($"Connection History{filterText} (last 60 min, 15-min buckets)", Bold);
        output.Line("─────────────────────────────────────────────────");
        output.Line();
        output.Line(new StyledText("  ").Append("Connects:", Green).Append($"    {ErrorTrend.Sparkline(connects)}  total {totalConnects}"));
        output.Line(new StyledText("  ").Append("Disconnects:", Yellow)
            .Append($" {ErrorTrend.Sparkline(disconnects)}  total {totalDisconnects}"));
        output.Line();
        output.Line(net switch
        {
            > 0 => new StyledText("  Net change: ").Append($"+{net}", Green).Append(" (connections growing)"),
            < 0 => new StyledText("  Net change: ").Append(net.ToString(CultureInfo.InvariantCulture), Yellow)
                .Append(" (connections decreasing)"),
            _ => new StyledText("  Net change: 0 (stable)"),
        });

        if (totalConnects > 10 && totalDisconnects == 0)
        {
            output.Line();
            output.Line(new StyledText("  ").Append("⚠ Possible connection leak detected:", Red)
                .Append(" connections without disconnections"));
        }
        else if (totalConnects > 20 && totalDisconnects < totalConnects * 0.1)
        {
            output.Line();
            output.Line(new StyledText("  ").Append("⚠ Low disconnect rate:", Yellow)
                .Append($" only {totalDisconnects} disconnects for {totalConnects} connects"));
        }

        output.Line();
        output.Line(new StyledText("  Active now: ").Append(stats.ActiveCount.ToString(CultureInfo.InvariantCulture), Green));
    }

    private static async Task WatchAsync(CommandInvocation invocation, ConnectionFilter filter)
    {
        var session = invocation.Session;
        var output = invocation.Output;
        var instance = session.LastSource?.Instance
            ?? session.Instances.FirstOrDefault(item => item.LogPath is { } log && File.Exists(log));
        if (instance?.LogPath is not { } path)
        {
            output.Line("No log file available. Use 'tail' first to select an instance.", Yellow);
            return;
        }

        if (!File.Exists(path))
        {
            output.Line($"Log file not found: {path}", Yellow);
            return;
        }

        // The log is opened before the header shows, so every event written after it is seen.
        var source = new LogTailer(path, fromStart: false, instance.DataDirectory, instance.LogDirectory, LogSources.PollInterval);
        source.Start();
        var filterText = filter.IsEmpty ? "" : $" (filter: {Describe(filter)})";
        output.Line(new StyledText($"Watching connections{filterText}", Bold).Append($" - {Path.GetFileName(path)} (Ctrl+C to exit)"));
        output.Line(new StyledText().Append("[+]", Green).Append(" connect  ").Append("[-]", Yellow).Append(" disconnect  ")
            .Append("[!]", Red).Append(" failed"));
        output.Line();
        await CoreCommands.Repl(invocation).WatchAsync(cancellationToken => Events(session, source, filter, cancellationToken));
    }

    private static async IAsyncEnumerable<StyledText> Events(
        PgtailSession session,
        LogTailer source,
        ConnectionFilter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        var seen = 0;
        await using (source)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    _ = await source.Events.WaitToReadAsync(cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }

                while (source.Events.TryRead(out var item))
                {
                    if (item.Entry is not { } entry || ConnectionEvent.FromEntry(entry) is not { } connection)
                    {
                        continue;
                    }

                    _ = session.Connections.Add(entry);
                    if (filter.IsEmpty || filter.Matches(connection))
                    {
                        seen++;
                        yield return Format(connection);
                    }
                }
            }
        }

        yield return new StyledText();
        yield return new StyledText($"Exited watch mode. {seen} events seen.");
    }

    private static StyledText Format(ConnectionEvent item)
    {
        var time = LogTimestamps.ToLocal(item.Timestamp).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
        var details = $"{item.User ?? "?"}@{item.Database ?? "?"}";
        if (item.Application != "unknown" && item.Application.Length > 0)
        {
            details += $" ({item.Application})";
        }

        if (item.Host is { Length: > 0 } host)
        {
            details += $" from {host}";
        }

        return item.Type switch
        {
            ConnectionEventType.Connect => new StyledText("[+]", BrightGreen).Append($" {time}  {details}"),
            ConnectionEventType.Disconnect => new StyledText("[-]", BrightYellow)
                .Append($" {time}  {details}{Duration(item.DurationSeconds)}"),
            _ => new StyledText("[!]", BrightRed).Append($" {time}  {details} FAILED"),
        };
    }

    private static string Duration(double? seconds) => seconds switch
    {
        null => "",
        < 60 => string.Create(CultureInfo.InvariantCulture, $" ({seconds.Value:F1}s)"),
        < 3600 => $" ({(int)(seconds.Value / 60)}m{(int)(seconds.Value % 60)}s)",
        _ => $" ({(int)(seconds.Value / 3600)}h{(int)(seconds.Value % 3600 / 60)}m)",
    };
}
