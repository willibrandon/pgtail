namespace Pgtail.Parsing;

/// <summary>
/// One parsed PostgreSQL log entry in any of the supported formats.
/// </summary>
/// <remarks>
/// <para>
/// Timestamps keep the distinction PostgreSQL logs make: a time written with a zone is stored as
/// <see cref="DateTimeKind.Utc"/>, and a time written without one is stored as <see cref="DateTimeKind.Unspecified"/> and
/// read as local time wherever times are compared.
/// </para>
/// <para>
/// The extended fields are filled from csvlog and jsonlog lines; text lines carry only the core fields.
/// </para>
/// </remarks>
public sealed class LogEntry
{
    /// <summary>
    /// The field names in the order they are listed and serialized.
    /// </summary>
    public static IReadOnlyList<string> FieldOrder { get; } =
    [
        "timestamp", "level", "message", "raw", "pid", "format", "source_file", "user_name", "database_name",
        "application_name", "sql_state", "detail", "hint", "context", "query", "internal_query", "location", "session_id",
        "session_line_num", "command_tag", "virtual_transaction_id", "transaction_id", "backend_type", "leader_pid",
        "query_id", "connection_from", "remote_host", "remote_port", "session_start", "query_pos", "internal_query_pos",
        "func_name", "file_name", "file_line_num",
    ];

    /// <summary>
    /// When the entry was logged, or null when the line had no readable time.
    /// </summary>
    public DateTime? Timestamp { get; init; }

    /// <summary>
    /// The severity.
    /// </summary>
    public LogLevel Level { get; init; } = LogLevel.Log;

    /// <summary>
    /// The message text.
    /// </summary>
    public string Message { get; init; } = "";

    /// <summary>
    /// The line as read, without its line ending.
    /// </summary>
    public string Raw { get; init; } = "";

    /// <summary>
    /// The backend process ID, when the line carries one.
    /// </summary>
    public int? Pid { get; init; }

    /// <summary>
    /// The format the line was parsed as.
    /// </summary>
    public LogFormat Format { get; init; } = LogFormat.Text;

    /// <summary>
    /// The file name the entry came from while several files are tailed together.
    /// </summary>
    public string? SourceFile { get; set; }

    /// <summary>
    /// The database user.
    /// </summary>
    public string? UserName { get; init; }

    /// <summary>
    /// The database name.
    /// </summary>
    public string? DatabaseName { get; init; }

    /// <summary>
    /// The client application name.
    /// </summary>
    public string? ApplicationName { get; init; }

    /// <summary>
    /// The SQLSTATE code, such as <c>42P01</c>.
    /// </summary>
    public string? SqlState { get; init; }

    /// <summary>
    /// The error detail.
    /// </summary>
    public string? Detail { get; init; }

    /// <summary>
    /// The error hint.
    /// </summary>
    public string? Hint { get; init; }

    /// <summary>
    /// The error context.
    /// </summary>
    public string? Context { get; init; }

    /// <summary>
    /// The user query that led to the entry.
    /// </summary>
    public string? Query { get; init; }

    /// <summary>
    /// The internal query that led to the entry.
    /// </summary>
    public string? InternalQuery { get; init; }

    /// <summary>
    /// The PostgreSQL source location.
    /// </summary>
    public string? Location { get; init; }

    /// <summary>
    /// The session identifier.
    /// </summary>
    public string? SessionId { get; init; }

    /// <summary>
    /// The line number within the session.
    /// </summary>
    public long? SessionLineNumber { get; init; }

    /// <summary>
    /// The command tag, such as SELECT (csvlog only).
    /// </summary>
    public string? CommandTag { get; init; }

    /// <summary>
    /// The virtual transaction ID.
    /// </summary>
    public string? VirtualTransactionId { get; init; }

    /// <summary>
    /// The transaction ID.
    /// </summary>
    public string? TransactionId { get; init; }

    /// <summary>
    /// The backend type, such as client backend or autovacuum worker.
    /// </summary>
    public string? BackendType { get; init; }

    /// <summary>
    /// The parallel group leader's process ID.
    /// </summary>
    public int? LeaderPid { get; init; }

    /// <summary>
    /// The query identifier.
    /// </summary>
    public long? QueryId { get; init; }

    /// <summary>
    /// The client host and port (csvlog only).
    /// </summary>
    public string? ConnectionFrom { get; init; }

    /// <summary>
    /// The client host (jsonlog only).
    /// </summary>
    public string? RemoteHost { get; init; }

    /// <summary>
    /// The client port (jsonlog only).
    /// </summary>
    public int? RemotePort { get; init; }

    /// <summary>
    /// When the session started.
    /// </summary>
    public DateTime? SessionStart { get; init; }

    /// <summary>
    /// The error position in the query.
    /// </summary>
    public int? QueryPosition { get; init; }

    /// <summary>
    /// The error position in the internal query.
    /// </summary>
    public int? InternalQueryPosition { get; init; }

    /// <summary>
    /// The function that raised the error (jsonlog only).
    /// </summary>
    public string? FunctionName { get; init; }

    /// <summary>
    /// The source file that raised the error (jsonlog only).
    /// </summary>
    public string? FileName { get; init; }

    /// <summary>
    /// The source line that raised the error (jsonlog only).
    /// </summary>
    public int? FileLineNumber { get; init; }

    /// <summary>
    /// A field's value by its canonical name or an alias.
    /// </summary>
    /// <remarks>
    /// The aliases are <c>app</c>, <c>application</c>, <c>db</c>, <c>database</c>, <c>user</c>, and <c>backend</c>.
    /// </remarks>
    /// <param name="name">The field name.</param>
    /// <returns>The value, or null when the entry has none or the name is unknown.</returns>
    public object? GetField(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        var canonical = name switch
        {
            "app" or "application" => "application_name",
            "db" or "database" => "database_name",
            "user" => "user_name",
            "backend" => "backend_type",
            _ => name,
        };

        return canonical switch
        {
            "timestamp" => Timestamp,
            "level" => Level,
            "message" => Message,
            "raw" => Raw,
            "pid" => Pid,
            "format" => Format,
            "source_file" => SourceFile,
            "user_name" => UserName,
            "database_name" => DatabaseName,
            "application_name" => ApplicationName,
            "sql_state" => SqlState,
            "detail" => Detail,
            "hint" => Hint,
            "context" => Context,
            "query" => Query,
            "internal_query" => InternalQuery,
            "location" => Location,
            "session_id" => SessionId,
            "session_line_num" => SessionLineNumber,
            "command_tag" => CommandTag,
            "virtual_transaction_id" => VirtualTransactionId,
            "transaction_id" => TransactionId,
            "backend_type" => BackendType,
            "leader_pid" => LeaderPid,
            "query_id" => QueryId,
            "connection_from" => ConnectionFrom,
            "remote_host" => RemoteHost,
            "remote_port" => RemotePort,
            "session_start" => SessionStart,
            "query_pos" => QueryPosition,
            "internal_query_pos" => InternalQueryPosition,
            "func_name" => FunctionName,
            "file_name" => FileName,
            "file_line_num" => FileLineNumber,
            _ => null,
        };
    }

    /// <summary>
    /// The names of the fields that have a value, in <see cref="FieldOrder"/>.
    /// </summary>
    /// <returns>The field names.</returns>
    public IReadOnlyList<string> AvailableFields() => [.. FieldOrder.Where(name => GetField(name) is not null)];
}
