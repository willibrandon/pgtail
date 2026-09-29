namespace Pgtail.Highlighting;

/// <summary>
/// The keywords and phrases the built-in keyword highlighters look for.
/// </summary>
internal static class HighlightKeywords
{
    /// <summary>
    /// SQL data manipulation keywords.
    /// </summary>
    public static readonly string[] SqlDml =
    [
        "SELECT", "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT",
    ];

    /// <summary>
    /// SQL data definition keywords.
    /// </summary>
    public static readonly string[] SqlDdl =
    [
        "CREATE", "ALTER", "DROP", "TRUNCATE", "TABLE", "INDEX", "VIEW", "TRIGGER", "FUNCTION", "PROCEDURE", "SCHEMA", "DATABASE",
        "EXTENSION", "TYPE", "DOMAIN", "SEQUENCE", "MATERIALIZED", "TABLESPACE", "ROLE", "USER", "POLICY", "RULE", "OPERATOR",
        "AGGREGATE", "COLLATION", "CONVERSION", "LANGUAGE", "PUBLICATION", "SUBSCRIPTION", "STATISTICS", "TRANSFORM",
    ];

    /// <summary>
    /// SQL data control keywords.
    /// </summary>
    public static readonly string[] SqlDcl =
    [
        "GRANT", "REVOKE", "PRIVILEGES", "USAGE", "CONNECT",
    ];

    /// <summary>
    /// SQL transaction control keywords.
    /// </summary>
    public static readonly string[] SqlTcl =
    [
        "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE", "START", "TRANSACTION", "WORK",
    ];

    /// <summary>
    /// Every other SQL keyword.
    /// </summary>
    public static readonly string[] SqlOther =
    [
        "FROM", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AS", "ORDER", "BY", "GROUP", "HAVING", "LIMIT", "OFFSET",
        "INTO", "VALUES", "SET", "RETURNING", "FETCH", "ONLY", "NEXT", "PRIOR", "PERCENT", "TIES", "AND", "OR", "NOT", "IN", "EXISTS",
        "BETWEEN", "LIKE", "ILIKE", "SIMILAR", "IS", "ISNULL", "NOTNULL", "NULL", "UNION", "INTERSECT", "EXCEPT", "DISTINCT", "ALL",
        "ANY", "SOME", "CASE", "WHEN", "THEN", "ELSE", "END", "WITH", "RECURSIVE", "OVER", "PARTITION", "WINDOW", "RANGE", "ROWS",
        "GROUPS", "UNBOUNDED", "PRECEDING", "FOLLOWING", "CURRENT", "ROW", "EXCLUDE", "CROSS", "FULL", "NATURAL", "USING", "LATERAL",
        "ASC", "DESC", "NULLS", "FIRST", "LAST", "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "CONSTRAINT", "DEFAULT", "CHECK", "UNIQUE",
        "DEFERRABLE", "DEFERRED", "IMMEDIATE", "INITIALLY", "ISOLATION", "LEVEL", "SERIALIZABLE", "REPEATABLE", "READ", "COMMITTED",
        "UNCOMMITTED", "EXPLAIN", "ANALYZE", "VACUUM", "REINDEX", "CLUSTER", "REFRESH", "LOCK", "COPY", "COMMENT", "SECURITY", "LABEL",
        "TEMPORARY", "TEMP", "PREPARE", "EXECUTE", "DEALLOCATE", "CURSOR", "DECLARE", "CLOSE", "MOVE", "ABSOLUTE", "RELATIVE",
        "FORWARD", "BACKWARD", "DISCARD", "RESET", "SHOW", "LISTEN", "NOTIFY", "UNLISTEN", "TRUE", "FALSE", "UNKNOWN", "CAST",
        "COALESCE", "NULLIF", "GREATEST", "LEAST", "RETURNS", "ARRAY", "FILTER", "WITHIN", "IF", "ELSIF", "LOOP", "WHILE", "FOR",
        "FOREACH", "EXIT", "CONTINUE", "RETURN", "RAISE", "EXCEPTION", "PERFORM", "GET", "DIAGNOSTICS", "INHERITS", "OF", "ATTACH",
        "DETACH", "CASCADE", "RESTRICT", "NO", "ACTION", "NOTHING", "CONFLICT", "DO", "FORCE", "CONCURRENTLY", "OWNER", "TO", "RENAME",
        "ADD", "COLUMN", "ENABLE", "DISABLE", "ALWAYS", "REPLICA", "IDENTITY", "GENERATED", "STORED", "VIRTUAL", "OVERRIDING", "SYSTEM",
        "VALUE", "LOCAL", "GLOBAL", "SESSION", "VALID", "NOWAIT", "SKIP", "LOCKED", "SHARE", "EXCLUSIVE", "ACCESS",
    ];

