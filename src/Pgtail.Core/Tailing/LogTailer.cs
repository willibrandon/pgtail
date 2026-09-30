using Pgtail.Detection;
using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Tails one PostgreSQL log file, following PostgreSQL to a new file after a restart or rotation.
/// </summary>
/// <remarks>
/// When the file stops growing or disappears, the source checks at most once a second whether PostgreSQL moved on:
/// <c>current_logfiles</c> in the data directory names the current file, or else the newest file with the same
/// extension in the log directory is taken when it was written after the file being read. A file that was not the
/// newest in its directory when tailing began, such as an older log or a copy named on purpose, is not followed. When
/// only the file's last lines are read at first, the rest of it is read back once caught up, a chunk at a time from the
/// newest, and reported as older entries, until the start of the file or of the time filter, or until the reader has
/// enough.
/// </remarks>
/// <param name="path">The log file.</param>
/// <param name="fromStart">True to read existing lines, as when a time filter looks back; false to read only new lines.</param>
/// <param name="dataDirectory">The instance's data directory, or null when tailing a file on its own.</param>
/// <param name="logDirectory">The directory PostgreSQL logs to, or null.</param>
/// <param name="interval">How often to poll.</param>
/// <param name="lastLines">With <paramref name="fromStart"/>, how many of the file's last lines to read first, or null for all.</param>
/// <param name="since">The start of the time filter, where reading back older entries stops.</param>
public sealed class LogTailer(
    string path,
    bool fromStart,
    string? dataDirectory,
    string? logDirectory,
    TimeSpan interval,
    int? lastLines = null,
    DateTime? since = null)
    : PollingLogSource(interval)
{
    private readonly List<ReadOnlyMemory<byte>> _lines = [];
    private readonly EntryGrouper _grouper = new();
    private FileCursor _cursor = new(path);
    private long _lastDirectoryScan;
    private bool _caughtUp;
    private long _olderEnd = -1;
    private int _olderGeneration;
    private volatile bool _stopOlder;
    private bool _followsDirectory;

    /// <inheritdoc />
    public override void StopReadingOlder() => _stopOlder = true;

    /// <inheritdoc />
    protected override void Prepare()
    {
        // A file chosen over a newer log in its directory is read on its own.
        _followsDirectory = logDirectory is not null && (!File.Exists(path) || Successor() is null);
        _cursor.Open(fromStart, lastLines);
        if (fromStart && lastLines is not null && _cursor.Position > 0)
        {
            _olderEnd = _cursor.Position;
            _olderGeneration = _cursor.Generation;
        }
    }

    /// <inheritdoc />
    protected override void Poll()
    {
        _lines.Clear();
        ReadOutcome outcome = _cursor.Read(_lines, format => Post(new LogSourceEvent(LogSourceEventKind.FormatDetected, Format: format,
            Path: _cursor.Path)));
        foreach (LogEntry complete in Group(_grouper, _lines))
        {
            Post(new LogSourceEvent(LogSourceEventKind.Entry, complete));
        }

        // A read that stopped short of the end may have split an entry from its continuation lines, so its last entry
        // waits for the next read.
        if (outcome != ReadOutcome.Read || _cursor.AtEnd)
        {
            FlushEntry();
        }

        if (!_caughtUp && _cursor.AtEnd)
        {
            _caughtUp = true;
            Post(new LogSourceEvent(LogSourceEventKind.CaughtUp));
        }

        if (_caughtUp && _olderEnd >= 0)
        {
            ReadOlder();
        }

        Behind = (outcome == ReadOutcome.Read && !_cursor.AtEnd) || _olderEnd > 0;
        IsUnavailable = outcome != ReadOutcome.Read;
        IsPermissionDenied = outcome == ReadOutcome.PermissionDenied;
        if (outcome != ReadOutcome.Read || _lines.Count == 0)
        {
            CheckForNewFile();
        }
    }

    // Reads back the chunk of entries before those read so far, until the start of the file or of the time filter.
    private void ReadOlder()
    {
        if (_stopOlder || _olderEnd == 0 || _cursor.Generation != _olderGeneration)
        {
            FinishOlder();
            return;
        }

        var lines = new List<ReadOnlyMemory<byte>>();
        _olderEnd = _cursor.ReadOlder(_olderEnd, lines);
        var grouper = new EntryGrouper();
        List<LogEntry> entries = [.. Group(grouper, lines)];

        if (grouper.Flush() is { } last)
        {
            entries.Add(last);
        }

        if (entries.Count > 0)
        {
            Post(new LogSourceEvent(LogSourceEventKind.Older, Entries: entries));
        }

        DateTime? bound = since is { } start ? LogTimestamps.ToUtc(start) : null;
        DateTime? oldest = entries.Find(entry => entry.Timestamp is not null)?.Timestamp;
        if (_olderEnd == 0 || (bound is { } limit && oldest is { } time && LogTimestamps.ToUtc(time) < limit))
        {
            FinishOlder();
        }
    }

    // The entries that lines complete, in order; the last one stays with the grouper until more lines or a flush.
    private IEnumerable<LogEntry> Group(EntryGrouper grouper, IEnumerable<ReadOnlyMemory<byte>> lines) =>
        lines.Select(line => grouper.Add(LogLineParser.Parse(line, _cursor.Format ?? LogFormat.Text))).OfType<LogEntry>();

    private void FlushEntry()
    {
        if (_grouper.Flush() is { } last)
        {
            Post(new LogSourceEvent(LogSourceEventKind.Entry, last));
        }
    }

    private void FinishOlder()
    {
        _olderEnd = -1;
        Post(new LogSourceEvent(LogSourceEventKind.OlderRead));
    }

    private void CheckForNewFile()
    {
        long now = Environment.TickCount64;
        if (now - _lastDirectoryScan < 1000)
        {
            return;
        }

        _lastDirectoryScan = now;
        string current = PathResolver.Resolve(_cursor.Path);
        if (dataDirectory is not null && PostgresConf.ReadCurrentLogfiles(dataDirectory) is { } listed && File.Exists(listed)
            && PathResolver.Resolve(listed) != current)
        {
            Switch(listed);
            return;
        }

        if (_followsDirectory && Successor() is { } next)
        {
            Switch(next);
        }
    }

    // The newest log in the directory written after the one being read, as the file PostgreSQL moves on to is, or null.
    // Only a file with the same extension counts, so a server writing both .log and .csv files is not followed back and
    // forth; one written at the same time is a copy or a neighbor, not a successor.
    private string? Successor()
    {
        if (logDirectory is null || PostgresConf.FindLatestLog(logDirectory, Path.GetExtension(_cursor.Path)) is not { } latest
            || PathResolver.Resolve(latest) == PathResolver.Resolve(_cursor.Path))
        {
            return null;
        }

        try
        {
            return !File.Exists(_cursor.Path) || File.GetLastWriteTimeUtc(latest) > File.GetLastWriteTimeUtc(_cursor.Path) ? latest : null;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    private void Switch(string next)
    {
        FlushEntry();
        _cursor = new FileCursor(next);
        _cursor.Open(fromStart: true);
        IsUnavailable = false;
        IsPermissionDenied = false;
        Post(new LogSourceEvent(LogSourceEventKind.FileSwitched, Path: next));
    }
}
