using System.Globalization;
using Pgtail.Parsing;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// What tail mode's status bar and header show: follow state, counts, filters, and the source.
/// </summary>
internal sealed class TailStatus
{
    private static readonly TextStyle Follow = StyleParser.Parse("bold bright_green");
    private static readonly TextStyle Paused = StyleParser.Parse("bold bright_yellow");
    private static readonly TextStyle Dim = StyleParser.Parse("dim");
    private static readonly TextStyle Errors = StyleParser.Parse("bold bright_red");
    private static readonly TextStyle Warnings = StyleParser.Parse("bold bright_yellow");
    private static readonly TextStyle Filters = StyleParser.Parse("bright_cyan");
    private static readonly TextStyle Instance = StyleParser.Parse("bright_white");
    private static readonly TextStyle Unavailable = StyleParser.Parse("bright_yellow");
    private static readonly TextStyle Key = StyleParser.Parse("bold bright_white");

    /// <summary>
    /// The number of ERROR, FATAL, and PANIC entries shown.
    /// </summary>
    public int ErrorCount { get; set; }

    /// <summary>
    /// The number of WARNING entries shown.
    /// </summary>
    public int WarningCount { get; set; }

    /// <summary>
    /// The number of lines in the log.
    /// </summary>
    public int TotalLines { get; set; }

    /// <summary>
    /// Whether new entries scroll into view.
    /// </summary>
    public bool Following { get; private set; } = true;

    /// <summary>
    /// The entries that arrived since following stopped.
    /// </summary>
    public int NewSincePause { get; private set; }

    /// <summary>
    /// The levels shown, or null for all.
    /// </summary>
    public IReadOnlySet<LogLevel>? Levels { get; set; }

    /// <summary>
    /// The first regular expression filter, or null.
    /// </summary>
    public string? RegexPattern { get; set; }

    /// <summary>
    /// The time filter as shown, such as <c>since:5m</c>, or null.
    /// </summary>
    public string? TimeFilter { get; set; }

    /// <summary>
    /// The slow query threshold in milliseconds, or null.
    /// </summary>
    public double? SlowThreshold { get; set; }

    /// <summary>
    /// The PostgreSQL version, from the instance or found in the log.
    /// </summary>
    public string PgVersion { get; set; } = "";

    /// <summary>
    /// The PostgreSQL port, from the instance or found in the log.
    /// </summary>
    public int PgPort { get; set; } = 5432;

    /// <summary>
    /// The file name shown when tailing files without a known version.
    /// </summary>
    public string? FileName { get; set; }

    /// <summary>
    /// Whether a file being read is missing or unreadable.
    /// </summary>
    public bool FileUnavailable { get; set; }

    /// <summary>
    /// Whether a file being read exists but may not be read.
    /// </summary>
    public bool FilePermissionDenied { get; set; }

    /// <summary>
    /// Counts an entry shown in the log.
    /// </summary>
    /// <param name="entry">The entry.</param>
    public void Count(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        switch (entry.Level)
        {
            case LogLevel.Error or LogLevel.Fatal or LogLevel.Panic:
                ErrorCount++;
                break;
            case LogLevel.Warning:
                WarningCount++;
                break;
        }
    }

    /// <summary>
    /// Clears the error and warning counts.
    /// </summary>
    public void ResetCounts()
    {
        ErrorCount = 0;
        WarningCount = 0;
    }

    /// <summary>
    /// Sets follow or paused mode.
    /// </summary>
    /// <param name="following">True to follow.</param>
    /// <param name="newEntries">The entries waiting while paused.</param>
    public void SetFollowing(bool following, int newEntries = 0)
    {
        Following = following;
        NewSincePause = following ? 0 : newEntries;
    }

    /// <summary>
    /// The status bar: <c>FOLLOW | E:0 W:0 | 12 lines | levels:ALL | PG17:5432</c>.
    /// </summary>
    /// <returns>The styled text.</returns>
    public StyledText FormatStatus()
    {
        var text = new StyledText(" ");
        if (Following)
        {
            text.Append("FOLLOW", Follow);
        }
        else
        {
            text.Append(NewSincePause > 0 ? $"PAUSED +{NewSincePause} new" : "PAUSED", Paused);
        }

        text.Append(" | ", Dim).Append($"E:{ErrorCount}", Errors).Append(" ", Dim).Append($"W:{WarningCount}", Warnings);
        text.Append(" | ", Dim).Append($"{TotalLines.ToString("N0", CultureInfo.InvariantCulture)} lines");
        text.Append(" | ", Dim).Append(string.Join(' ', FilterParts()), Filters).Append(" | ", Dim);
        var unavailable = FilePermissionDenied ? "(permission denied)" : "(unavailable)";
        if (PgVersion.Length > 0)
        {
            text.Append($"PG{PgVersion}:{PgPort}", Instance);
            if (FileUnavailable)
            {
                text.Append(" ").Append(unavailable, Unavailable);
            }
        }
        else if (FileName is { } file)
        {
            if (FileUnavailable)
            {
                text.Append(file + " ", Instance).Append(unavailable, Unavailable);
            }
            else
            {
                text.Append(file, Instance);
            }
        }
        else
        {
            text.Append($":{PgPort}", Instance);
        }

        return text;
    }

    /// <summary>
    /// The header's key hints.
    /// </summary>
    /// <returns>The styled text.</returns>
    public static StyledText FormatHeader()
    {
        (string Key, string Description)[] hints =
        [
            ("q", "Quit"), ("?", "Help"), ("/", "Cmd"), ("v", "Visual"), ("y", "Yank"), ("p", "Pause"), ("f", "Follow"),
            ("g/G", "Top/End"),
        ];
        var text = new StyledText(" ");
        for (var i = 0; i < hints.Length; i++)
        {
            if (i > 0)
            {
                text.Append("  ", Dim);
            }

            text.Append(hints[i].Key, Key).Append(" ", Dim).Append(hints[i].Description, Dim);
        }

        return text;
    }

    private List<string> FilterParts()
    {
        var parts = new List<string>
        {
            Levels is null || Levels.Count == LogLevels.All.Count
                ? "levels:ALL"
                : "levels:" + string.Join(',', Levels.Select(level => level.ToName()).Order(StringComparer.Ordinal)),
        };

        if (RegexPattern is { } pattern)
        {
            parts.Add($"filter:/{pattern}/");
        }

        if (TimeFilter is { } time)
        {
            parts.Add(time);
        }

        if (SlowThreshold is { } slow)
        {
            parts.Add($"slow:>{slow.ToString("0.###", CultureInfo.InvariantCulture)}ms");
        }

        return parts;
    }
}
