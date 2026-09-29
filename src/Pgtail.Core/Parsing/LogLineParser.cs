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
    /// <param name="line">The line, with or without its line ending.</param>
    /// <param name="format">The format the log is written in.</param>
    /// <returns>The entry.</returns>
    public static LogEntry Parse(string line, LogFormat format = LogFormat.Text)
    {
        ArgumentNullException.ThrowIfNull(line);
        line = line.TrimEnd('\n', '\r');
        switch (format)
        {
            case LogFormat.Csv:
                return CsvLogParser.TryParse(line, out var csv) ? csv : Unparsed(line, format);
            case LogFormat.Json:
                return JsonLogParser.TryParse(line, out var json) ? json : Unparsed(line, format);
            default:
                return TextLogParser.Parse(line);
        }
    }

    private static LogEntry Unparsed(string line, LogFormat format) =>
        new() { Level = LogLevel.Log, Message = line, Raw = line, Format = format };
}
