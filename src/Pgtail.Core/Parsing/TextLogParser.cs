using System.Globalization;
using System.Text;
using Scout.Text.Regex;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's plain text (stderr) log format.
/// </summary>
/// <remarks>
/// Three prefixes are recognized: <c>time zone [pid] LEVEL:</c>, the bracketed <c>[time zone] [pid] [context] LEVEL:</c>,
/// and <c>time zone LEVEL:</c> without a process ID, which is common on Windows. Anything else becomes a LOG entry whose
/// message is the whole line. Lines are matched as bytes and only the parts kept are decoded.
/// </remarks>
public static class TextLogParser
{
    private const string Time = @"([0-9]{4}-[0-9]{2}-[0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)";

    // Groups: timestamp, zone, pid, level, message.
    private static readonly ByteRegex WithPid = ByteRegex.Compile(@"^" + Time + @"\s+(\w+)?\s*\[([0-9]+)\]\s+(\w+):\s*(.*)$");

    // Groups: timestamp, zone, pid, level, message.
    private static readonly ByteRegex Bracketed =
        ByteRegex.Compile(@"^\[" + Time + @"\s+(\w+)\]\s+\[([0-9]+)\]\s+(?:\[[^\]]*\]\s+)?(\w+):\s*(.*)$");

    // Groups: timestamp, zone, level, message.
    private static readonly ByteRegex WithoutPid = ByteRegex.Compile(@"^" + Time + @"\s+(\w+)\s+(\w+):\s+(.*)$");

    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="line">The line as UTF-8, without its line ending.</param>
    /// <returns>The entry.</returns>
    public static LogEntry Parse(ReadOnlyMemory<byte> line)
    {
        var bytes = line.Span;
        string timestamp;
        string zone;
        string level;
        string message;
        int? pid = null;
        if ((WithPid.FindCaptures(bytes) ?? Bracketed.FindCaptures(bytes)) is { } captures)
        {
            timestamp = Text(bytes, captures.GetGroup(1));
            zone = Text(bytes, captures.GetGroup(2));
            pid = int.TryParse(Text(bytes, captures.GetGroup(3)), NumberStyles.None, CultureInfo.InvariantCulture, out var id) ? id : null;
            level = Text(bytes, captures.GetGroup(4));
            message = Text(bytes, captures.GetGroup(5));
        }
        else if (WithoutPid.FindCaptures(bytes) is { } plain)
        {
            timestamp = Text(bytes, plain.GetGroup(1));
            zone = Text(bytes, plain.GetGroup(2));
            level = Text(bytes, plain.GetGroup(3));
            message = Text(bytes, plain.GetGroup(4));
        }
        else
        {
            var raw = Encoding.UTF8.GetString(bytes);
            return new LogEntry { Level = LogLevel.Log, Message = raw, Raw = raw, RawUtf8 = line, Format = LogFormat.Text };
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
            RawUtf8 = line,
            Pid = pid,
            Format = LogFormat.Text,
        };
    }

    private static string Text(ReadOnlySpan<byte> bytes, ByteRegexMatch? group) =>
        group is { } match ? Encoding.UTF8.GetString(match.Value(bytes)) : "";
}
