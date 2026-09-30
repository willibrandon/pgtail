using System.Globalization;
using System.Text.Json;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's jsonlog format.
/// </summary>
public static class JsonLogParser
{
    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="utf8">The line as UTF-8, without its line ending.</param>
    /// <param name="entry">The entry, when the line is a JSON object.</param>
    /// <returns>True when the line is a JSON object.</returns>
    public static bool TryParse(ReadOnlyMemory<byte> utf8, out LogEntry entry)
    {
        entry = null!;
        if (!TryReadObject(utf8, out Dictionary<string, JsonElement>? data))
        {
            return false;
        }

        string? severity = data.TryGetValue("error_severity", out JsonElement level) && level.ValueKind == JsonValueKind.String
            ? level.GetString()
            : "LOG";
        string message = data.TryGetValue("message", out JsonElement text) ? AsText(text) ?? "" : "";
        (DateTime Time, TimeSpan Offset)? timestamp = LogTimestamps.ParseStructured(StringOrNull(data, "timestamp"));
        entry = new LogEntry
        {
            Timestamp = timestamp?.Time,
            Offset = timestamp?.Offset,
            Level = LogLevels.FromSeverity(severity),
            Message = message,
            RawUtf8 = utf8,
            Pid = (int?)Integer(data, "pid"),
            Format = LogFormat.Json,
            UserName = Text(data, "user"),
            DatabaseName = Text(data, "dbname"),
            RemoteHost = Text(data, "remote_host"),
            RemotePort = (int?)Integer(data, "remote_port"),
            SessionId = Text(data, "session_id"),
            SessionLineNumber = Integer(data, "line_num"),
            SessionStart = LogTimestamps.ParseStructured(StringOrNull(data, "session_start"))?.Time,
            VirtualTransactionId = Text(data, "vxid"),
            TransactionId = Text(data, "txid"),
            SqlState = Text(data, "state_code"),
            Detail = Text(data, "detail"),
            Hint = Text(data, "hint"),
            InternalQuery = Text(data, "internal_query"),
            InternalQueryPosition = (int?)Integer(data, "internal_position"),
            Context = Text(data, "context"),
            Query = Text(data, "statement"),
            QueryPosition = (int?)Integer(data, "cursor_position"),
            FunctionName = Text(data, "func_name"),
            FileName = Text(data, "file_name"),
            FileLineNumber = (int?)Integer(data, "file_line_num"),
            ApplicationName = Text(data, "application_name"),
            BackendType = Text(data, "backend_type"),
            LeaderPid = (int?)Integer(data, "leader_pid"),
            QueryId = Integer(data, "query_id"),
        };

        return true;
    }

    /// <summary>
    /// Reads a UTF-8 line as a JSON object, keeping the last value of a repeated key.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <param name="data">The object's properties.</param>
    /// <returns>True when the line is one JSON object.</returns>
    public static bool TryReadObject(ReadOnlyMemory<byte> line, out Dictionary<string, JsonElement> data)
    {
        data = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        try
        {
            using var document = JsonDocument.Parse(line);
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                return false;
            }

            foreach (JsonProperty property in document.RootElement.EnumerateObject())
            {
                data[property.Name] = property.Value.Clone();
            }

            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    /// <summary>
    /// A JSON value as the text it stands for.
    /// </summary>
    /// <remarks>
    /// A string is itself, booleans are <c>True</c> or <c>False</c>, and other values are written as they appear.
    /// </remarks>
    /// <param name="value">The value.</param>
    /// <returns>The text, or null for a JSON null.</returns>
    public static string? AsText(JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.Null or JsonValueKind.Undefined => null,
        JsonValueKind.String => value.GetString(),
        JsonValueKind.True => "True",
        JsonValueKind.False => "False",
        _ => value.GetRawText(),
    };

    private static string? StringOrNull(Dictionary<string, JsonElement> data, string key) =>
        data.TryGetValue(key, out JsonElement value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static string? Text(Dictionary<string, JsonElement> data, string key) =>
        data.TryGetValue(key, out JsonElement value) ? AsText(value) : null;

    private static long? Integer(Dictionary<string, JsonElement> data, string key)
    {
        if (!data.TryGetValue(key, out JsonElement value))
        {
            return null;
        }

        switch (value.ValueKind)
        {
            case JsonValueKind.Number:
                if (value.TryGetInt64(out long whole))
                {
                    return whole;
                }

                return value.TryGetDouble(out double real) && double.IsFinite(real) && Math.Abs(real) < 9.2e18 ? (long)real : null;
            case JsonValueKind.True:
                return 1;
            case JsonValueKind.False:
                return 0;
            case JsonValueKind.String:
                string text = value.GetString()!.Trim().Replace("_", "", StringComparison.Ordinal);
                return long.TryParse(text, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out long parsed) ? parsed : null;
            default:
                return null;
        }
    }
}
