using Hex1b;
using Hex1b.Input;
using Hex1b.Nodes;
using Hex1b.Widgets;
using Pgtail.Detection;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <content>
/// The screen's widgets, keys, and lifecycle.
/// </content>
internal sealed partial class TailScreen
{
    private static readonly TextStyle PanelText = StyleParser.Parse("fg:#c0c0c0 bg:#262626 bold");
    private static readonly TextStyle HeaderText = StyleParser.Parse("fg:#8a8a8a bg:#262626");
    private static readonly TextStyle Separator = StyleParser.Parse("fg:#5f5f5f");
    private CancellationTokenSource? _watch;
    private Dictionary<char, Action<InputBindingActionContext>> _logKeys = [];

    /// <summary>
    /// Sets up the app and returns the screen's builder.
    /// </summary>
    /// <remarks>
    /// Starts the source and a watcher that wakes the app when entries arrive; <see cref="EndAsync"/> stops both.
    /// </remarks>
    /// <param name="app">The app.</param>
    /// <param name="options">The app's options.</param>
    /// <returns>The widget builder.</returns>
    public Func<RootContext, Hex1bWidget> Configure(Hex1bApp app, Hex1bAppOptions options)
    {
        ArgumentNullException.ThrowIfNull(app);
        ArgumentNullException.ThrowIfNull(options);
        _app = app;
        options.EnableDefaultCtrlCExit = false;
        options.EnableMouse = true;
        Input.Load();
        Input.FocusLog = context => context.FocusWhere(IsLog);
        _logKeys = new Dictionary<char, Action<InputBindingActionContext>>
        {
            ['q'] = _ => Stop(),
            ['?'] = _ => HelpVisible = true,
            ['/'] = context => context.FocusWhere(IsInput),
        };

        CheckInitialAccess();
        _source.Start();
        _watch = new CancellationTokenSource();
        _ = WatchAsync(app, _watch.Token);
        app.RequestFocus(IsInput);
        return Build;
    }

    /// <summary>
    /// Stops the watcher and the source once the app has stopped.
    /// </summary>
    /// <returns>A task that completes when the source has stopped.</returns>
    public async Task EndAsync()
    {
        if (_watch is { } watch)
        {
            await watch.CancelAsync();
            watch.Dispose();
            _watch = null;
        }

        await _source.DisposeAsync();
    }

    private async Task WatchAsync(Hex1bApp app, CancellationToken cancellationToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(50));
        var unavailable = false;
        var denied = false;
        try
        {
            while (await timer.WaitForNextTickAsync(cancellationToken))
            {
                if (_source.Events.TryPeek(out _) || _source.IsUnavailable != unavailable || _source.IsPermissionDenied != denied)
                {
                    unavailable = _source.IsUnavailable;
                    denied = _source.IsPermissionDenied;
                    app.Invalidate();
                }
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // The screen closed.
        }
    }

    private void CheckInitialAccess()
    {
        if (_request.Source.Stdin || _request.LogPath is not { } path || (_request.Source.Files?.Count ?? 1) > 1)
        {
            return;
        }

        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        }
        catch (UnauthorizedAccessException)
        {
            var lines = new List<StyledText>
            {
                Markup.Parse("[bold yellow]Warning:[/] Cannot read log file due to permissions"),
                Markup.Parse($"[dim]File:[/] {Markup.Escape(path)}"),
                new(),
            };

            lines.AddRange(PermissionAdvice.LogPermission(markup: true).Select(Markup.Parse));
            WriteLines(lines);
            Status.FilePermissionDenied = true;
            Status.FileUnavailable = true;
        }
        catch (IOException)
        {
            // A missing file is reported by the source once it looks.
        }
    }

    private Hex1bWidget Build(RootContext context)
    {
        if (!_ended)
        {
            Pump();
        }

        Input.UpdateHints();
        var main = context.VStack(v =>
        [
            Bar(v, TailStatus.FormatHeader(), HeaderText),
            Rule(v),
            _view.Build(v, _logKeys, bindings => BindScreenKeys(bindings, logFocused: true)).Fill(),
            Rule(v),
            v.Editor(Input.Editor)
                .Decorations(Input.Hints)
                .InputBindings(bindings =>
                {
                    Input.Bind(bindings);
                    BindScreenKeys(bindings, logFocused: false);
                })
                .FixedHeight(1),
            Rule(v),
            Bar(v, Status.FormatStatus(), PanelText),
        ]);
        return HelpVisible ? context.ZStack(z => [main, TailHelpOverlay.Build(z, CloseHelp)]) : main;
    }

    private void BindScreenKeys(InputBindingsBuilder bindings, bool logFocused)
    {
        bindings.Remove(Hex1bKey.Tab);
        bindings.Key(Hex1bKey.Tab).Action(context => context.FocusWhere(logFocused ? IsInput : IsLog),
            "Switch between the log and the command input");
        bindings.Ctrl().Key(Hex1bKey.C).Action(_ =>
        {
            if (!_view.CopySelection())
            {
                Stop();
            }
        }, "Copy the selection, or leave tail mode");
    }

    private void CloseHelp(InputBindingActionContext context)
    {
        HelpVisible = false;
        _ = context.FocusWhere(IsLog);
    }

    private static bool IsLog(Hex1bNode node) => node is InteractableNode { Child: SurfaceNode };

    private bool IsInput(Hex1bNode node) => node is EditorNode editor && editor.State == Input.Editor;

    private SurfaceWidget Bar<TParent>(WidgetContext<TParent> context, StyledText text, TextStyle panel)
        where TParent : Hex1bWidget
    {
        var row = StyledTextFolder.Fold(new StyledText().Append(text), 0)[0];
        return context.Surface(s =>
        [
            s.Layer(surface =>
            {
                StyledBlock.DrawRow(surface, 0, 0, [new StyledSpan(new string(' ', surface.Width), panel)], Session.ColorEnabled);
                StyledBlock.DrawRow(surface, 0, 0, [.. row.Select(span => span with { Style = panel.Then(span.Style) })],
                    Session.ColorEnabled);
            }),
        ]).Height(Hex1b.Layout.SizeHint.Fixed(1));
    }

    private SurfaceWidget Rule<TParent>(WidgetContext<TParent> context)
        where TParent : Hex1bWidget => context.Surface(s =>
        [
            s.Layer(surface => StyledBlock.DrawRow(surface, 0, 0, [new StyledSpan(new string('─', surface.Width), Separator)],
                Session.ColorEnabled)),
        ]).Height(Hex1b.Layout.SizeHint.Fixed(1));
}
