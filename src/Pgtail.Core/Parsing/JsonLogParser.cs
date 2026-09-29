using System.Globalization;
using System.Text.Json;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's jsonlog format.
/// </summary>
public static class JsonLogParser
{
    /// <summary>
    /// Maps jsonlog keys to the entry fields they fill.
    /// </summary>
    public static IReadOnlyDictionary<string, string> FieldMap { get; } = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["timestamp"] = "timestamp",
        ["user"] = "user_name",
        ["dbname"] = "database_name",
        ["pid"] = "pid",
        ["remote_host"] = "remote_host",
        ["remote_port"] = "remote_port",
        ["session_id"] = "session_id",
        ["line_num"] = "session_line_num",
        ["session_start"] = "session_start",
        ["vxid"] = "virtual_transaction_id",
        ["txid"] = "transaction_id",
        ["error_severity"] = "level",
        ["state_code"] = "sql_state",
        ["message"] = "message",
        ["detail"] = "detail",
        ["hint"] = "hint",
        ["internal_query"] = "internal_query",
        ["internal_position"] = "internal_query_pos",
        ["context"] = "context",
        ["statement"] = "query",
        ["cursor_position"] = "query_pos",
        ["func_name"] = "func_name",
        ["file_name"] = "file_name",
        ["file_line_num"] = "file_line_num",
        ["application_name"] = "application_name",
        ["backend_type"] = "backend_type",
        ["leader_pid"] = "leader_pid",
        ["query_id"] = "query_id",
    };

    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <param name="entry">The entry, when the line is a JSON object.</param>
    /// <returns>True when the line is a JSON object.</returns>
    public static bool TryParse(string line, out LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(line);
        entry = null!;
        line = line.TrimEnd('\n', '\r');
        if (!TryReadObject(line, out var data))
        {
            return false;
        }

        var severity = data.TryGetValue("error_severity", out var level) && level.ValueKind == JsonValueKind.String
            ? level.GetString()
            : "LOG";
        var message = data.TryGetValue("message", out var text) ? AsText(text) ?? "" : "";
        entry = new LogEntry
        {
            Timestamp = LogTimestamps.ParseStructured(StringOrNull(data, "timestamp")),
            Level = LogLevels.FromSeverity(severity),
            Message = message,
            Raw = line,
            Pid = (int?)Integer(data, "pid"),
            Format = LogFormat.Json,
            UserName = Text(data, "user"),
            DatabaseName = Text(data, "dbname"),
            RemoteHost = Text(data, "remote_host"),
            RemotePort = (int?)Integer(data, "remote_port"),
            SessionId = Text(data, "session_id"),
            SessionLineNumber = Integer(data, "line_num"),
            SessionStart = LogTimestamps.ParseStructured(StringOrNull(data, "session_start")),
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
    /// Reads a line as a JSON object, keeping the last value of a repeated key.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <param name="data">The object's properties.</param>
    /// <returns>True when the line is one JSON object.</returns>
    public static bool TryReadObject(string line, out Dictionary<string, JsonElement> data)
    {
        ArgumentNullException.ThrowIfNull(line);
        data = new Dictionary<string, JsonElement>(StringComparer.Ordinal);
        try
        {
            using var document = JsonDocument.Parse(line);
            if (document.RootElement.ValueKind != JsonValueKind.Object)
            {
                return false;
            }

            foreach (var property in document.RootElement.EnumerateObject())
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
        data.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static string? Text(Dictionary<string, JsonElement> data, string key) =>
        data.TryGetValue(key, out var value) ? AsText(value) : null;

    private static long? Integer(Dictionary<string, JsonElement> data, string key)
    {
        if (!data.TryGetValue(key, out var value))
        {
            return null;
        }

        switch (value.ValueKind)
        {
            case JsonValueKind.Number:
                if (value.TryGetInt64(out var whole))
                {
                    return whole;
                }

                return value.TryGetDouble(out var real) && double.IsFinite(real) && Math.Abs(real) < 9.2e18 ? (long)real : null;
            case JsonValueKind.True:
                return 1;
            case JsonValueKind.False:
                return 0;
            case JsonValueKind.String:
                var text = value.GetString()!.Trim().Replace("_", "", StringComparison.Ordinal);
                return long.TryParse(text, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var parsed) ? parsed : null;
            default:
                return null;
        }
    }
}
