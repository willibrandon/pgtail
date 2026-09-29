using System.Text;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's plain text (stderr) log format.
/// </summary>
/// <remarks>
/// Three prefixes are recognized: <c>time zone [pid] LEVEL:</c> (the zone may be missing), the bracketed
/// <c>[time zone] [pid] [context] LEVEL:</c>, and <c>time zone LEVEL:</c> without a process ID, which is common on
/// Windows. Anything else becomes a LOG entry whose message is the whole line. Lines are read as bytes by a scanner, since
/// every line of a log passes through here, and only the parts kept are decoded.
/// </remarks>
public static class TextLogParser
{
    // The labels of the lines PostgreSQL writes after a message's first line; they keep their label in the message.
    private static readonly HashSet<string> ContinuationLabels = ["DETAIL", "HINT", "CONTEXT", "STATEMENT", "QUERY", "LOCATION"];

    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="line">The line as UTF-8, without its line ending.</param>
    /// <returns>The entry.</returns>
    public static LogEntry Parse(ReadOnlyMemory<byte> line)
    {
        var bytes = line.Span;
        if (!TryReadPrefix(bytes, out var prefix))
        {
            // PostgreSQL indents the further lines of a multi-line message with a tab.
            var raw = Encoding.UTF8.GetString(bytes);
            return new LogEntry
            {
                Level = LogLevel.Log,
                Message = raw,
                Raw = raw,
                RawUtf8 = line,
                Format = LogFormat.Text,
                Continues = bytes is [(byte)'\t', ..],
            };
        }

        var time = prefix.Time;
        TimeSpan? offset = null;
        var zone = Encoding.ASCII.GetString(bytes[prefix.Zone]);
        if (time is { } parsed && LogTimestamps.TryGetZoneOffset(zone, out var known))
        {
            // A zone pgtail knows gives the instant; any other zone name is read as the local time it was written in.
            time = DateTime.SpecifyKind(parsed - known, DateTimeKind.Utc);
            offset = known;
        }

        var level = Encoding.ASCII.GetString(bytes[prefix.Level]);
        var message = Encoding.UTF8.GetString(bytes[prefix.Message..]);
        var label = level.ToUpperInvariant();
        var continues = ContinuationLabels.Contains(label);
        return new LogEntry
        {
            Timestamp = time,
            Offset = offset,
            Level = LogLevels.FromSeverity(level),
            Message = continues ? $"{label}:  {message}" : message,
            RawUtf8 = line,
            Pid = prefix.Pid,
            Format = LogFormat.Text,
            Continues = continues,
        };
    }

    // Reads one of the three prefixes, trying them in the order the formats are listed.
    private static bool TryReadPrefix(ReadOnlySpan<byte> line, out Prefix prefix)
    {
        prefix = default;
        return line is [(byte)'[', ..]
            ? TryReadBracketed(line, ref prefix)
            : TryReadWithPid(line, ref prefix) || TryReadWithoutPid(line, ref prefix);
    }

    // time [zone] [pid] LEVEL: message
    private static bool TryReadWithPid(ReadOnlySpan<byte> line, ref Prefix prefix)
    {
        var position = 0;
        if (!TryReadTime(line, ref position, out prefix.Time) || SkipSpaces(line, ref position) == 0)
        {
            return false;
        }

        var zoneStart = position;
        _ = SkipWord(line, ref position);
        prefix.Zone = zoneStart..position;
        _ = SkipSpaces(line, ref position);
        return TryReadPid(line, ref position, out prefix.Pid) && SkipSpaces(line, ref position) > 0
            && TryReadLevel(line, ref position, out prefix.Level, requireSpace: false, out prefix.Message);
    }

    // [time zone] [pid] [context] LEVEL: message
    private static bool TryReadBracketed(ReadOnlySpan<byte> line, ref Prefix prefix)
    {
        var position = 1;
        if (!TryReadTime(line, ref position, out prefix.Time) || SkipSpaces(line, ref position) == 0)
        {
            return false;
        }

        var zoneStart = position;
        if (SkipWord(line, ref position) == 0)
        {
            return false;
        }

        prefix.Zone = zoneStart..position;
        if (!TryRead(line, ref position, (byte)']') || SkipSpaces(line, ref position) == 0
            || !TryReadPid(line, ref position, out prefix.Pid) || SkipSpaces(line, ref position) == 0)
        {
            return false;
        }

        // An optional [context] follows the process ID.
        if (line[position..] is [(byte)'[', ..] && line[position..].IndexOf((byte)']') is var close and >= 0)
        {
            var after = position + close + 1;
            if (SkipSpaces(line, ref after) > 0)
            {
                position = after;
            }
        }

        return TryReadLevel(line, ref position, out prefix.Level, requireSpace: false, out prefix.Message);
    }

