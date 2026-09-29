using Hex1b;
using Pgtail.Commands;
using Pgtail.Parsing;
using Pgtail.Rendering;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Tail;

/// <summary>
/// The full screen tail view: the log, the command output, the command input, the status bar, and the help overlay.
/// </summary>
/// <remarks>
/// All state changes happen on Hex1b's app loop: entries are taken from the source while the screen is built, a
/// filter change redraws the log a batch at a time across frames, and entries that arrive meanwhile wait in the
/// source until the redraw finishes, so the log stays in order. A command's output shows in a panel above the input
/// until the next command or Escape, so a busy log does not scroll it away.
/// </remarks>
internal sealed partial class TailScreen : ITailHost
{
    private const int EntriesPerFrame = 2_000;
    private const int RebuildBatch = 500;
    private readonly TailRequest _request;
    private readonly ILogSource _source;
    private readonly List<LogEntry> _entries = [];
    private readonly TailLog _log = new();
    private readonly TailLogView _view;
    private readonly TailHistory _history;
    private readonly FilterAnchor _anchor;
    private readonly TailHelpOverlay _help = new();
    private List<List<StyledSpan>> _result = [];
    private int _resultTop;
    private int _resultRows;
    private Hex1bApp? _app;
    private List<LogEntry>? _rebuildSnapshot;
    private int _rebuildIndex;
    private bool _paused;
    private int _detectionScanned;
    private bool _versionDetected;
    private bool _portDetected;
    private bool _ended;

    /// <summary>
    /// Creates the screen for a request.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <param name="request">What to tail.</param>
    /// <param name="source">The source, not yet started.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    public TailScreen(PgtailSession session, TailRequest request, ILogSource source, string currentDirectory)
    {
        ArgumentNullException.ThrowIfNull(session);
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(source);
        Session = session;
        _request = request;
        _source = source;
        CurrentDirectory = currentDirectory;
        _view = new TailLogView(_log, session.ColorEnabled)
        {
            PauseRequested = Pause,
            FollowRequested = Follow,
            Copy = CopyText,
        };

        _history = new TailHistory(session.Paths.TailHistoryFile);
        _anchor = new FilterAnchor(
            session.ActiveLevels is { } levels ? [.. levels] : null,
            session.Regex.Clone(),
            session.Time);
        Input = new TailInput(this, _history);
        RefreshStatus();
        if (request.Source.Instance is { } instance)
        {
            Status.PgVersion = instance.Version;
            Status.PgPort = instance.Port ?? 5432;
        }
        else
        {
            Status.FileName = request.Source.DisplayName;
        }
    }

    /// <inheritdoc/>
    public PgtailSession Session { get; }

    /// <inheritdoc/>
    public CommandOutput Output { get; } = new();

    /// <inheritdoc/>
    public string CurrentDirectory { get; }

    /// <summary>
    /// The status bar.
    /// </summary>
    public TailStatus Status { get; } = new();

    /// <summary>
    /// The command input.
    /// </summary>
    public TailInput Input { get; }

    /// <inheritdoc/>
    public IReadOnlyList<LogEntry> Entries => _entries;

    /// <inheritdoc/>
    public LogFormat? Format { get; private set; }

    /// <summary>
    /// Whether the help overlay is showing.
    /// </summary>
    public bool HelpVisible { get; private set; }

    /// <summary>
    /// Whether a command's output is showing above the input.
    /// </summary>
    public bool ResultVisible => _result.Count > 0;

    /// <summary>
    /// Closes the command output.
    /// </summary>
    public void CloseResult()
    {
        _result = [];
        _resultTop = 0;
    }

    /// <summary>
    /// Scrolls the command output a page at a time when it is longer than its panel, or else the log.
    /// </summary>
    /// <param name="pages">The pages to scroll, negative for up.</param>
    public void Scroll(int pages)
    {
        if (_result.Count > _resultRows)
        {
            var page = PageRows(_resultRows);
            _resultTop = Math.Clamp(_resultTop + (pages * page), 0, Math.Max(0, _result.Count - page));
            return;
        }

        _view.Page(pages);
    }

    /// <inheritdoc/>
    public void Stop()
    {
        _ended = true;
        _app?.RequestStop();
    }

    /// <inheritdoc/>
    public void Pause()
    {
        _paused = true;
        Status.SetFollowing(false);
    }

    /// <inheritdoc/>
    public void Follow()
    {
        _paused = false;
        _view.Reset();
        Status.SetFollowing(true);
        Rebuild();
    }

    /// <inheritdoc/>
    public void Rebuild()
    {
        _rebuildSnapshot = [.. _entries];
        _rebuildIndex = 0;
        _log.Clear();
        _view.Reset();
        Status.ResetCounts();
        Status.TotalLines = 0;
        _app?.Invalidate();
    }

    /// <inheritdoc/>
    public void ResetToAnchor()
    {
        Session.ActiveLevels = _anchor.Levels is { } levels ? [.. levels] : null;
        Session.Regex = _anchor.Regex.Clone();
        Session.Time = _anchor.Time;
        RefreshStatus();
        Rebuild();
    }

    /// <inheritdoc/>
    public void ClearEverything()
    {
        Session.ActiveLevels = null;
        Session.Regex = new Filtering.RegexFilterState();
        Session.Time = Filtering.TimeFilter.Empty;
        Session.Fields.Clear();
        _entries.Clear();
        _rebuildSnapshot = null;
        _log.Clear();
        _view.Reset();
        Status.ResetCounts();
        Status.TotalLines = 0;
        RefreshStatus();
        Status.SlowThreshold = null;
    }

