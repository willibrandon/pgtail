using Hex1b;
using Hex1b.Widgets;
using System.Globalization;
using System.Text;
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
/// Between prompts the terminal goes to shell commands, streaming output, clearing the screen, and full screen apps.
/// After clearing, the next prompt starts on the top row, and after a full screen app, which leaves the cursor where it
/// found it, on the row where the flow ended; otherwise the flow asks the terminal where the cursor is.
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

        // Between terminals the console is not in raw mode, so Ctrl+C there is a signal that would end the process;
        // the REPL keeps running and a stream, when one runs, stops.
        ConsoleCancelEventHandler keepRunning = (_, e) => e.Cancel = true;
        Console.CancelKeyPress += keepRunning;
        try
        {
            return await LoopAsync(host);
        }
        finally
        {
            Console.CancelKeyPress -= keepRunning;
        }
    }

    private static async Task<int> LoopAsync(ReplHost host)
    {
        int? resumeRow = null;
        while (true)
        {
            ReplRequest? request = null;
            var startRow = resumeRow;
            resumeRow = null;
            if (startRow is null)
            {
                Terminals.ForgetCursorPosition();
            }

            await using (var terminal = Terminals.Builder()
                .WithHex1bFlow(
                    async flow =>
                    {
                        request = await host.RunAsync(flow);
                        await Terminals.DrainOutputAsync();
                        Terminals.PlaceCursor(host.EndRow);
                    },
                    options =>
                    {
                        Terminals.FlowOptions(options);
                        if (startRow is { } row)
                        {
                            options.InitialCursorRow = row;
                            options.CursorRowProvider = () => row;
                        }
                    })
                .Build())
            {
                _ = await terminal.RunAsync();
            }

            Terminals.PlaceCursor(host.EndRow);
            await Terminals.ReleaseConsoleAsync();
            switch (request)
            {
                case null or { Kind: ReplRequestKind.Exit }:
                    return 0;
                case { Kind: ReplRequestKind.ClearScreen }:
                    Console.Out.Write("\e[H\e[2J\e[3J");
                    Console.Out.Flush();
                    resumeRow = 0;
                    break;
                case { Kind: ReplRequestKind.Shell, Command: { } command }:
                    ShellRunner.Run(command, message => Console.Out.WriteLine(message));
                    break;
                case { Kind: ReplRequestKind.Stream, Stream: { } stream }:
                    await StreamAsync(stream);
                    break;
                case { Kind: ReplRequestKind.Screen, Screen: { } screen }:
                    resumeRow = host.EndRow;
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

        // Streams flush after each batch of entries, so writing through a buffer saves a write to the terminal or pipe
        // for every line.
        await using var output = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false), 64 * 1024);
        try
        {
            await stream(output, cancellation.Token);
            await output.FlushAsync(CancellationToken.None);
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
        await using (var terminal = Terminals.Builder()
            .WithMouse()
            .WithHex1bApp(configure => options = configure, app => screen(app, options!))
            .Build())
        {
            _ = await terminal.RunAsync();
        }

        await Terminals.ReleaseConsoleAsync();
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
