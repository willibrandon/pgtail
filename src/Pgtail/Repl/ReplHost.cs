using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using Hex1b;
using Hex1b.Flow;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Commands;
using Pgtail.Rendering;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Repl;

/// <summary>
/// Runs the interactive REPL as a Hex1b flow: the banner, then a prompt, the command's output, and the next prompt.
/// </summary>
/// <remarks>
/// Output scrolls into the terminal's own scrollback, as it did with prompt_toolkit. When a command needs the real
/// terminal (a shell command, clearing the screen, streaming output, or leaving), the flow ends with a
/// <see cref="ReplRequest"/>; the caller services it and runs the flow again to continue the session.
/// </remarks>
internal sealed partial class ReplHost : IReplHost
{
    private readonly CommandCatalog _catalog;
    private readonly StrongBox<bool> _shellMode = new(false);
    private readonly PromptState _prompt;
    private readonly ConcurrentQueue<StyledText> _posted = new();
    private Hex1bFlowContext? _flow;
    private ReplRequest? _pending;
    private bool _bannerShown;
    private Task? _suspended;
    private ReplRequest? _served;
    private TaskCompletionSource<ReplRequest> _screenRequests = NewScreenRequests();

    /// <summary>
    /// Creates the host.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <param name="catalog">The commands.</param>
    /// <param name="history">The command history.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    public ReplHost(PgtailSession session, CommandCatalog catalog, ReplHistory history, string currentDirectory)
    {
        ArgumentNullException.ThrowIfNull(session);
        ArgumentNullException.ThrowIfNull(catalog);
        ArgumentNullException.ThrowIfNull(history);
        Session = session;
        _catalog = catalog;
        _prompt = new PromptState(history);
        CurrentDirectory = currentDirectory;
    }

    /// <inheritdoc/>
    public PgtailSession Session { get; }

    /// <inheritdoc/>
    public CommandOutput Output { get; } = new();

    /// <inheritdoc/>
    public string CurrentDirectory { get; }

    /// <summary>
    /// The lines shown before the first prompt, after the banner.
    /// </summary>
    public List<StyledText> StartupNotices { get; } = [];

    /// <summary>
    /// The screen row the cursor was on when the flow last ended, below everything it printed.
    /// </summary>
    public int EndRow { get; private set; }

    /// <summary>
    /// Runs prompts until a command needs the real terminal.
    /// </summary>
    /// <param name="flow">The flow.</param>
    /// <returns>What the terminal is needed for.</returns>
    public async Task<ReplRequest> RunAsync(Hex1bFlowContext flow)
    {
        ArgumentNullException.ThrowIfNull(flow);
        _flow = flow;
        try
        {
            if (!_bannerShown)
            {
                _bannerShown = true;
                ShowBanner();
            }

            if (_suspended is { } suspended)
            {
                _suspended = null;
                _served?.Done.TrySetResult();
                _served = null;
                if (await ContinueAsync(suspended) is { } request)
                {
                    return request;
                }
            }

            await FlushAsync();
            while (true)
            {
                var result = await PromptAsync();
                Task execution;
                switch (result.Outcome)
                {
                    case PromptOutcome.Interrupted:
                        Output.Line();
                        execution = Task.CompletedTask;
                        break;
                    case PromptOutcome.EndOfInput:
                        Output.Line();
                        Leave();
                        execution = Task.CompletedTask;
                        break;
                    case PromptOutcome.ClearScreen:
                        _pending = new ReplRequest(ReplRequestKind.ClearScreen);
                        execution = Task.CompletedTask;
                        break;
                    default:
                        execution = ExecuteAsync(result);
                        break;
                }

                if (await ContinueAsync(execution) is { } request)
                {
                    return request;
                }
            }
        }
        finally
        {
            EndRow = flow.TerminalHeight - flow.AvailableHeight;
            _flow = null;
        }
    }

    /// <summary>
    /// Asks for the real terminal to run a full screen app, and waits until the app has stopped.
    /// </summary>
    /// <remarks>
    /// The prompt loop returns the request to whoever runs the REPL, which runs the app and then the loop again; the
    /// command that asked continues from here once the loop is running again.
    /// </remarks>
    /// <param name="screen">Sets up the app and returns its builder.</param>
    /// <returns>A task that completes when the app has stopped.</returns>
    public async Task RunScreenAsync(Func<Hex1bApp, Hex1bAppOptions, Func<RootContext, Hex1bWidget>> screen)
    {
        ArgumentNullException.ThrowIfNull(screen);
        await FlushAsync();
        var request = new ReplRequest(ReplRequestKind.Screen) { Screen = screen };
        _screenRequests.TrySetResult(request);
        await request.Done.Task;
    }