    /// <summary>
    /// PostgreSQL error condition names.
    /// </summary>
    public static readonly (string Keyword, string Style)[] ErrorNames =
    [
        ("unique_violation", "hl_error_name"),
        ("foreign_key_violation", "hl_error_name"),
        ("not_null_violation", "hl_error_name"),
        ("check_violation", "hl_error_name"),
        ("exclusion_violation", "hl_error_name"),
        ("restrict_violation", "hl_error_name"),
        ("deadlock_detected", "hl_error_name"),
        ("serialization_failure", "hl_error_name"),
        ("lock_not_available", "hl_error_name"),
        ("data_exception", "hl_error_name"),
        ("division_by_zero", "hl_error_name"),
        ("invalid_text_representation", "hl_error_name"),
        ("numeric_value_out_of_range", "hl_error_name"),
        ("string_data_right_truncation", "hl_error_name"),
        ("datetime_field_overflow", "hl_error_name"),
        ("insufficient_resources", "hl_error_name"),
        ("disk_full", "hl_error_name"),
        ("out_of_memory", "hl_error_name"),
        ("too_many_connections", "hl_error_name"),
        ("statement_too_complex", "hl_error_name"),
        ("too_many_columns", "hl_error_name"),
        ("too_many_arguments", "hl_error_name"),
        ("undefined_table", "hl_error_name"),
        ("undefined_column", "hl_error_name"),
        ("undefined_function", "hl_error_name"),
        ("undefined_object", "hl_error_name"),
        ("duplicate_table", "hl_error_name"),
        ("duplicate_column", "hl_error_name"),
        ("duplicate_object", "hl_error_name"),
        ("duplicate_database", "hl_error_name"),
        ("duplicate_schema", "hl_error_name"),
        ("ambiguous_column", "hl_error_name"),
        ("ambiguous_function", "hl_error_name"),
        ("syntax_error", "hl_error_name"),
        ("connection_exception", "hl_error_name"),
        ("connection_failure", "hl_error_name"),
        ("protocol_violation", "hl_error_name"),
        ("invalid_transaction_state", "hl_error_name"),
        ("read_only_sql_transaction", "hl_error_name"),
        ("no_active_sql_transaction", "hl_error_name"),
        ("system_error", "hl_error_name"),
        ("io_error", "hl_error_name"),
        ("config_file_error", "hl_error_name"),
        ("query_canceled", "hl_error_name"),
        ("admin_shutdown", "hl_error_name"),
        ("crash_shutdown", "hl_error_name"),
        ("cannot_connect_now", "hl_error_name"),
        ("raise_exception", "hl_error_name"),
        ("no_data_found", "hl_error_name"),
        ("too_many_rows", "hl_error_name"),
    ];

