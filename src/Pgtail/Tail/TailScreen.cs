using Hex1b;
using Pgtail.Commands;
using Pgtail.Display;
using Pgtail.Filtering;
using Pgtail.Highlighting;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Tail;

/// <summary>
/// The full screen tail view: the log, the command output, the command input, the status bar, and the help overlay.
/// </summary>
/// <remarks>
/// All state changes happen on Hex1b's app loop: entries are taken from the source while the screen is built. What the
/// log held when tailing started, as a time filter reads back, is read without being drawn, and the view opens at its
/// newest entries once it is all read, while older ones are read back and put in front. A filter change redraws the log
/// at once, and a command's output is written into the log.
/// </remarks>
internal sealed partial class TailScreen : ITailHost, IAsyncDisposable
{
    /// <summary>
    /// How many of a log's last lines tail mode reads back for a time filter, enough for the entries it keeps.
    /// </summary>
    /// <remarks>
    /// A long log opens as fast as a short one; the rest of the range is read back afterward.
    /// </remarks>
    public const int BacklogLines = 20_000;

    /// <summary>
    /// The most entries tail mode keeps; reading back older ones stops there.
    /// </summary>
    public const int MaxEntries = 200_000;

    private const int EntriesPerFrame = 2_000;
    private const int LoadPerFrame = 20_000;
    private const int RecountPerFrame = 5_000;
    private readonly TailRequest _request;
    private readonly ILogSource _source;
    private readonly List<LogEntry> _entries = [];
    private readonly TailLog _log = new();
    private readonly TailLogView _view;
    private readonly TailHistory _history;
    private readonly FilterAnchor _anchor;
    private readonly TailHelpOverlay _help = new();
    private Hex1bApp? _app;
    private int _loaded;
    private bool _paused;
    private int _detectionScanned;
    private bool _versionDetected;
    private bool _portDetected;
    private bool _ended;
    private bool _caughtUp;
    private bool _olderAdded;
    private int? _recounted;

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
    /// Scrolls the log a page at a time, as Page Up and Page Down do in the input.
    /// </summary>
    /// <param name="pages">The pages to scroll, negative for up.</param>
    public void Scroll(int pages) => _view.Page(pages);

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
        _log.Clear();
        _view.Reset();
        Status.ResetCounts();
        Status.TotalLines = 0;
        ShowEntries();
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
        Session.Regex = new RegexFilterState();
        Session.Time = TimeFilter.Empty;
        Session.Fields.Clear();
        _entries.Clear();
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
    /// Runs a command typed in the input and writes its output into the log.
    /// </summary>
    /// <param name="line">The command line.</param>
    /// <returns>A task that completes when the command has run.</returns>
    public async Task RunCommandAsync(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        string text = line.Trim();
        if (text.Length == 0)
        {
            return;
        }

        _history.Add(text);
        // A command that reads the statistics sees them whole.
        Recount(int.MaxValue);
        await TailCatalog.ExecuteAsync(text, this);
        WriteLines(Output.Take());
    }