    private async Task<ReplRequest?> ContinueAsync(Task execution)
    {
        var requested = _screenRequests.Task;
        if (await Task.WhenAny(execution, requested) != execution)
        {
            _suspended = execution;
            _screenRequests = NewScreenRequests();
            _served = await requested;
            return _served;
        }

        await execution;
        await FlushAsync();
        if (_pending is { } request)
        {
            _pending = null;
            return request;
        }

        return null;
    }

    private static TaskCompletionSource<ReplRequest> NewScreenRequests() => new(TaskCreationOptions.RunContinuationsAsynchronously);

    /// <summary>
    /// Runs one line as the REPL would, for a submitted prompt.
    /// </summary>
    /// <param name="result">The prompt's result.</param>
    /// <returns>A task that completes when the command has run.</returns>
    public async Task ExecuteAsync(PromptResult result)
    {
        ArgumentNullException.ThrowIfNull(result);
        var line = result.Text.Trim();
        if (line.Length == 0)
        {
            _shellMode.Value = false;
            return;
        }

        if (result.Shell)
        {
            _shellMode.Value = false;
            RunShell(line);
            return;
        }

        if (line.StartsWith('!'))
        {
            var command = line[1..].Trim();
            if (command.Length > 0)
            {
                RunShell(command);
            }
            else
            {
                _shellMode.Value = true;
            }

            return;
        }

        var tokens = CommandLineSplitter.Split(line);
        var name = tokens[0].Text;
        if (_catalog.Find(name) is not { } info)
        {
            Output.Line($"Unknown command: {name.ToLowerInvariant()}");
            Output.Line("Type 'help' for available commands.");
            return;
        }

        await info.Handler(new CommandInvocation(info, name, line, [.. tokens.Skip(1)], this));
    }

    /// <summary>
    /// Shows any waiting output as frozen lines above the next prompt.
    /// </summary>
    /// <returns>A task that completes when the output has been drawn.</returns>
    public async Task FlushAsync()
    {
        var flow = Flow;
        while (_posted.TryDequeue(out var notice))
        {
            Output.Line(notice);
        }

        if (!Output.HasLines)
        {
            return;
        }

        // A row that fills the last column would lose that column when the line is erased to its end.
        var width = FrozenWidth(flow);
        var rows = StyledBlock.Fold(Output.Take(), width);
        var chunk = Math.Max(1, flow.TerminalHeight - 1);
        for (var start = 0; start < rows.Count; start += chunk)
        {
            var slice = rows.GetRange(start, Math.Min(chunk, rows.Count - start));
            await flow.ShowAsync(ctx => StyledBlock.BuildRows(ctx, slice, width, Session.ColorEnabled));
        }
    }

    /// <summary>
    /// Queues a line from another thread, such as the update notice, to show before the next prompt.
    /// </summary>
    /// <param name="line">The line.</param>
    public void Post(StyledText line) => _posted.Enqueue(line);

    /// <inheritdoc/>
    public void Exit() => Leave();

    /// <inheritdoc/>
    public void ClearScreen() => _pending = new ReplRequest(ReplRequestKind.ClearScreen);

