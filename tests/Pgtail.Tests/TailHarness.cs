using Hex1b;
using Hex1b.Automation;
using Pgtail.Commands;
using Pgtail.Filtering;
using Pgtail.Sessions;
using Pgtail.Tail;
using Pgtail.Tailing;

namespace Pgtail.Tests;

/// <summary>
/// Runs tail mode on a log file in a headless Hex1b terminal for a test, as <c>pgtail tail --file</c> does.
/// </summary>
/// <remarks>
/// The session looks back a day, as <c>--since 1d</c> would, so the file's existing lines are read before new ones.
/// </remarks>
internal sealed class TailHarness : IAsyncDisposable
{
    private readonly Hex1bTerminal _terminal;
    private readonly TailScreen _screen;
    private readonly Task<int> _run;
    private readonly CancellationTokenSource _stop;

    private TailHarness(PgtailSession session, string logFile, string directory, int width, int height, CancellationToken cancellationToken)
    {
        Session = session;
        var request = new TailRequest(new TailSource(Files: [logFile]), logFile, Stream: false);
        var source = LogSources.Create(request, session, directory, () => Stream.Null);
        _screen = new TailScreen(session, request, source, directory);
        Hex1bAppOptions? options = null;
        _terminal = Hex1bTerminal.CreateBuilder()
            .WithHex1bApp(configure => options = configure, app => _screen.Configure(app, options!))
            .WithHeadless()
            .WithDimensions(width, height)
            .Build();
        _stop = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        _run = _terminal.RunAsync(_stop.Token);
        Automator = new Hex1bTerminalAutomator(_terminal, defaultTimeout: TimeSpan.FromSeconds(15));
    }

    /// <summary>
    /// The session.
    /// </summary>
    public PgtailSession Session { get; }

    /// <summary>
    /// Drives the terminal.
    /// </summary>
    public Hex1bTerminalAutomator Automator { get; }

    /// <summary>
    /// Whether tail mode has ended.
    /// </summary>
    public bool Stopped => _run.IsCompleted;

    /// <summary>
    /// Starts tail mode on a file, with the command input focused as it starts.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="logFile">The log file.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <param name="width">The terminal width.</param>
    /// <param name="height">The terminal height.</param>
    /// <returns>The harness, once the status bar shows.</returns>
    public static async Task<TailHarness> StartAsync(
        TestEnvironment environment,
        string logFile,
        CancellationToken cancellationToken,
        int width = 100,
        int height = 24)
    {
        var session = environment.CreateSession();
        session.Time = new TimeFilter(since: DateTime.UtcNow.AddDays(-1), originalInput: "1d");
        var harness = new TailHarness(session, logFile, environment.Root, width, height, cancellationToken);
        await harness.Automator.WaitUntilTextAsync("FOLLOW");
        return harness;
    }

    /// <summary>
    /// The status bar: the screen's last row.
    /// </summary>
    /// <param name="screen">The screen.</param>
    /// <returns>The row, trimmed.</returns>
    public static string Status(IHex1bTerminalRegion screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        return screen.GetLineTrimmed(screen.Height - 1).TrimStart();
    }

    /// <summary>
    /// The command input: the row above the status bar's rule, starting with the <c>tail&gt;</c> prompt.
    /// </summary>
    /// <param name="screen">The screen.</param>
    /// <returns>The row, trimmed.</returns>
    public static string Input(IHex1bTerminalRegion screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        return screen.GetLineTrimmed(screen.Height - 3);
    }

    /// <summary>
    /// The log's rows, between the header's rule and the input's rule, trimmed.
    /// </summary>
    /// <param name="screen">The screen.</param>
    /// <returns>The rows.</returns>
    public static List<string> LogRows(IHex1bTerminalRegion screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        return [.. Enumerable.Range(2, screen.Height - 6).Select(row => screen.GetLineTrimmed(row).TrimEnd('│', '▉').TrimEnd())];
    }

    /// <summary>
    /// Types a command into the input and runs it, from whatever the screen was doing.
    /// </summary>
    /// <remarks>
    /// In the input, Escape closes the last command's output and then empties the input and focuses the log; on the log
    /// it clears the selection. Two of them leave the log focused either way, so <c>/</c> then focuses the input.
    /// </remarks>
    /// <param name="command">The command.</param>
    /// <param name="cancellationToken">Cancels the typing.</param>
    /// <returns>A task that completes when the keys were sent.</returns>
    public async Task RunAsync(string command, CancellationToken cancellationToken)
    {
        await Automator.EscapeAsync(cancellationToken);
        await Automator.EscapeAsync(cancellationToken);
        await Automator.TypeAsync("/", cancellationToken);
        await Automator.WaitUntilAsync(screen => Input(screen) == "tail>", description: "an empty command input");
        await Automator.TypeAsync(command, cancellationToken);
        await Automator.WaitUntilAsync(screen => Input(screen)
            .StartsWith($"tail> {command}", StringComparison.Ordinal), description: "the command typed");
        await Automator.EnterAsync(cancellationToken);
    }

    /// <summary>
    /// Stops tail mode, unless it already ended, and waits for the terminal and the source.
    /// </summary>
    /// <returns>A task that completes when everything has stopped.</returns>
    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync();
        try
        {
            _ = await _run.WaitAsync(TimeSpan.FromSeconds(15));
        }
        catch (OperationCanceledException)
        {
            // The test ended without leaving tail mode.
        }

        await _terminal.DisposeAsync();
        await _screen.EndAsync();
        _stop.Dispose();
    }
}
