using System.Globalization;
using System.Runtime.CompilerServices;
using Pgtail.Detection;
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
    private static readonly TextStyle s_yellow = StyleParser.Parse("ansiyellow");
    private static readonly TextStyle s_green = StyleParser.Parse("ansigreen");
    private static readonly TextStyle s_brightGreen = StyleParser.Parse("ansibrightgreen");
    private static readonly TextStyle s_brightYellow = StyleParser.Parse("ansibrightyellow");
    private static readonly TextStyle s_brightRed = StyleParser.Parse("ansibrightred");
    private static readonly TextStyle s_red = StyleParser.Parse("ansired");
    private static readonly TextStyle s_bold = StyleParser.Parse("bold");

    private static readonly string[] s_noData =
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

        ConnectionStats stats = invocation.Session.Connections;
        CommandOutput output = invocation.Output;
        output.Markup("[bold cyan]Connection Statistics[/bold cyan]");
        output.Markup($"  Active: [magenta]{stats.ActiveCount}[/magenta]  Connects: [green]{stats.ConnectCount}[/green]  "
            + $"Disconnects: [red]{stats.DisconnectCount}[/red]");
        (string Title, IReadOnlyList<KeyValuePair<string, int>> Counts)[] groups =
            [("By Database", stats.GetByDatabase()), ("By User", stats.GetByUser())];
        foreach ((string title, IReadOnlyList<KeyValuePair<string, int>> counts) in groups)
        {
            if (counts.Count == 0)
            {
                continue;
            }

            output.Markup($"[dim]  {title}:[/dim]");
            foreach ((string name, int count) in counts.OrderByDescending(pair => pair.Value).Take(5))
            {
                output.Markup($"    [cyan]{Markup.Escape(name)}[/cyan]: [magenta]{count}[/magenta]");
            }
        }

        return Task.CompletedTask;
    }

    private static (bool Clear, bool History, bool Watch, ConnectionFilter Filter)? Parse(CommandInvocation invocation)
    {
        IReadOnlyList<string> args = invocation.Args;
        CommandOutput output = invocation.Output;
        if (args.Contains("clear"))
        {
            if (args.Count > 1)
            {
                output.Line("Warning: clear ignores other options", s_yellow);
            }

            return (true, false, false, new ConnectionFilter());
        }

        (bool history, bool watch) = (false, false);
        string? database = null, user = null, application = null;
        foreach (string argument in args)
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
                    output.Line("Usage: connections [--history] [--watch] [--db=NAME] [--user=NAME] [--app=NAME] [clear]", s_yellow);
                    return null;
            }
        }

        if (history && watch)
        {
            output.Line("Cannot use --history and --watch together.", s_yellow);
            return null;
        }

        return (false, history, watch, new ConnectionFilter(database, user, application));
    }

    private static void Report(CommandInvocation invocation, (bool Clear, bool History, bool Watch, ConnectionFilter Filter) options)
    {
        PgtailSession session = invocation.Session;
        CommandOutput output = invocation.Output;
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
        ConnectionStats stats = session.Connections;
        if (stats.IsEmpty)
        {
            output.Lines(s_noData);
            return;
        }

        IReadOnlyList<ConnectionEvent> active = stats.GetActiveConnections(filter);
        StyledText header = filter.IsEmpty ? new StyledText("Active connections:", s_bold) : new StyledText("Active connections", s_bold)
            .Append($" (filter: {Describe(filter)}):");
        output.Line(header.Append(" ").Append(active.Count.ToString(CultureInfo.InvariantCulture), s_green));
        output.Line();
        foreach ((string title, Func<ConnectionEvent, string> key) in new (string, Func<ConnectionEvent, string>)[]
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
            foreach ((string name, int count) in groups)
            {
                output.Line($"  {name,-15} {count,5}");
            }

            output.Line();
        }

        string totals = $"Session totals: {stats.ConnectCount} connects, {stats.DisconnectCount} disconnects";
        output.Line(stats.FailedCount > 0 ? $"{totals}, {stats.FailedCount} failed" : totals);
    }

    private static void History(PgtailSession session, CommandOutput output, ConnectionFilter filter)
    {
        ConnectionStats stats = session.Connections;
        if (stats.IsEmpty)
        {
            output.Lines(s_noData);
            return;
        }

        const int minutes = 60;
        const int bucketSize = 15;
        const int count = minutes / bucketSize;
        int[] connects = new int[count];
        int[] disconnects = new int[count];
        DateTime now = DateTime.UtcNow;
        foreach (ConnectionEvent item in stats.GetEvents())
        {
            if (!filter.IsEmpty && !filter.Matches(item))
            {
                continue;
            }

            double ago = (now - LogTimestamps.ToUtc(item.Timestamp)).TotalMinutes;
            if (ago is < 0 or >= minutes)
            {
                continue;
            }

            int index = Math.Clamp(count - 1 - (int)(ago / bucketSize), 0, count - 1);
            if (item.Type == ConnectionEventType.Connect)
            {
                connects[index]++;
            }
            else if (item.Type == ConnectionEventType.Disconnect)
            {
                disconnects[index]++;
            }
        }

        int totalConnects = connects.Sum();
        int totalDisconnects = disconnects.Sum();
        int net = totalConnects - totalDisconnects;
        string filterText = filter.IsEmpty ? "" : $" (filter: {Describe(filter)})";
        output.Line($"Connection History{filterText} (last 60 min, 15-min buckets)", s_bold);
        output.Line("─────────────────────────────────────────────────");
        output.Line();
        output.Line(new StyledText("  ").Append("Connects:", s_green)
            .Append($"    {ErrorTrend.Sparkline(connects)}  total {totalConnects}"));
        output.Line(new StyledText("  ").Append("Disconnects:", s_yellow)
            .Append($" {ErrorTrend.Sparkline(disconnects)}  total {totalDisconnects}"));
        output.Line();
        output.Line(net switch
        {
            > 0 => new StyledText("  Net change: ").Append($"+{net}", s_green).Append(" (connections growing)"),
            < 0 => new StyledText("  Net change: ").Append(net.ToString(CultureInfo.InvariantCulture), s_yellow)
                .Append(" (connections decreasing)"),
            _ => new StyledText("  Net change: 0 (stable)"),
        });

        if (totalConnects > 10 && totalDisconnects == 0)
        {
            output.Line();
            output.Line(new StyledText("  ").Append("⚠ Possible connection leak detected:", s_red)
                .Append(" connections without disconnections"));
        }
        else if (totalConnects > 20 && totalDisconnects < totalConnects * 0.1)
        {
            output.Line();
            output.Line(new StyledText("  ").Append("⚠ Low disconnect rate:", s_yellow)
                .Append($" only {totalDisconnects} disconnects for {totalConnects} connects"));
        }

        output.Line();
        output.Line(new StyledText("  Active now: ").Append(stats.ActiveCount.ToString(CultureInfo.InvariantCulture), s_green));
    }

    private static async Task WatchAsync(CommandInvocation invocation, ConnectionFilter filter)
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

        // The log is opened before the header shows, so every event written after it is seen.
        var source = new LogTailer(path, fromStart: false, instance.DataDirectory, instance.LogDirectory, LogSources.PollInterval);
        source.Start();
        string filterText = filter.IsEmpty ? "" : $" (filter: {Describe(filter)})";
        output.Line(new StyledText($"Watching connections{filterText}", s_bold).Append($" - {Path.GetFileName(path)} (Ctrl+C to exit)"));
        output.Line(new StyledText().Append("[+]", s_green).Append(" connect  ").Append("[-]", s_yellow).Append(" disconnect  ")
            .Append("[!]", s_red).Append(" failed"));
        output.Line();
        await CoreCommands.Repl(invocation).WatchAsync(cancellationToken => Events(session, source, filter, cancellationToken));
    }

    private static async IAsyncEnumerable<StyledText> Events(
        PgtailSession session,
        LogTailer source,
        ConnectionFilter filter,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        int seen = 0;
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

                while (source.Events.TryRead(out LogSourceEvent? item))
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
        string time = LogTimestamps.ToLocal(item.Timestamp).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
        string details = $"{item.User ?? "?"}@{item.Database ?? "?"}";
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
            ConnectionEventType.Connect => new StyledText("[+]", s_brightGreen).Append($" {time}  {details}"),
            ConnectionEventType.Disconnect => new StyledText("[-]", s_brightYellow)
                .Append($" {time}  {details}{Duration(item.DurationSeconds)}"),
            _ => new StyledText("[!]", s_brightRed).Append($" {time}  {details} FAILED"),
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
