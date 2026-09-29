using Pgtail.Detection;
using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Tails one PostgreSQL log file, following PostgreSQL to a new file after a restart or rotation.
/// </summary>
/// <remarks>
/// When the file stops growing or disappears, the source checks at most once a second whether PostgreSQL moved on:
/// <c>current_logfiles</c> in the data directory names the current file, or else the newest file with the same
/// extension in the log directory is taken.
/// </remarks>
/// <param name="path">The log file.</param>
/// <param name="fromStart">True to read existing lines, as when a time filter looks back; false to read only new lines.</param>
/// <param name="dataDirectory">The instance's data directory, or null when tailing a file on its own.</param>
/// <param name="logDirectory">The directory PostgreSQL logs to, or null.</param>
/// <param name="interval">How often to poll.</param>
public sealed class LogTailer(string path, bool fromStart, string? dataDirectory, string? logDirectory, TimeSpan interval)
    : PollingLogSource(interval)
{
    private readonly List<ReadOnlyMemory<byte>> _lines = [];
    private readonly EntryGrouper _grouper = new();
    private FileCursor _cursor = new(path);
    private long _lastDirectoryScan;

    /// <summary>
    /// The file being read.
    /// </summary>
    public string CurrentPath => _cursor.Path;

    /// <inheritdoc />
    protected override void Prepare() => _cursor.Open(fromStart);

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

        if (_grouper.Flush() is { } last)
        {
            Post(new LogSourceEvent(LogSourceEventKind.Entry, last));
        }

        IsUnavailable = outcome != ReadOutcome.Read;
        IsPermissionDenied = outcome == ReadOutcome.PermissionDenied;
        if (outcome != ReadOutcome.Read || _lines.Count == 0)
        {
            CheckForNewFile();
        }
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
        _cursor = new FileCursor(next);
        _cursor.Open(fromStart: true);
        IsUnavailable = false;
        IsPermissionDenied = false;
        Post(new LogSourceEvent(LogSourceEventKind.FileSwitched, Path: next));
    }
}
