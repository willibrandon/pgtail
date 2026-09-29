using Pgtail.Files;
using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Tails several log files together, interleaving their entries by time.
/// </summary>
/// <remarks>
/// Each entry is marked with the name of its file. When the files came from a pattern, files that start matching it
/// are picked up within five seconds.
/// </remarks>
/// <param name="paths">The files to start with.</param>
/// <param name="pattern">The pattern to watch for new files, or null.</param>
/// <param name="fromStart">True to read existing lines; false to read only new lines.</param>
/// <param name="interval">How often to poll.</param>
public sealed class MultiFileTailer(IReadOnlyList<string> paths, GlobPattern? pattern, bool fromStart, TimeSpan interval)
    : PollingLogSource(interval)
{
    private readonly Dictionary<string, FileCursor> _cursors = new(OperatingSystem.IsWindows()
        ? StringComparer.OrdinalIgnoreCase
        : StringComparer.Ordinal);

    private readonly List<ReadOnlyMemory<byte>> _lines = [];
    private long _lastScan;

    /// <summary>
    /// The files being read.
    /// </summary>
    public IReadOnlyList<string> Paths => [.. _cursors.Keys];

    /// <summary>
    /// The files that are currently missing or unreadable.
    /// </summary>
    public IReadOnlyList<string> UnavailablePaths { get; private set; } = [];

    /// <inheritdoc />
    protected override void Prepare()
    {
        foreach (var path in paths)
        {
            Add(path, fromStart);
        }

        _lastScan = Environment.TickCount64;
    }

    /// <inheritdoc />
    protected override void Poll()
    {
        ScanPattern();
        var entries = new List<LogEntry>();
        var unavailable = new List<string>();
        foreach (var cursor in _cursors.Values)
        {
            _lines.Clear();
            var outcome = cursor.Read(_lines, format => Post(new LogSourceEvent(LogSourceEventKind.FormatDetected, Format: format,
                Path: cursor.Path)));
            if (outcome != ReadOutcome.Read)
            {
                unavailable.Add(cursor.Path);
                continue;
            }

            var name = Path.GetFileName(cursor.Path);
            foreach (var line in _lines)
            {
                var entry = LogLineParser.Parse(line, cursor.Format ?? LogFormat.Text);
                entry.SourceFile = name;
                entries.Add(entry);
            }
        }

        UnavailablePaths = unavailable;
        IsUnavailable = unavailable.Count > 0;
        foreach (var entry in entries
            .OrderBy(entry => entry.Timestamp is { } time ? LogTimestamps.ToUtc(time) : DateTime.MinValue)
            .ThenBy(entry => entry.SourceFile, StringComparer.Ordinal))
        {
            Post(new LogSourceEvent(LogSourceEventKind.Entry, entry));
        }
    }

    private void ScanPattern()
    {
        var now = Environment.TickCount64;
        if (pattern is null || now - _lastScan < 5000)
        {
            return;
        }

        _lastScan = now;
        foreach (var path in pattern.Expand())
        {
            if (!_cursors.ContainsKey(path))
            {
                Add(path, fromStart);
            }
        }
    }

    private void Add(string path, bool start)
    {
        if (!File.Exists(path))
        {
            return;
        }

        var cursor = new FileCursor(path);
        cursor.Open(start);
        _cursors[path] = cursor;
    }
}
