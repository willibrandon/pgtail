using System.Globalization;
using System.Text;

namespace Pgtail.Parsing;

/// <summary>
/// Parses lines of PostgreSQL's csvlog format.
/// </summary>
/// <remarks>
/// PostgreSQL writes 22 to 26 columns depending on its version. A line needs at least the 14 columns up to the message;
/// missing trailing columns are read as empty.
/// </remarks>
public static class CsvLogParser
{
    /// <summary>
    /// The csvlog column names in order.
    /// </summary>
    public static IReadOnlyList<string> FieldOrder { get; } =
    [
        "log_time", "user_name", "database_name", "process_id", "connection_from", "session_id", "session_line_num",
        "command_tag", "session_start_time", "virtual_transaction_id", "transaction_id", "error_severity", "sql_state_code",
        "message", "detail", "hint", "internal_query", "internal_query_pos", "context", "query", "query_pos", "location",
        "application_name", "backend_type", "leader_pid", "query_id",
    ];

    /// <summary>
    /// Parses one line.
    /// </summary>
    /// <param name="utf8">The line as UTF-8, without its line ending.</param>
    /// <param name="entry">The entry, when the line is a csvlog record.</param>
    /// <returns>True when the line is a csvlog record.</returns>
    public static bool TryParse(ReadOnlyMemory<byte> utf8, out LogEntry entry)
    {
        entry = null!;
        string line = Encoding.UTF8.GetString(utf8.Span);
        if (!CsvLine.TrySplit(line, out List<string>? fields) || fields.Count < 14)
        {
            return false;
        }

        string Field(int index) => index < fields.Count ? fields[index] : "";
        (DateTime Time, TimeSpan Offset)? timestamp = LogTimestamps.ParseStructured(Field(0));
        entry = new LogEntry
        {
            Timestamp = timestamp?.Time,
            Offset = timestamp?.Offset,
            Level = LogLevels.FromSeverity(Field(11)),
            Message = Field(13),
            Raw = line,
            RawUtf8 = utf8,
            Pid = ParseInt(Field(3)),
            Format = LogFormat.Csv,
            UserName = NonEmpty(Field(1)),
            DatabaseName = NonEmpty(Field(2)),
            ConnectionFrom = NonEmpty(Field(4)),
            SessionId = NonEmpty(Field(5)),
            SessionLineNumber = ParseLong(Field(6)),
            CommandTag = NonEmpty(Field(7)),
            SessionStart = LogTimestamps.ParseStructured(Field(8))?.Time,
            VirtualTransactionId = NonEmpty(Field(9)),
            TransactionId = NonEmpty(Field(10)),
            SqlState = NonEmpty(Field(12)),
            Detail = NonEmpty(Field(14)),
            Hint = NonEmpty(Field(15)),
            InternalQuery = NonEmpty(Field(16)),
            InternalQueryPosition = ParseInt(Field(17)),
            Context = NonEmpty(Field(18)),
            Query = NonEmpty(Field(19)),
            QueryPosition = ParseInt(Field(20)),
            Location = NonEmpty(Field(21)),
            ApplicationName = NonEmpty(Field(22)),
            BackendType = NonEmpty(Field(23)),
            LeaderPid = ParseInt(Field(24)),
            QueryId = ParseLong(Field(25)),
        };

        return true;
    }

    private static string? NonEmpty(string value) => value.Length == 0 ? null : value;

    private static int? ParseInt(string value) =>
        int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int number) ? number : null;

    private static long? ParseLong(string value) =>
        long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out long number) ? number : null;
}
