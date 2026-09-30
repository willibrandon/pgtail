using System.Text;

namespace Pgtail.Parsing;

/// <summary>
/// Parses a log line in a known format.
/// </summary>
/// <remarks>
/// A line that does not fit its format is still shown: it becomes a LOG entry whose message is the whole line.
/// </remarks>
public static class LogLineParser
{
    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="utf8">The line as UTF-8, with or without its line ending.</param>
    /// <param name="format">The format the log is written in.</param>
    /// <returns>The entry.</returns>
    public static LogEntry Parse(ReadOnlyMemory<byte> utf8, LogFormat format = LogFormat.Text)
    {
        ReadOnlySpan<byte> span = utf8.Span;
        int length = span.Length;
        while (length > 0 && span[length - 1] is (byte)'\n' or (byte)'\r')
        {
            length--;
        }

        ReadOnlyMemory<byte> line = utf8[..length];
        switch (format)
        {
            case LogFormat.Csv:
                return CsvLogParser.TryParse(line, out LogEntry? csv) ? csv : Unparsed(line, format);
            case LogFormat.Json:
                return JsonLogParser.TryParse(line, out LogEntry? json) ? json : Unparsed(line, format);
            default:
                return TextLogParser.Parse(line);
        }
    }

    private static LogEntry Unparsed(ReadOnlyMemory<byte> line, LogFormat format)
    {
        string raw = Encoding.UTF8.GetString(line.Span);
        return new LogEntry { Level = LogLevel.Log, Message = raw, Raw = raw, RawUtf8 = line, Format = format };
    }
}
