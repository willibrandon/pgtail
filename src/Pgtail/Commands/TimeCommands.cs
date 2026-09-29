using System.Globalization;
using Pgtail.Filtering;
using Pgtail.Parsing;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// Time filters: <c>since</c>, <c>until</c>, and <c>between</c>, in the REPL and in tail mode.
/// </summary>
internal static class TimeCommands
{
    private static readonly string[] Formats =
    [
        "Time formats:",
        "  5m, 30s, 2h, 1d       Relative (from now)",
        "  14:30, 14:30:45       Time today",
        "  2024-01-15T14:30      ISO 8601 datetime",
    ];

    /// <summary>
    /// The REPL's <c>since</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Since(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            output.Line(session.Time.IsActive ? $"Time filter: {session.Time.FormatDescription()}" : "No time filter active");
            output.Line();
            output.Line("Usage: since <time>     Show logs since time");
            output.Line("       since clear      Remove time filter");
            output.Line();
            output.Lines(Formats);
            return Task.CompletedTask;
        }

        if (args[0].Equals("clear", StringComparison.OrdinalIgnoreCase))
        {
            session.Time = TimeFilter.Empty;
            output.Line("Time filter cleared");
            return Task.CompletedTask;
        }

        if (!TryParse(args[0], out var since, out var error))
        {
            output.Line($"Error: {error}");
            return Task.CompletedTask;
        }

        if (TimeParser.IsFuture(since))
        {
            output.Line($"Warning: {args[0]} is in the future, no entries will match yet");
        }

        session.Time = new TimeFilter(since: since, originalInput: args[0]);
        output.Line($"Showing logs {session.Time.FormatDescription()}");
        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL's <c>until</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Until(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            ShowActive(invocation);
            output.Line("Usage: until <time>");
            output.Line();
            output.Lines(Formats);
            output.Line();
            output.Line("Example: until 15:00");
            output.Line();
            output.Line("Note: until disables live tailing (no new entries will appear)");
            return Task.CompletedTask;
        }

        if (args[0].Equals("clear", StringComparison.OrdinalIgnoreCase))
        {
            session.Time = TimeFilter.Empty;
            output.Line("Time filter cleared");
            return Task.CompletedTask;
        }

        if (!TryParse(args[0], out var until, out var error))
        {
            output.Line($"Error: {error}");
            return Task.CompletedTask;
        }

        session.Time = new TimeFilter(until: until, originalInput: args[0]);
        output.Line($"Showing logs {session.Time.FormatDescription()}");
        output.Line("Note: Live tailing disabled (until sets an upper bound)");
        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL's <c>between</c> command, which accepts <c>between 14:30 and 15:00</c> too.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Between(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = WithoutAnd(invocation.Args);
        if (args.Count < 2)
        {
            ShowActive(invocation);
            output.Line("Usage: between <start> <end>");
            output.Line();
            output.Lines(Formats);
            output.Line();
            output.Line("Example: between 14:30 15:00");
            return Task.CompletedTask;
        }

        if (!TryParse(args[0], out var start, out var startError))
        {
            output.Line($"Error parsing start time: {startError}");
            return Task.CompletedTask;
        }

        if (!TryParse(args[1], out var end, out var endError))
        {
            output.Line($"Error parsing end time: {endError}");
            return Task.CompletedTask;
        }

        if (LogTimestamps.ToUtc(start) >= LogTimestamps.ToUtc(end))
        {
            output.Line("Error: Start time must be before end time");
            output.Line($"  Start: {LogTimestamps.ToLocal(start).ToString("HH:mm:ss", CultureInfo.InvariantCulture)}");
            output.Line($"  End:   {LogTimestamps.ToLocal(end).ToString("HH:mm:ss", CultureInfo.InvariantCulture)}");
            return Task.CompletedTask;
        }

        session.Time = new TimeFilter(start, end, $"{args[0]} {args[1]}");
        output.Line($"Showing logs {session.Time.FormatDescription()}");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Tail mode's <c>since</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailSince(CommandInvocation invocation) => TailSet(invocation, until: false);

    /// <summary>
    /// Tail mode's <c>until</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailUntil(CommandInvocation invocation) => TailSet(invocation, until: true);

    /// <summary>
    /// Tail mode's <c>between</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailBetween(CommandInvocation invocation)
    {
        var args = WithoutAnd(invocation.Args);
        if (args.Count < 2)
        {
            invocation.Output.Markup("[bold red]✗[/] Usage: between <start> <end>");
            return Task.CompletedTask;
        }

        if (!TryParse(args[0], out var start, out var startError))
        {
            invocation.Output.Markup($"[bold red]✗[/] Start time: {Markup.Escape(startError)}");
            return Task.CompletedTask;
        }

        if (!TryParse(args[1], out var end, out var endError))
        {
            invocation.Output.Markup($"[bold red]✗[/] End time: {Markup.Escape(endError)}");
            return Task.CompletedTask;
        }

        if (LogTimestamps.ToUtc(start) >= LogTimestamps.ToUtc(end))
        {
            invocation.Output.Markup("[bold red]✗[/] Start time must be before end time");
            return Task.CompletedTask;
        }

        Apply(invocation, new TimeFilter(start, end, $"{args[0]} {args[1]}"));
        return Task.CompletedTask;
    }

    private static Task TailSet(CommandInvocation invocation, bool until)
    {
        var args = invocation.Args;
        if (args.Count == 0)
        {
            invocation.Output.Markup($"[bold red]✗[/] Usage: {(until ? "until" : "since")} <time>");
            return Task.CompletedTask;
        }

        if (args[0].Equals("clear", StringComparison.OrdinalIgnoreCase))
        {
            Apply(invocation, TimeFilter.Empty);
            return Task.CompletedTask;
        }

        if (!TryParse(args[0], out var time, out var error))
        {
            invocation.Output.Markup($"[bold red]✗[/] {Markup.Escape(error)}");
            return Task.CompletedTask;
        }

        var filter = until ? new TimeFilter(until: time, originalInput: args[0]) : new TimeFilter(since: time, originalInput: args[0]);
        Apply(invocation, filter);
        return Task.CompletedTask;
    }

    private static void Apply(CommandInvocation invocation, TimeFilter filter)
    {
        var host = (ITailHost)invocation.Host;
        invocation.Session.Time = filter;
        host.RefreshStatus();
        host.Rebuild();
    }

    private static void ShowActive(CommandInvocation invocation)
    {
        if (invocation.Session.Time.IsActive)
        {
            invocation.Output.Line($"Time filter: {invocation.Session.Time.FormatDescription()}");
            invocation.Output.Line();
        }
    }

    private static List<string> WithoutAnd(IReadOnlyList<string> args) =>
        args.Count >= 2 && args[1].Equals("and", StringComparison.OrdinalIgnoreCase) ? [args[0], .. args.Skip(2)] : [.. args];

    private static bool TryParse(string text, out DateTime time, out string error)
    {
        try
        {
            time = TimeParser.Parse(text);
            error = "";
            return true;
        }
        catch (FormatException exception)
        {
            time = default;
            error = exception.Message;
            return false;
        }
    }
}
