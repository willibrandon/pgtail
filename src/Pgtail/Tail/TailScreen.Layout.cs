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
    private const string Prompt = "tail> ";
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
            ['?'] = _ =>
            {
                _help.Open();
                HelpVisible = true;
            },
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

            lines.AddRange(PermissionAdvice.LogPermission(path).Select(Markup.Parse));
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

        var resultRows = ResultRows();
        var main = context.VStack(v =>
        [
            Bar(v, TailStatus.FormatHeader(), HeaderText),
            Rule(v),
            _view.Build(v, _logKeys, TypeCommand, bindings => BindScreenKeys(bindings, logFocused: true)).Fill(),
            Rule(v),
            // The output's place is always there, so the input keeps its place in the layout, and its focus.
            v.VStack(r => resultRows > 0 ? [Result(r, resultRows), Rule(r)] : []).FixedHeight(resultRows > 0 ? resultRows + 1 : 0),
            v.HStack(h => [h.Text(Prompt), Input.Build(h, bindings => BindScreenKeys(bindings, logFocused: false))]).FixedHeight(1),
            Rule(v),
            Bar(v, Status.FormatStatus(), PanelText),
        ]);
        return HelpVisible ? context.ZStack(z => [main, _help.Build(z, ScreenRows(), CloseHelp)]) : main;
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

    // The command output takes as many rows as it has, up to half of what it shares with the log; a longer output
    // shows a page at a time with a line saying how to scroll.
    private int ResultRows()
    {
        if (_result.Count == 0)
        {
            _resultRows = 0;
            return 0;
        }

        var shared = _view.Rows + (_resultRows > 0 ? _resultRows + 1 : 0);
        _resultRows = Math.Min(_result.Count, Math.Max(3, shared / 2));
        _resultTop = Math.Clamp(_resultTop, 0, Math.Max(0, _result.Count - PageRows(_resultRows)));
        return _resultRows;
    }

    // The screen's rows: the log's, the output's with its rule, and the bars, rules, and input around them.
    private int ScreenRows() => _view.Rows + (_resultRows > 0 ? _resultRows + 1 : 0) + 6;

    private int PageRows(int rows) => _result.Count > rows ? rows - 1 : rows;

    private SurfaceWidget Result<TParent>(WidgetContext<TParent> context, int rows)
        where TParent : Hex1bWidget
    {
        var page = PageRows(rows);
        var shown = _result.Skip(_resultTop).Take(page).ToList();
        if (page < rows)
        {
            var above = _resultTop;
            var below = _result.Count - _resultTop - page;
            var where = (above, below) switch
            {
                (0, _) => $"{below} more below",
                (_, 0) => $"{above} more above",
                _ => $"{above} more above, {below} below",
            };

            shown.Add(StyledTextFolder.Fold(Markup.Parse($"[dim]── {where} · PgUp/PgDn scroll · Esc closes[/]"), 0)[0]);
        }

        return context.Surface(s => [s.Layer(surface => StyledBlock.Draw(surface, shown, Session.ColorEnabled))])
            .Height(Hex1b.Layout.SizeHint.Fixed(rows));
    }

    // Keys typed on the log that are not its own start a command.
    private void TypeCommand(string text, InputBindingActionContext context)
    {
        _ = context.FocusWhere(IsInput);
        Input.Type(text);
    }

    private void CloseHelp(InputBindingActionContext context)
    {
        HelpVisible = false;
        _ = context.FocusWhere(IsLog);
    }

    private static bool IsLog(Hex1bNode node) => node is InteractableNode { Child: SurfaceNode };

    private static bool IsInput(Hex1bNode node) => node is TextBoxNode;

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