    /// <summary>
    /// PostgreSQL backend process names.
    /// </summary>
    public static readonly (string Keyword, string Style)[] BackendNames =
    [
        ("autovacuum", "hl_backend"),
        ("autovacuum launcher", "hl_backend"),
        ("autovacuum worker", "hl_backend"),
        ("checkpointer", "hl_backend"),
        ("background writer", "hl_backend"),
        ("bgwriter", "hl_backend"),
        ("walwriter", "hl_backend"),
        ("wal writer", "hl_backend"),
        ("walsender", "hl_backend"),
        ("wal sender", "hl_backend"),
        ("walreceiver", "hl_backend"),
        ("wal receiver", "hl_backend"),
        ("startup", "hl_backend"),
        ("archiver", "hl_backend"),
        ("parallel worker", "hl_backend"),
        ("parallel leader", "hl_backend"),
        ("logical replication launcher", "hl_backend"),
        ("logical replication worker", "hl_backend"),
        ("stats collector", "hl_backend"),
        ("postmaster", "hl_backend"),
        ("postgres", "hl_backend"),
        ("backend", "hl_backend"),
        ("recovery", "hl_backend"),
    ];

    /// <summary>
    /// Checkpoint keywords and phrases.
    /// </summary>
    public static readonly (string Keyword, string Style)[] Checkpoint =
    [
        ("checkpoint starting", "hl_checkpoint"),
        ("checkpoint complete", "hl_checkpoint"),
        ("checkpoint", "hl_checkpoint"),
        ("time", "hl_checkpoint"),
        ("xlog", "hl_checkpoint"),
        ("wal", "hl_checkpoint"),
        ("shutdown", "hl_checkpoint"),
        ("immediate", "hl_checkpoint"),
        ("force", "hl_checkpoint"),
        ("checkpointer", "hl_checkpoint"),
        ("restartpoint", "hl_checkpoint"),
        ("wrote", "hl_checkpoint"),
        ("sync", "hl_checkpoint"),
        ("synced", "hl_checkpoint"),
        ("total", "hl_checkpoint"),
        ("longest", "hl_checkpoint"),
        ("average", "hl_checkpoint"),
    ];

    /// <summary>
    /// Recovery and startup keywords and phrases.
    /// </summary>
    public static readonly (string Keyword, string Style)[] Recovery =
    [
        ("redo starts at", "hl_recovery"),
        ("redo done at", "hl_recovery"),
        ("redo", "hl_recovery"),
        ("recovery", "hl_recovery"),
        ("recovering", "hl_recovery"),
        ("recovered", "hl_recovery"),
        ("consistent recovery state", "hl_recovery"),
        ("ready to accept connections", "hl_recovery"),
        ("ready to accept read only connections", "hl_recovery"),
        ("entering standby mode", "hl_recovery"),
        ("starting point-in-time recovery", "hl_recovery"),
        ("requested", "hl_recovery"),
        ("database system was interrupted", "hl_recovery"),
        ("database system was not properly shut down", "hl_recovery"),
        ("database system is ready", "hl_recovery"),
        ("database system was shut down", "hl_recovery"),
        ("database system is starting up", "hl_recovery"),
        ("startup", "hl_recovery"),
        ("starting up", "hl_recovery"),
        ("shutting down", "hl_recovery"),
        ("shut down", "hl_recovery"),
        ("archive recovery", "hl_recovery"),
        ("restored log file", "hl_recovery"),
        ("selected new timeline", "hl_recovery"),
        ("streaming replication", "hl_recovery"),
        ("primary", "hl_recovery"),
        ("standby", "hl_recovery"),
        ("replica", "hl_recovery"),
    ];

    /// <summary>
    /// Lock type names, share locks first.
    /// </summary>
    public static readonly (string Keyword, string Style)[] Locks =
    [
        ("AccessShareLock", "hl_lock_share"),
        ("RowShareLock", "hl_lock_share"),
        ("ShareLock", "hl_lock_share"),
        ("ShareRowExclusiveLock", "hl_lock_share"),
        ("ShareUpdateExclusiveLock", "hl_lock_share"),
        ("RowExclusiveLock", "hl_lock_exclusive"),
        ("ExclusiveLock", "hl_lock_exclusive"),
        ("AccessExclusiveLock", "hl_lock_exclusive"),
    ];
}