    private static string? TimeStatus(TimeFilter time)
    {
        if (!time.IsActive)
        {
            return null;
        }

        string input = time.OriginalInput;
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

    private void WriteLines(IReadOnlyList<StyledText> lines)
    {
        Append(lines.Select(line => TailSegment.Of(TailLine.From(line))));
        _view.ShowEnd();
    }

    private void Append(IEnumerable<TailSegment> segments)
    {
        _view.Dropped(_log.Append(segments));
        Status.TotalLines = _log.EntryRows;
    }

    private void CopyText(string text, bool announce)
    {
        TailClipboard.Copy(_app, text);
        if (announce)
        {
            WriteLines([Markup.Parse($"[dim]Copied {text.Length} characters[/]")]);
        }
    }

    /// <summary>
    /// Takes entries from the source for one frame.
    /// </summary>
    private void Pump()
    {
        if (!_caughtUp)
        {
            Load();
            return;
        }

        var shown = new List<TailSegment>();
        int taken = 0;
        while (taken < EntriesPerFrame && _source.Events.TryRead(out LogSourceEvent? item))
        {
            taken++;
            Handle(item, shown);
        }

        TrimEntries();
        Recount(RecountPerFrame);
        if (_recounted is not null)
        {
            _app?.Invalidate();
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

    private void Handle(LogSourceEvent item, List<TailSegment> shown)
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
            case LogSourceEventKind.Older when item.Entries is { } older:
                AddOlder(older);
                break;
            case LogSourceEventKind.OlderRead:
                Status.LoadingOlder = false;
                if (_olderAdded)
                {
                    StartRecount();
                }

                break;
            case LogSourceEventKind.EndOfInput:
                shown.Add(TailSegment.Of(TailLine.From(
                    Markup.Parse($"[dim]--- stdin complete ({item.LinesRead} lines loaded) - press 'q' to quit ---[/]"))));
                break;
        }
    }

    // Reads the log's backlog a frame's worth at a time without drawing it; when it is all read, the view opens at the
    // newest entries.
    private void Load()
    {
        int taken = 0;
        while (taken < LoadPerFrame && _source.Events.TryRead(out LogSourceEvent? item))
        {
            taken++;
            if (item.Kind == LogSourceEventKind.CaughtUp)
            {
                _caughtUp = true;
                Status.Loading = null;
                TrimEntries();
                ShowEntries();
                _app?.Invalidate();
                return;
            }

            if (item is { Kind: LogSourceEventKind.Entry, Entry: { } entry })
            {
                Keep(entry, isNew: false);
                _loaded++;
            }
            else
            {
                Handle(item, []);
            }
        }

        TrimEntries();
        Status.Loading = _loaded;
        if (taken == LoadPerFrame)
        {
            _app?.Invalidate();
        }
    }

    // Counts every entry the filters show and draws the newest of them, as many as the log keeps.
    private void ShowEntries()
    {
        var shown = new List<LogEntry>();
        foreach (LogEntry entry in _entries.Where(Session.ShouldShow))
        {
            Status.Count(entry);
            shown.Add(entry);
        }

        Append(shown.Skip(Math.Max(0, shown.Count - TailLog.MaxLines)).Select(Segment));
    }

    // The oldest entries go once per frame rather than one at a time, which would shift the list for every entry.
    private void TrimEntries()
    {
        if (_entries.Count > MaxEntries)
        {
            int removed = _entries.Count - MaxEntries;
            _entries.RemoveRange(0, removed);
            _recounted = _recounted is { } recounted ? Math.Max(0, recounted - removed) : null;
        }
    }

    // Puts entries read back in front, as many as tail mode keeps, and stops reading back once it is full. They count in
    // the statistics once all are read, since those take entries oldest first.
    private void AddOlder(IReadOnlyList<LogEntry> older)
    {
        int room = MaxEntries - _entries.Count;
        IReadOnlyList<LogEntry> kept = older.Count > room ? [.. older.Skip(older.Count - Math.Max(0, room))] : older;
        _entries.InsertRange(0, kept);
        _olderAdded |= kept.Count > 0;
        var segments = new List<TailSegment>();
        foreach (LogEntry entry in kept.Where(Session.ShouldShow))
        {
            Status.Count(entry);
            segments.Add(Segment(entry));
        }

        _view.Prepended(_log.Prepend(segments));
        Status.TotalLines = _log.EntryRows;
        Status.LoadingOlder = true;
        if (older.Count > room)
        {
            _source.StopReadingOlder();
            Status.LoadingOlder = false;
            Status.OlderNotLoaded = true;
        }
    }

    // Once older entries are read back behind those counted, the statistics count every entry kept over again in the
    // order they were logged, a frame's worth at a time, and the newest are kept for export.
    private void StartRecount()
    {
        Session.ClearStatistics();
        _olderAdded = false;
        _recounted = 0;
        Session.Buffer.Clear();
        foreach (LogEntry? entry in _entries.Skip(Math.Max(0, _entries.Count - Session.Buffer.Capacity)))
        {
            Session.Buffer.Add(entry);
        }
    }

    // Counts the next entries of a recount. Entries that come in meanwhile are counted when the recount reaches them.
    private void Recount(int count)
    {
        if (_recounted is not { } start)
        {
            return;
        }

        int end = start + Math.Min(count, _entries.Count - start);
        for (int i = start; i < end; i++)
        {
            Session.Count(_entries[i]);
        }

        _recounted = end < _entries.Count ? end : null;
    }

    private void Keep(LogEntry entry, bool isNew)
    {
        _entries.Add(entry);
        Session.Buffer.Add(entry);
        if (_recounted is null)
        {
            Session.Observe(entry, isNew);
        }
        else if (isNew)
        {
            Session.Notifications.Consider(entry);
        }

        DetectInstance(entry);
    }

    private void AddEntry(LogEntry entry, List<TailSegment> shown)
    {
        Keep(entry, isNew: true);
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

        shown.Add(Segment(entry));
    }

    // An entry's rows, one for each line of its message, made when first drawn: formatted without semantic
    // highlighting, which comes when a row is first drawn.
    private TailSegment Segment(LogEntry entry) => new(
        1 + entry.Message.AsSpan().Count('\n'),
        Width(entry),
        () => TailLine.From(
            EntryFormatter.TailLine(entry, Session.Theme, HighlighterChain.None, Session.SlowLevel(entry)),
            () => Formatted(entry)));

    // The width of the entry's widest row, measured without formatting the entry unless its prefix has characters
    // outside ASCII.
    private static int Width(LogEntry entry) => EntryFormatter.TailPrefixLength(entry) is { } prefix
        ? TailLine.Widest(prefix, entry.Message)
        : TailLine.Widest(EntryFormatter.TailPrefix(entry).PlainText + entry.Message);

    private StyledText Formatted(LogEntry entry) =>
        EntryFormatter.TailLine(entry, Session.Theme, Session.Chain, Session.SlowLevel(entry));

    private void DetectInstance(LogEntry entry)
    {
        // The server logs its version and then the ports it listens on, so scanning goes on until both are found.
        if (_request.Source.Instance is not null || (_versionDetected && _portDetected) || _detectionScanned >= 50)
        {
            return;
        }

        _detectionScanned++;
        (string? foundVersion, int? foundPort) = InstanceDetection.Find(entry.Message);
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