    /// <inheritdoc/>
    public void RunShell(string command)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);
        _pending = new ReplRequest(ReplRequestKind.Shell) { Command = command };
    }

    /// <inheritdoc/>
    public async Task<bool> ConfirmAsync(string question)
    {
        ArgumentNullException.ThrowIfNull(question);
        await FlushAsync();
        var flow = Flow;
        var answer = new TextBoxState();
        var label = new StyledText(question);
        var width = FrozenWidth(flow);
        var step = flow.Step(ctx => ctx.HStack(h =>
            [
                StyledBlock.Build(h, [label], Math.Max(1, DisplayWidth.GetStringWidth(question)), Session.ColorEnabled),
                h.TextBox().State(answer).OnSubmit(_ => ctx.Step.Complete(y => StyledBlock.Build(
                    y, [new StyledText(question + answer.Text)], width, Session.ColorEnabled))),
            ]).InputBindings(b => b.Ctrl().Key(Hex1bKey.C).Action(_ =>
            {
                answer.Text = "";
                ctx.Step.Complete(y => StyledBlock.Build(y, [label], width, Session.ColorEnabled));
            }, "Answer no")),
            options => options.MaxHeight = 1);
        await step.WaitForCompletionAsync(flow.CancellationToken);
        return answer.Text.Trim().ToLowerInvariant() is "y" or "yes";
    }

    /// <inheritdoc/>
    public async Task LiveAsync(Func<IReadOnlyList<StyledText>> render, TimeSpan interval)
    {
        ArgumentNullException.ThrowIfNull(render);
        await FlushAsync();
        var flow = Flow;
        var width = FrozenWidth(flow);
        var height = Math.Max(1, flow.TerminalHeight - 1);
        var stopped = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var step = flow.Step(ctx => StyledBlock.BuildRows(ctx, Rows(), width, Session.ColorEnabled)
            .InputBindings(b =>
            {
                b.Ctrl().Key(Hex1bKey.C).Action(_ => stopped.TrySetResult(), "Stop");
                b.Key(Hex1bKey.Q).Action(_ => stopped.TrySetResult(), "Stop");
            }), options => options.MaxHeight = height);

        using var timer = new PeriodicTimer(interval);
        while (!stopped.Task.IsCompleted)
        {
            var tick = timer.WaitForNextTickAsync(flow.CancellationToken).AsTask();
            _ = await Task.WhenAny(tick, stopped.Task);
            step.Invalidate();
        }

        await step.CompleteAsync(y => StyledBlock.BuildRows(y, Rows(), width, Session.ColorEnabled));

        List<List<StyledSpan>> Rows()
        {
            var rows = StyledBlock.Fold(render(), width);
            return rows.Count > height ? rows.GetRange(0, height) : rows;
        }
    }

    private Hex1bFlowContext Flow => _flow ?? throw new InvalidOperationException("The REPL flow is not running.");

    /// <summary>
    /// The width that lines left in the scrollback are folded to.
    /// </summary>
    /// <remarks>
    /// One column short of the terminal, since erasing to the end of a full row can drop its last character.
    /// </remarks>
    /// <param name="flow">The flow.</param>
    /// <returns>The width.</returns>
    private static int FrozenWidth(Hex1bFlowContext flow) => Math.Max(1, flow.TerminalWidth - 1);

    private void ShowBanner()
    {
        var banner = new List<StyledText>
        {
            new("pgtail - PostgreSQL log tailer"),
            new(),
        };

        banner.AddRange(StartupNotices);
        banner.Add(new StyledText(Session.Instances.Count switch
        {
            0 => "No PostgreSQL instances found. Use 'refresh' to scan again.",
            1 => "Found 1 PostgreSQL instance. Type 'list' to see details.",
            var count => $"Found {count} PostgreSQL instances. Type 'list' to see details.",
        }));

        banner.Add(new StyledText("Type 'help' for available commands, 'quit' to exit."));
        banner.Add(new StyledText());
        foreach (var line in banner)
        {
            Output.Line(line);
        }
    }

    private void Leave()
    {
        if (IsStreaming)
        {
            StopStreaming();
        }

        Output.Line("Goodbye!");
        _pending = new ReplRequest(ReplRequestKind.Exit);
    }

    private async Task<PromptResult> PromptAsync()
    {
        var flow = Flow;
        var controller = new PromptController(_prompt, _catalog, this, _shellMode);
        var completed = new TaskCompletionSource<PromptResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        var height = Math.Min(flow.TerminalHeight, Math.Max(flow.AvailableHeight, PromptState.MenuRows + 2));
        var width = Math.Max(1, flow.TerminalWidth);
        var step = flow.Step(
            ctx =>
            {
                controller.Changed = ctx.Step.Invalidate;
                controller.Ended = result =>
                {
                    var tombstone = PromptLabel(result.Shell).Append(result.Text);
                    ctx.Step.Complete(y => StyledBlock.Build(y, [tombstone], FrozenWidth(flow), Session.ColorEnabled));
                    _ = completed.TrySetResult(result);
                };

                return new ReplPromptView(controller, PromptLabel(_shellMode.Value), ReplToolbar.Build(Session, _shellMode.Value),
                    width, height, Session.ColorEnabled);
            },
            options => options.MaxHeight = height);
        step.RequestFocus(node => node is EditorNode);
        await step.WaitForCompletionAsync(flow.CancellationToken);
        var result = await completed.Task;
        if (result.Outcome != PromptOutcome.ClearScreen)
        {
            if (result.Outcome == PromptOutcome.Submitted)
            {
                _prompt.History.Add(result.Shell ? "!" + result.Text.Trim() : result.Text.Trim());
            }

            _prompt.Reset();
        }

        return result;
    }

    private StyledText PromptLabel(bool shell)
    {
        if (shell)
        {
            return Markup.Parse("[#ff6688]![/] ");
        }

        return StreamLabel is { } label
            ? Markup.Parse($"[#ffaa00]paused[/] [#00aaaa]{Markup.Escape($"[{label}]")}[/][#666666]>[/] ")
            : Markup.Parse("[#00aa00]pgtail[/][#666666]>[/] ");
    }
}
