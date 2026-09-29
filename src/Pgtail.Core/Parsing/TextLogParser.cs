using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's plain text (stderr) log format.
/// </summary>
/// <remarks>
/// Three prefixes are recognized: <c>time zone [pid] LEVEL:</c>, the bracketed <c>[time zone] [pid] [context] LEVEL:</c>,
/// and <c>time zone LEVEL:</c> without a process ID, which is common on Windows. Anything else becomes a LOG entry whose
/// message is the whole line.
/// </remarks>
public static partial class TextLogParser
{
    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="line">The line, without its line ending.</param>
    /// <returns>The entry.</returns>
    public static LogEntry Parse(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        string timestamp;
        string zone;
        string level;
        string message;
        int? pid = null;
        var match = WithPid().Match(line);
        if (!match.Success)
        {
            match = Bracketed().Match(line);
        }

        if (match.Success)
        {
            timestamp = match.Groups[1].Value;
            zone = match.Groups[2].Value;
            pid = int.TryParse(match.Groups[3].ValueSpan, NumberStyles.None, CultureInfo.InvariantCulture, out var id) ? id : null;
            level = match.Groups[4].Value;
            message = match.Groups[5].Value;
        }
        else
        {
            match = WithoutPid().Match(line);
            if (!match.Success)
            {
                return new LogEntry { Level = LogLevel.Log, Message = line, Raw = line, Format = LogFormat.Text };
            }

            timestamp = match.Groups[1].Value;
            zone = match.Groups[2].Value;
            level = match.Groups[3].Value;
            message = match.Groups[4].Value;
        }

        DateTime? time = null;
        if (LogTimestamps.TryParseNaive(timestamp, out var parsed))
        {
            // Only UTC is attached; any other zone name is read as the local time it was written in.
            time = zone.Equals("UTC", StringComparison.OrdinalIgnoreCase) ? DateTime.SpecifyKind(parsed, DateTimeKind.Utc) : parsed;
        }

        return new LogEntry
        {
            Timestamp = time,
            Level = LogLevels.FromSeverity(level),
            Message = message,
            Raw = line,
            Pid = pid,
            Format = LogFormat.Text,
        };
    }

    [GeneratedRegex(@"^([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)\s+(\w+)?\s*\[([0-9]+)\]\s+(\w+):\s*(.*)$")]
    private static partial Regex WithPid();

    [GeneratedRegex(@"^([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)\s+(\w+)\s+(\w+):\s+(.*)$")]
    private static partial Regex WithoutPid();

    [GeneratedRegex(@"^\[([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)\s+(\w+)\]\s+"
        + @"\[([0-9]+)\]\s+(?:\[[^\]]*\]\s+)?(\w+):\s*(.*)$")]
    private static partial Regex Bracketed();
}
