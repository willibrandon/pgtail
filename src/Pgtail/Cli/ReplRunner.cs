using Hex1b;
using Hex1b.Widgets;
using System.Globalization;
using Pgtail.Commands;
using Pgtail.Repl;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Updates;

namespace Pgtail.Cli;

/// <summary>
/// Runs the interactive REPL on the real terminal.
/// </summary>
/// <remarks>
/// Between prompts the terminal goes to shell commands, streaming output, and clearing the screen.
/// </remarks>
internal static class ReplRunner
{
    /// <summary>
    /// Runs the REPL until the user leaves.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <param name="updates">Checks for a newer release at startup, or null.</param>
    /// <returns>The exit code.</returns>
    public static async Task<int> RunAsync(PgtailSession session, UpdateChecker? updates)
    {
        ArgumentNullException.ThrowIfNull(session);
        var history = new ReplHistory(session.Paths.HistoryFile);
        history.Load();
        session.Refresh();
        var host = new ReplHost(session, ReplCatalog.Catalog, history, Environment.CurrentDirectory);
        foreach (var warning in session.TakeWarnings())
        {
            host.StartupNotices.Add(new StyledText($"Warning: {warning}"));
        }

        if (updates is not null && UpdateChecker.ShouldCheck(session.Config, DateTime.UtcNow))
        {
            _ = CheckForUpdateAsync(session, updates, host);
        }

        while (true)
        {
            ReplRequest? request = null;
            await using (var terminal = Terminals.Builder()
                .WithHex1bFlow(async flow => request = await host.RunAsync(flow), Terminals.FlowOptions)
                .Build())
            {
                _ = await terminal.RunAsync();
            }

            switch (request)
            {
                case null or { Kind: ReplRequestKind.Exit }:
                    return 0;
                case { Kind: ReplRequestKind.ClearScreen }:
                    Console.Out.Write("\e[H\e[2J\e[3J");
                    Console.Out.Flush();
                    break;
                case { Kind: ReplRequestKind.Shell, Command: { } command }:
                    ShellRunner.Run(command, message => Console.Out.WriteLine(message));
                    break;
                case { Kind: ReplRequestKind.Stream, Stream: { } stream }:
                    await StreamAsync(stream);
                    break;
                case { Kind: ReplRequestKind.Screen, Screen: { } screen }:
                    await RunScreenAsync(screen);
                    break;
            }
        }
    }

    /// <summary>
    /// Writes streaming output to the terminal until Ctrl+C.
    /// </summary>
    /// <param name="stream">Writes the output until its token is cancelled.</param>
    /// <returns>A task that completes when streaming has stopped.</returns>
    public static async Task StreamAsync(Func<TextWriter, CancellationToken, Task> stream)
    {
        ArgumentNullException.ThrowIfNull(stream);
        using var cancellation = new CancellationTokenSource();
        ConsoleCancelEventHandler stop = (_, e) =>
        {
            e.Cancel = true;
            cancellation.Cancel();
        };

        Console.CancelKeyPress += stop;
        try
        {
            await stream(Console.Out, cancellation.Token);
            await Console.Out.FlushAsync(CancellationToken.None);
        }
        finally
        {
            Console.CancelKeyPress -= stop;
        }
    }

    /// <summary>
    /// Runs a full screen app on the terminal until it stops.
    /// </summary>
    /// <param name="screen">Sets up the app and returns its builder.</param>
    /// <returns>A task that completes when the app has stopped.</returns>
    public static async Task RunScreenAsync(Func<Hex1bApp, Hex1bAppOptions, Func<RootContext, Hex1bWidget>> screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        Hex1bAppOptions? options = null;
        await using var terminal = Terminals.Builder()
            .WithHex1bApp(configure => options = configure, app => screen(app, options!))
            .Build();
        _ = await terminal.RunAsync();
    }

    private static async Task CheckForUpdateAsync(PgtailSession session, UpdateChecker updates, ReplHost host)
    {
        if (await updates.FetchLatestAsync(CancellationToken.None) is not { } latest)
        {
            return;
        }

        if (updates.IsNewer(latest))
        {
            host.Post(updates.Notice(latest));
        }

        var now = DateTimeOffset.UtcNow.ToString("o", CultureInfo.InvariantCulture);
        _ = session.Store.Save("updates.last_check", now);
    }
}
