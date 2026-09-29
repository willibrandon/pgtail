using System.Collections.Frozen;
using System.Text.Json;

namespace Pgtail.Parsing;

/// <summary>
/// Recognizes the format of a PostgreSQL log from one of its lines.
/// </summary>
public static class LogFormatDetector
{
    private static readonly FrozenSet<string> Severities = new[]
    {
        "DEBUG5", "DEBUG4", "DEBUG3", "DEBUG2", "DEBUG1", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "LOG", "FATAL", "PANIC",
    }
    .ToFrozenSet(StringComparer.Ordinal);

    /// <summary>
    /// Detects the format of a line: jsonlog, then csvlog, then plain text.
    /// </summary>
    /// <param name="line">The first non-empty line of a log.</param>
    /// <returns>The format.</returns>
    public static LogFormat Detect(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        line = line.Trim();
        if (line.Length == 0)
        {
            return LogFormat.Text;
        }

        if (line.StartsWith('{') && IsJsonLog(line))
        {
            return LogFormat.Json;
        }

        return IsCsvLog(line) ? LogFormat.Csv : LogFormat.Text;
    }

    /// <summary>
    /// Whether a line is a jsonlog object: JSON with <c>error_severity</c> naming a level and a <c>message</c>.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <returns>True for a jsonlog line.</returns>
    public static bool IsJsonLog(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        line = line.Trim();
        if (!line.StartsWith('{') || !JsonLogParser.TryReadObject(line, out var data))
        {
            return false;
        }

        if (!data.TryGetValue("error_severity", out var severity) || !data.ContainsKey("message"))
        {
            return false;
        }

        var name = severity.ValueKind == JsonValueKind.Null ? "None" : JsonLogParser.AsText(severity) ?? "";
        return Severities.Contains(name.ToUpperInvariant());
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
        if (line.Length == 0 || !CsvLine.TrySplit(line, out var fields) || fields.Count is < 22 or > 26)
        {
            return false;
        }

        var timestamp = fields[0];
        if (timestamp.Length < 19 || timestamp[4] != '-' || timestamp[7] != '-' || timestamp[10] != ' ' || timestamp[13] != ':'
            || timestamp[16] != ':')
        {
            return false;
        }

        return Severities.Contains(fields[11].ToUpperInvariant());
    }
}
