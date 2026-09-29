namespace Pgtail.Commands;

/// <summary>
/// The category and description of each built-in highlighter, as <c>highlight list</c> shows them.
/// </summary>
internal static class HighlighterMetadata
{
    /// <summary>
    /// The built-in highlighters with their categories and descriptions.
    /// </summary>
    public static IReadOnlyList<(string Name, string Category, string Description)> All { get; } =
    [
        ("timestamp", "structural", "Timestamps with date, time, ms, tz"),
        ("pid", "structural", "Process IDs in brackets"),
        ("context", "structural", "DETAIL:, HINT:, CONTEXT: labels"),
        ("sqlstate", "diagnostic", "SQLSTATE error codes"),
        ("error_name", "diagnostic", "Error names (unique_violation, etc.)"),
        ("duration", "performance", "Query durations with threshold coloring"),
        ("memory", "performance", "Memory values (kB, MB, GB)"),
        ("statistics", "performance", "Checkpoint/vacuum statistics"),
        ("identifier", "objects", "Double-quoted identifiers"),
        ("relation", "objects", "Table/index names"),
        ("schema", "objects", "Schema-qualified names"),
        ("lsn", "wal", "Log sequence numbers"),
        ("wal_segment", "wal", "WAL segment filenames"),
        ("txid", "wal", "Transaction IDs"),
        ("connection", "connection", "Connection info (host, port, user)"),
        ("ip", "connection", "IP addresses"),
        ("backend", "connection", "Backend process types"),
        ("sql_keyword", "sql", "SQL keywords"),
        ("sql_string", "sql", "SQL strings"),
        ("sql_number", "sql", "SQL numbers"),
        ("sql_param", "sql", "SQL parameters ($1, $2)"),
        ("sql_operator", "sql", "SQL operators"),
        ("lock_type", "lock", "Lock type names"),
        ("lock_wait", "lock", "Lock wait info"),
        ("checkpoint", "checkpoint", "Checkpoint messages"),
        ("recovery", "checkpoint", "Recovery messages"),
        ("boolean", "misc", "Boolean values"),
        ("null", "misc", "NULL keyword"),
        ("oid", "misc", "Object IDs"),
        ("path", "misc", "File paths"),
    ];

    /// <summary>
    /// Sample lines for <c>highlight preview</c>: the highlighters each shows, the line, and a description.
    /// </summary>
    public static IReadOnlyList<(string[] Highlighters, string Line, string Description)> PreviewSamples { get; } =
    [
        (["timestamp", "pid"], "2024-01-15 14:30:45.123 UTC [12345] LOG:  database system is ready",
            "Timestamp with timezone and process ID"),
        (["context"], "DETAIL:  Key (id)=(42) already exists.", "Context label (DETAIL:)"),
        (["context"], "HINT:  Use UPSERT to handle duplicates.", "Context label (HINT:)"),
        (["sqlstate"], "ERROR:  23505: duplicate key value violates unique constraint \"users_pkey\"", "SQLSTATE error code"),
        (["error_name"], "ERROR:  unique_violation: duplicate key value", "Error name (unique_violation)"),
        (["duration"], "LOG:  duration: 45.123 ms  statement: SELECT * FROM users", "Fast query duration"),
        (["duration"], "LOG:  duration: 150.456 ms  statement: SELECT * FROM orders", "Slow query duration"),
        (["duration"], "LOG:  duration: 5500.789 ms  statement: SELECT * FROM large_table", "Critical query duration"),
        (["memory"], "LOG:  temporary file: 15 MB used for sort", "Memory/size value"),
        (["statistics"], "LOG:  checkpoint complete: wrote 1500 buffers (9.2%)", "Checkpoint statistics with percentage"),
        (["identifier"], "ERROR:  column \"user_name\" does not exist", "Double-quoted identifier"),
        (["relation"], "ERROR:  relation \"orders\" does not exist", "Relation name"),
        (["schema"], "LOG:  autovacuum: analyzing public.users", "Schema-qualified name"),
        (["lsn"], "LOG:  redo starts at 0/1234ABCD", "Log sequence number (LSN)"),
        (["wal_segment"], "LOG:  archived transaction log file 000000010000000100000023", "WAL segment filename (24-char hex)"),
        (["txid"], "DETAIL:  xmin: 1234567, xmax: 1234570", "Transaction ID"),
        (["connection", "ip"], "LOG:  connection authorized: user=postgres database=mydb host=192.168.1.100 port=5432",
            "Connection info with IP address"),
        (["ip"], "LOG:  connection from 2001:db8::1 rejected", "IPv6 address"),
        (["backend"], "LOG:  autovacuum launcher started", "Backend process type"),
        (["sql_keyword", "sql_string", "sql_number"], "LOG:  statement: SELECT id, 'hello' FROM users WHERE id = 42",
            "SQL keywords, strings, and numbers"),
        (["sql_param"], "LOG:  execute <unnamed>: SELECT * FROM users WHERE id = $1", "SQL parameter placeholder"),
        (["sql_operator"], "LOG:  statement: SELECT name || ' ' || email FROM users", "SQL operator (||)"),
        (["lock_type"], "LOG:  process 12345 acquired ShareLock on relation 16384", "Lock type name (ShareLock)"),
        (["lock_wait"], "LOG:  process 12345 still waiting for ExclusiveLock after 5000.123 ms", "Lock wait information"),
        (["checkpoint"], "LOG:  checkpoint starting: time", "Checkpoint message"),
        (["recovery"], "LOG:  redo done at 0/1234ABCD", "Recovery message"),
        (["boolean"], "LOG:  setting log_connections to on", "Boolean value (on)"),
        (["null"], "LOG:  parameter value is NULL", "NULL keyword"),
        (["oid"], "LOG:  dropping objects with OID 16384", "Object ID (OID)"),
        (["path"], "LOG:  redirecting log output to /var/log/postgresql/postgresql-17-main.log", "File path"),
    ];

    /// <summary>
    /// The description of a built-in highlighter.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>The description, or null for an unknown name.</returns>
    public static string? Describe(string name) => All.FirstOrDefault(item => item.Name == name).Description;

    /// <summary>
    /// A category's name as a heading, such as <c>WAL</c> or <c>Structural</c>.
    /// </summary>
    /// <param name="category">The category.</param>
    /// <returns>The heading.</returns>
    public static string Heading(string category) => category switch
    {
        "wal" => "WAL",
        "sql" => "SQL",
        _ => char.ToUpperInvariant(category[0]) + category[1..],
    };
}