    // time zone LEVEL: message, with at least one space after the colon
    private static bool TryReadWithoutPid(ReadOnlySpan<byte> line, ref Prefix prefix)
    {
        var position = 0;
        if (!TryReadTime(line, ref position, out prefix.Time) || SkipSpaces(line, ref position) == 0)
        {
            return false;
        }

        var zoneStart = position;
        if (SkipWord(line, ref position) == 0)
        {
            return false;
        }

        prefix.Zone = zoneStart..position;
        prefix.Pid = null;
        return SkipSpaces(line, ref position) > 0
            && TryReadLevel(line, ref position, out prefix.Level, requireSpace: true, out prefix.Message);
    }

    // [digits]
    private static bool TryReadPid(ReadOnlySpan<byte> line, ref int position, out int? pid)
    {
        pid = null;
        var start = position + 1;
        var end = start;
        if (!TryRead(line, ref position, (byte)'['))
        {
            return false;
        }

        long value = 0;
        while (end < line.Length && char.IsAsciiDigit((char)line[end]))
        {
            value = Math.Min(value * 10 + (line[end] - '0'), long.MaxValue / 10);
            end++;
        }

        if (end == start || end >= line.Length || line[end] != (byte)']')
        {
            return false;
        }

        position = end + 1;
        pid = value <= int.MaxValue ? (int)value : null;
        return true;
    }

    // LEVEL: then spaces, then the message
    private static bool TryReadLevel(ReadOnlySpan<byte> line, ref int position, out Range level, bool requireSpace, out int message)
    {
        level = default;
        message = 0;
        var start = position;
        if (SkipWord(line, ref position) == 0 || !TryRead(line, ref position, (byte)':'))
        {
            return false;
        }

        level = start..(position - 1);
        if (SkipSpaces(line, ref position) == 0 && requireSpace)
        {
            return false;
        }

        message = position;
        return true;
    }

    // yyyy-mm-dd hh:mm:ss[.fraction]; the time is null when its fields are out of range.
    private static bool TryReadTime(ReadOnlySpan<byte> line, ref int position, out DateTime? time)
    {
        time = null;
        var p = position;
        if (!TryReadNumber(line, ref p, 4, out var year) || !TryRead(line, ref p, (byte)'-')
            || !TryReadNumber(line, ref p, 2, out var month) || !TryRead(line, ref p, (byte)'-')
            || !TryReadNumber(line, ref p, 2, out var day) || SkipSpaces(line, ref p) == 0
            || !TryReadNumber(line, ref p, 2, out var hour) || !TryRead(line, ref p, (byte)':')
            || !TryReadNumber(line, ref p, 2, out var minute) || !TryRead(line, ref p, (byte)':')
            || !TryReadNumber(line, ref p, 2, out var second))
        {
            return false;
        }

        long ticks = 0;
        if (p < line.Length && line[p] == (byte)'.' && p + 1 < line.Length && char.IsAsciiDigit((char)line[p + 1]))
        {
            p++;
            var scale = TimeSpan.TicksPerSecond;
            while (p < line.Length && char.IsAsciiDigit((char)line[p]))
            {
                scale /= 10;
                ticks += (line[p] - '0') * scale;
                p++;
            }
        }

        position = p;
        if (year >= 1 && month is >= 1 and <= 12 && day >= 1 && day <= DateTime.DaysInMonth(year, month)
            && hour <= 23 && minute <= 59 && second <= 59)
        {
            time = new DateTime(year, month, day, hour, minute, second, DateTimeKind.Unspecified).AddTicks(ticks);
        }

        return true;
    }

    private static bool TryReadNumber(ReadOnlySpan<byte> line, ref int position, int digits, out int value)
    {
        value = 0;
        if (position + digits > line.Length)
        {
            return false;
        }

        for (var i = 0; i < digits; i++)
        {
            var digit = line[position + i];
            if (!char.IsAsciiDigit((char)digit))
            {
                return false;
            }

            value = (value * 10) + (digit - '0');
        }

        position += digits;
        return true;
    }

    private static bool TryRead(ReadOnlySpan<byte> line, ref int position, byte expected)
    {
        if (position < line.Length && line[position] == expected)
        {
            position++;
            return true;
        }

        return false;
    }

    private static int SkipSpaces(ReadOnlySpan<byte> line, ref int position)
    {
        var start = position;
        while (position < line.Length && line[position] is (byte)' ' or (byte)'\t' or (byte)'\v' or (byte)'\f' or (byte)'\r')
        {
            position++;
        }

        return position - start;
    }

    private static int SkipWord(ReadOnlySpan<byte> line, ref int position)
    {
        var start = position;
        while (position < line.Length && (char.IsAsciiLetterOrDigit((char)line[position]) || line[position] == (byte)'_'))
        {
            position++;
        }

        return position - start;
    }

    // Where the parts of a prefix are in the line.
    private struct Prefix
    {
        public DateTime? Time;
        public Range Zone;
        public int? Pid;
        public Range Level;
        public int Message;
    }
}