    /// <inheritdoc/>
    public void RefreshStatus()
    {
        Status.Levels = Session.ActiveLevels;
        Status.RegexPattern = Session.Regex.Includes.Count > 0 ? Session.Regex.Includes[0].Pattern : null;
        Status.TimeFilter = TimeStatus(Session.Time);
        Status.SlowThreshold = Session.Slow.Enabled ? Session.Slow.WarningMs : null;
    }

    /// <summary>
    /// Runs a command typed in the input and shows its output above the input.
    /// </summary>
    /// <param name="line">The command line.</param>
    /// <returns>A task that completes when the command has run.</returns>
    public async Task RunCommandAsync(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        var text = line.Trim();
        if (text.Length == 0)
        {
            return;
        }

        _history.Add(text);
        await TailCatalog.ExecuteAsync(text, this);
        ShowResult(Output.Take());
    }

    private static string? TimeStatus(Filtering.TimeFilter time)
    {
        if (!time.IsActive)
        {
            return null;
        }

        var input = time.OriginalInput;
        if (input.Length == 0)
        {
            return time.FormatDescription();
        }

        return (time.Since, time.Until) switch
        {
            ({ }, { }) => $"between:{input.Replace(' ', '-')}",
            ({ }, null) => $"since:{input}",
            _ => $"until:{input}",
        };
    }

    private void ShowResult(IReadOnlyList<StyledText> lines)
    {
        _result = [.. lines.SelectMany(line => StyledTextFolder.Fold(line, 0))];
        _resultTop = 0;
    }

    private void WriteLines(IReadOnlyList<StyledText> lines)
    {
        Append(lines);
        _view.ShowEnd();
    }

    private void Append(IReadOnlyList<StyledText> lines)
    {
        _view.Dropped(_log.Append(lines));
        Status.TotalLines = _log.Count;
    }

    private void CopyText(string text, bool announce)
    {
        TailClipboard.Copy(_app, text);
        if (announce)
        {
            ShowResult([Markup.Parse($"[dim]Copied {text.Length} characters[/]")]);
        }
    }

    /// <summary>
    /// Takes entries from the source, or continues a redraw, for one frame.
    /// </summary>
    private void Pump()
    {
        if (_rebuildSnapshot is { } snapshot)
        {
            var end = Math.Min(snapshot.Count, _rebuildIndex + RebuildBatch);
            var lines = new List<StyledText>();
            for (; _rebuildIndex < end; _rebuildIndex++)
            {
                var entry = snapshot[_rebuildIndex];
                if (Session.ShouldShow(entry))
                {
                    lines.Add(Formatted(entry));
                    Status.Count(entry);
                }
            }

            Append(lines);
            if (_rebuildIndex < snapshot.Count)
            {
                _app?.Invalidate();
                return;
            }

            _rebuildSnapshot = null;
        }

        var shown = new List<StyledText>();
        var taken = 0;
        while (taken < EntriesPerFrame && _source.Events.TryRead(out var item))
        {
            taken++;
            Handle(item, shown);
        }

        // The oldest entries go once per frame rather than one at a time, which would shift the list for every entry.
        if (_entries.Count > Sessions.LogBuffer.DefaultCapacity)
        {
            _entries.RemoveRange(0, _entries.Count - Sessions.LogBuffer.DefaultCapacity);
        }

        if (shown.Count > 0)
        {
            Append(shown);
            if (!_view.Following)
            {
                Status.SetFollowing(false, Status.NewSincePause + shown.Count);
            }
        }

        if (!_paused && _view.Following != Status.Following)
        {
            Status.SetFollowing(_view.Following, 0);
        }

        if (taken == EntriesPerFrame)
        {
            _app?.Invalidate();
        }

        Status.FileUnavailable = _source.IsUnavailable;
        Status.FilePermissionDenied = _source.IsPermissionDenied;
    }

    private void Handle(LogSourceEvent item, List<StyledText> shown)
    {
        switch (item.Kind)
        {
            case LogSourceEventKind.Entry when item.Entry is { } entry:
                AddEntry(entry, shown);
                break;
            case LogSourceEventKind.FormatDetected when item.Format is { } format:
                Format = format;
                Session.DetectedFormat = format;
                break;
            case LogSourceEventKind.EndOfInput:
                shown.Add(Markup.Parse($"[dim]--- stdin complete ({item.LinesRead} lines loaded) - press 'q' to quit ---[/]"));
                break;
        }
    }

    private void AddEntry(LogEntry entry, List<StyledText> shown)
    {
        _entries.Add(entry);

        Session.Buffer.Add(entry);
        if (Session.Observe(entry) is { } notification)
        {
            _ = Task.Run(() => Session.Notifications.Deliver(notification));
        }

        DetectInstance(entry);
        if (!Session.ShouldShow(entry))
        {
            return;
        }

        Status.Count(entry);
        if (_paused)
        {
            Status.SetFollowing(false, Status.NewSincePause + 1);
            return;
        }

        shown.Add(Formatted(entry));
    }

    private StyledText Formatted(LogEntry entry) =>
        Display.EntryFormatter.TailLine(entry, Session.Theme, Session.Chain, Session.SlowLevel(entry));

    private void DetectInstance(LogEntry entry)
    {
        // The server logs its version and then the ports it listens on, so scanning goes on until both are found.
        if (_request.Source.Instance is not null || (_versionDetected && _portDetected) || _detectionScanned >= 50)
        {
            return;
        }

        _detectionScanned++;
        var (foundVersion, foundPort) = InstanceDetection.Find(entry.Message);
        if (foundVersion is not null)
        {
            Status.PgVersion = foundVersion;
            _versionDetected = true;
        }

        if (foundPort is { } value)
        {
            Status.PgPort = value;
            _portDetected = true;
        }
    }
}
