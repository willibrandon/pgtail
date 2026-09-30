using System.Globalization;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using Pgtail.Parsing;

namespace Pgtail.Exporting;

/// <summary>
/// Writes entries as exported text, JSON Lines, or CSV.
/// </summary>
public static class EntryExporter
{
    /// <summary>
    /// The CSV header row.
    /// </summary>
    public const string CsvHeader = "timestamp,level,pid,message";

    private static readonly JavaScriptEncoder s_encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping;

    /// <summary>
    /// One entry as a line in a format, without a line ending.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="format">The format.</param>
    /// <returns>The line.</returns>
    public static string Format(LogEntry entry, ExportFormat format)
    {
        ArgumentNullException.ThrowIfNull(entry);
        return format switch
        {
            ExportFormat.Json => Json(entry),
            ExportFormat.Csv => Csv(entry),
            _ => entry.Raw,
        };
    }

    /// <summary>
    /// The entry as a JSON object: <c>{"timestamp": ..., "level": ..., "pid": ..., "message": ...}</c>.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The JSON text.</returns>
    public static string Json(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        var builder = new StringBuilder("{\"timestamp\": ");
        builder.Append(LogTimestamps.ToIsoFormat(entry) is { } time ? Quote(time) : "null");
        builder.Append(", \"level\": ").Append(Quote(entry.Level.ToName()));
        builder.Append(", \"pid\": ").Append(entry.Pid is { } pid ? pid.ToString(CultureInfo.InvariantCulture) : "null");
        builder.Append(", \"message\": ").Append(Quote(entry.Message)).Append('}');
        return builder.ToString();
    }

    /// <summary>
    /// The entry as a CSV row, quoting fields only where needed.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The row.</returns>
    public static string Csv(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        return string.Join(',',
            CsvField(LogTimestamps.ToIsoFormat(entry) ?? ""),
            CsvField(entry.Level.ToName()),
            CsvField(entry.Pid?.ToString(CultureInfo.InvariantCulture) ?? ""),
            CsvField(entry.Message));
    }

    /// <summary>
    /// Writes entries to a file, creating its directory, with a CSV header unless appending.
    /// </summary>
    /// <param name="entries">The entries.</param>
    /// <param name="path">The file.</param>
    /// <param name="format">The format.</param>
    /// <param name="append">True to add to the end of an existing file.</param>
    /// <param name="line">Formats a text entry in place of its raw line, as for highlighted export, or null.</param>
    /// <returns>The number of entries written.</returns>
    public static int WriteFile(
        IEnumerable<LogEntry> entries,
        string path,
        ExportFormat format,
        bool append,
        Func<LogEntry, string>? line = null)
    {
        ArgumentNullException.ThrowIfNull(entries);
        ArgumentNullException.ThrowIfNull(path);
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))!);
        using var writer = new StreamWriter(path, append, new UTF8Encoding(false)) { NewLine = "\n" };
        if (format == ExportFormat.Csv && !append)
        {
            writer.WriteLine(CsvHeader);
        }

        int count = 0;
        foreach (LogEntry entry in entries)
        {
            writer.WriteLine(format == ExportFormat.Text && line is not null ? line(entry) : Format(entry, format));
            count++;
        }

        return count;
    }

    private static string Quote(string text) => "\"" + JsonEncodedText.Encode(text, s_encoder).ToString() + "\"";

    private static string CsvField(string value) =>
        value.AsSpan().IndexOfAny(",\"\r\n") >= 0 ? "\"" + value.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"" : value;
}
