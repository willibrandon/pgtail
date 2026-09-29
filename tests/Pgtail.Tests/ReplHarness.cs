using System.Threading.Channels;
using Hex1b.Widgets;
using Hex1b;
using Hex1b.Automation;
using Pgtail.Commands;
using Pgtail.Repl;
using Pgtail.Sessions;

namespace Pgtail.Tests;

/// <summary>
/// Runs the REPL in a headless Hex1b terminal for a test.
/// </summary>
internal sealed class ReplHarness : IAsyncDisposable
{
    private readonly Hex1bTerminal _terminal;
    private readonly Task<int> _run;
    private readonly CancellationTokenSource _stop;
    private readonly Channel<Hex1bTerminalAutomator> _screens = Channel.CreateUnbounded<Hex1bTerminalAutomator>();
    private readonly Channel<ReplRequest> _requests = Channel.CreateUnbounded<ReplRequest>();
    private volatile bool _exited;

    private ReplHarness(
        TestEnvironment environment,
        PgtailSession session,
        int width,
        int height,
        CancellationToken cancellationToken)
    {
        Environment = environment;
        Session = session;
        var history = new ReplHistory(session.Paths.HistoryFile);
        history.Load();
        Host = new ReplHost(session, ReplCatalog.Catalog, history, environment.Root);
        _terminal = Hex1bTerminal.CreateBuilder()
            .WithHex1bFlow(async flow =>
            {
                while (true)
                {
                    var request = await Host.RunAsync(flow);
                    _exited = request.Kind == ReplRequestKind.Exit;
                    await _requests.Writer.WriteAsync(request, cancellationToken);
                    switch (request)
                    {
                        case { Kind: ReplRequestKind.Exit }:
                            return;
                        case { Kind: ReplRequestKind.Screen, Screen: { } screen }:
                            await RunScreenAsync(screen, width, height, cancellationToken);
                            break;
                    }
                }
            }, Cli.Terminals.FlowOptions)
            .WithHeadless()
            .WithDimensions(width, height)
            .Build();
        _stop = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        _run = _terminal.RunAsync(_stop.Token);
        Automator = new Hex1bTerminalAutomator(_terminal, defaultTimeout: TimeSpan.FromSeconds(15));
    }

    /// <summary>
    /// The test's environment.
    /// </summary>
    public TestEnvironment Environment { get; }

    /// <summary>
    /// The session.
    /// </summary>
    public PgtailSession Session { get; }

    /// <summary>
    /// The REPL.
    /// </summary>
    public ReplHost Host { get; }

    /// <summary>
    /// Drives the terminal.
    /// </summary>
    public Hex1bTerminalAutomator Automator { get; }

    /// <summary>
    /// Starts the REPL.
    /// </summary>
    /// <param name="environment">The test's environment.</param>
    /// <param name="cancellationToken">Stops the terminal.</param>
    /// <param name="width">The terminal width.</param>
    /// <param name="height">The terminal height.</param>
    /// <returns>The harness, once the first prompt shows.</returns>
    public static async Task<ReplHarness> StartAsync(
        TestEnvironment environment,
        CancellationToken cancellationToken,
        int width = 100,
        int height = 30)
    {
        var session = environment.CreateSession();
        session.Refresh();
        var harness = new ReplHarness(environment, session, width, height, cancellationToken);
        await harness.Automator.WaitUntilTextAsync("pgtail>");
        return harness;
    }

    /// <summary>
    /// Waits for a full screen app, such as tail mode, to start, and returns what drives it.
    /// </summary>
    /// <returns>The screen's automator.</returns>
    public async Task<Hex1bTerminalAutomator> WaitForScreenAsync()
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        return await _screens.Reader.ReadAsync(timeout.Token);
    }

    /// <summary>
    /// Waits for the REPL to ask for the real terminal, skipping other kinds of request.
    /// </summary>
    /// <param name="kind">The kind of request.</param>
    /// <returns>The request.</returns>
    public async Task<ReplRequest> WaitForRequestAsync(ReplRequestKind kind)
    {
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        while (true)
        {
            var request = await _requests.Reader.ReadAsync(timeout.Token);
            if (request.Kind == kind)
            {
                return request;
            }
        }
    }

    /// <summary>
    /// Types a command and presses Enter.
    /// </summary>
    /// <param name="command">The command.</param>
    /// <param name="cancellationToken">Cancels the typing.</param>
    /// <returns>A task that completes when the keys were sent.</returns>
    public async Task RunAsync(string command, CancellationToken cancellationToken)
    {
        await Automator.TypeAsync(command, ct: cancellationToken);
        await Automator.EnterAsync(ct: cancellationToken);
    }

    /// <summary>
    /// The prompt line: the last row above the toolbar that has text, when no completion menu shows.
    /// </summary>
    /// <param name="screen">The screen.</param>
    /// <returns>The row, trimmed.</returns>
    public static string PromptLine(IHex1bTerminalRegion screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        for (var row = screen.Height - 2; row >= 0; row--)
        {
            if (screen.GetLineTrimmed(row) is { Length: > 0 } line)
            {
                return line;
            }
        }

        return "";
    }

    /// <summary>
    /// The toolbar: the screen's last row.
    /// </summary>
    /// <param name="screen">The screen.</param>
    /// <returns>The row, trimmed.</returns>
    public static string Toolbar(IHex1bTerminalRegion screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        return screen.GetLineTrimmed(screen.Height - 1);
    }

    /// <summary>
    /// The screen's text, one string per row.
    /// </summary>
    /// <returns>The rows.</returns>
    public IReadOnlyList<string> Screen()
    {
        using var snapshot = _terminal.CreateSnapshot();
        return [.. Enumerable.Range(0, snapshot.Height).Select(snapshot.GetLineTrimmed)];
    }

    private async Task RunScreenAsync(
        Func<Hex1bApp, Hex1bAppOptions, Func<RootContext, Hex1bWidget>> screen,
        int width,
        int height,
        CancellationToken cancellationToken)
    {
        Hex1bAppOptions? options = null;
        await using var terminal = Hex1bTerminal.CreateBuilder()
            .WithHex1bApp(configure => options = configure, app => screen(app, options!))
            .WithHeadless()
            .WithDimensions(width, height)
            .Build();
        var run = terminal.RunAsync(cancellationToken);
        await _screens.Writer.WriteAsync(new Hex1bTerminalAutomator(terminal, defaultTimeout: TimeSpan.FromSeconds(15)), cancellationToken);
        _ = await run;
    }

    /// <summary>
    /// Stops the terminal, unless the REPL already ended, and waits for it.
    /// </summary>
    /// <returns>A task that completes when the terminal has stopped.</returns>
    public async ValueTask DisposeAsync()
    {
        if (!_exited)
        {
            await _stop.CancelAsync();
        }

        try
        {
            _ = await _run.WaitAsync(TimeSpan.FromSeconds(15));
        }
        catch (OperationCanceledException) when (_stop.IsCancellationRequested)
        {
            // The test ended without leaving the REPL.
        }

        await _terminal.DisposeAsync();
        _stop.Dispose();
    }
}
