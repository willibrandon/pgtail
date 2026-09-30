using Pgtail.Detection;
using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Tails one PostgreSQL log file, following PostgreSQL to a new file after a restart or rotation.
/// </summary>
/// <remarks>
/// When the file stops growing or disappears, the source checks at most once a second whether PostgreSQL moved on:
/// <c>current_logfiles</c> in the data directory names the current file, or else the newest file with the same
/// extension in the log directory is taken. When only the file's last lines are read at first, the rest of it is read
/// back once caught up, a chunk at a time from the newest, and reported as older entries, until the start of the file
/// or of the time filter, or until the reader has enough.
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

    /// <inheritdoc />
    public override void StopReadingOlder() => _stopOlder = true;

    /// <inheritdoc />
    protected override void Prepare()
    {
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
        var outcome = _cursor.Read(_lines, format => Post(new LogSourceEvent(LogSourceEventKind.FormatDetected, Format: format,
            Path: _cursor.Path)));
        foreach (var line in _lines)
        {
            if (_grouper.Add(LogLineParser.Parse(line, _cursor.Format ?? LogFormat.Text)) is { } complete)
            {
                Post(new LogSourceEvent(LogSourceEventKind.Entry, complete));
            }
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
        var entries = new List<LogEntry>();
        foreach (var line in lines)
        {
            if (grouper.Add(LogLineParser.Parse(line, _cursor.Format ?? LogFormat.Text)) is { } complete)
            {
                entries.Add(complete);
            }
        }

        if (grouper.Flush() is { } last)
        {
            entries.Add(last);
        }

        if (entries.Count > 0)
        {
            Post(new LogSourceEvent(LogSourceEventKind.Older, Entries: entries));
        }

        var bound = since is { } start ? LogTimestamps.ToUtc(start) : (DateTime?)null;
        var oldest = entries.Find(entry => entry.Timestamp is not null)?.Timestamp;
        if (_olderEnd == 0 || (bound is { } limit && oldest is { } time && LogTimestamps.ToUtc(time) < limit))
        {
            FinishOlder();
        }
    }

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
        var now = Environment.TickCount64;
        if (now - _lastDirectoryScan < 1000)
        {
            return;
        }

        _lastDirectoryScan = now;
        var current = PathResolver.Resolve(_cursor.Path);
        if (dataDirectory is not null && PostgresConf.ReadCurrentLogfiles(dataDirectory) is { } listed && File.Exists(listed)
            && PathResolver.Resolve(listed) != current)
        {
            Switch(listed);
            return;
        }

        // Only a file with the same extension is taken, so a server writing both .log and .csv files is not followed back and forth.
        if (logDirectory is not null && PostgresConf.FindLatestLog(logDirectory) is { } latest && PathResolver.Resolve(latest) != current
            && Path.GetExtension(latest) == Path.GetExtension(_cursor.Path))
        {
            Switch(latest);
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
