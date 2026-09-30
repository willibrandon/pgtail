using System.Collections.Frozen;
using System.Text;
using System.Text.Json;

namespace Pgtail.Parsing;

/// <summary>
/// Recognizes the format of a PostgreSQL log from one of its lines.
/// </summary>
public static class LogFormatDetector
{
    private static readonly FrozenSet<string> s_severities = new[]
    {
        "DEBUG5", "DEBUG4", "DEBUG3", "DEBUG2", "DEBUG1", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "LOG", "FATAL", "PANIC",
    }
    .ToFrozenSet(StringComparer.Ordinal);

    /// <summary>
    /// Detects the format of a line: jsonlog, then csvlog, then plain text.
    /// </summary>
    /// <param name="utf8">The first non-empty line of a log, as UTF-8.</param>
    /// <returns>The format.</returns>
    public static LogFormat Detect(ReadOnlyMemory<byte> utf8)
    {
        ReadOnlyMemory<byte> line = Trim(utf8);
        if (line.IsEmpty)
        {
            return LogFormat.Text;
        }

        if (line.Span[0] == (byte)'{' && IsJsonLog(line))
        {
            return LogFormat.Json;
        }

        return IsCsvLog(Encoding.UTF8.GetString(line.Span)) ? LogFormat.Csv : LogFormat.Text;
    }

    /// <summary>
    /// Whether a line is a jsonlog object: JSON with <c>error_severity</c> naming a level and a <c>message</c>.
    /// </summary>
    /// <param name="utf8">The line as UTF-8.</param>
    /// <returns>True for a jsonlog line.</returns>
    public static bool IsJsonLog(ReadOnlyMemory<byte> utf8)
    {
        ReadOnlyMemory<byte> line = Trim(utf8);
        if (line.IsEmpty || line.Span[0] != (byte)'{' || !JsonLogParser.TryReadObject(line, out Dictionary<string, JsonElement>? data))
        {
            return false;
        }

        if (!data.TryGetValue("error_severity", out JsonElement severity) || !data.ContainsKey("message"))
        {
            return false;
        }

        string name = severity.ValueKind == JsonValueKind.Null ? "None" : JsonLogParser.AsText(severity) ?? "";
        return s_severities.Contains(name.ToUpperInvariant());
    }

    /// <summary>
    /// Whether a line is a csvlog record: 22 to 26 columns, a timestamp first, and a level in the severity column.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <returns>True for a csvlog line.</returns>
    public static bool IsCsvLog(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        line = line.Trim();
        if (line.Length == 0 || !CsvLine.TrySplit(line, out List<string>? fields) || fields.Count is < 22 or > 26)
        {
            return false;
        }

        string timestamp = fields[0];
        if (timestamp.Length < 19 || timestamp[4] != '-' || timestamp[7] != '-' || timestamp[10] != ' ' || timestamp[13] != ':'
            || timestamp[16] != ':')
        {
            return false;
        }

        return s_severities.Contains(fields[11].ToUpperInvariant());
    }

    private static ReadOnlyMemory<byte> Trim(ReadOnlyMemory<byte> line)
    {
        ReadOnlySpan<byte> span = line.Span;
        int start = 0;
        int end = span.Length;
        while (start < end && IsWhite(span[start]))
        {
            start++;
        }

        while (end > start && IsWhite(span[end - 1]))
        {
            end--;
        }

        return line[start..end];
    }

    private static bool IsWhite(byte b) => b is (byte)' ' or (byte)'\t' or (byte)'\r' or (byte)'\n' or 0x0B or 0x0C;
}
