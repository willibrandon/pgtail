namespace Pgtail.Highlighting;

/// <summary>
/// The 30 built-in highlighters.
/// </summary>
public static class BuiltInHighlighters
{
    /// <summary>
    /// The built-in highlighter names in priority order.
    /// </summary>
    public static IReadOnlyList<string> Names { get; } =
    [
        "timestamp", "pid", "context", "sqlstate", "error_name", "duration", "memory", "statistics", "identifier", "relation",
        "schema", "lsn", "wal_segment", "txid", "connection", "ip", "backend", "sql_keyword", "sql_string", "sql_number",
        "sql_param", "sql_operator", "lock_type", "lock_wait", "checkpoint", "recovery", "boolean", "null", "oid", "path",
    ];

    /// <summary>
    /// Creates every built-in highlighter.
    /// </summary>
    /// <param name="slow">The slow duration threshold in milliseconds.</param>
    /// <param name="verySlow">The very slow duration threshold in milliseconds.</param>
    /// <param name="critical">The critical duration threshold in milliseconds.</param>
    /// <returns>The highlighters in priority order.</returns>
    public static IReadOnlyList<IHighlighter> Create(long slow = 100, long verySlow = 500, long critical = 5000)
    {
        var sqlKeywords = HighlightKeywords.SqlDml.Concat(HighlightKeywords.SqlDdl).Concat(HighlightKeywords.SqlDcl)
            .Concat(HighlightKeywords.SqlTcl).Concat(HighlightKeywords.SqlOther).Select(keyword => (keyword, "sql_keyword")).ToList();
        int sqlKeywordCount = HighlightKeywords.SqlDml.Length + HighlightKeywords.SqlDdl.Length + HighlightKeywords.SqlDcl.Length
            + HighlightKeywords.SqlTcl.Length + HighlightKeywords.SqlOther.Length;
        return
        [
            new GroupedRegexHighlighter("timestamp", 100, "Timestamps with date, time, milliseconds, timezone",
                HighlightPatterns.Timestamp,
                [(1, "hl_timestamp_date"), (2, "hl_timestamp_time"), (3, "hl_timestamp_ms"), (4, "hl_timestamp_tz")]),
            new RegexHighlighter("pid", 110, "Process IDs in brackets [12345] or [12345-1]", HighlightPatterns.Pid, "hl_pid"),
            new RegexHighlighter("context", 120, "Context labels (DETAIL:, HINT:, CONTEXT:, etc.)", HighlightPatterns.ContextLabel,
                "hl_context"),
            new SqlStateHighlighter(),
            new KeywordHighlighter("error_name", 210, $"PostgreSQL error names ({HighlightKeywords.ErrorNames.Length} patterns)",
                HighlightKeywords.ErrorNames),
            new DurationHighlighter(slow, verySlow, critical),
            new GroupedRegexHighlighter("memory", 310, "Memory sizes (bytes, kB, MB, GB, TB)", HighlightPatterns.Memory,
                [(1, "hl_memory_value"), (2, "hl_memory_unit")]),
            new RegexHighlighter("statistics", 320, "Checkpoint/vacuum statistics (buffers, tuples, pages, %)",
                HighlightPatterns.Statistics, "hl_statistics"),
            new RegexHighlighter("identifier", 400, "Double-quoted identifiers (\"table_name\")", HighlightPatterns.Identifier,
                "hl_identifier"),
            new RelationHighlighter(),
            new RegexHighlighter("schema", 420, "Schema-qualified names (schema.table)", HighlightPatterns.Schema, "hl_schema"),
            new GroupedRegexHighlighter("lsn", 500, "Log Sequence Numbers (0/12345678)", HighlightPatterns.Lsn,
                [(1, "hl_lsn_segment"), (2, "hl_lsn_offset")]),
            new RegexHighlighter("wal_segment", 510, "WAL segment filenames (24-char hex)", HighlightPatterns.WalSegment,
                "hl_wal_segment"),
            new RegexHighlighter("txid", 520, "Transaction IDs (xid, xmin, xmax, transaction N)", HighlightPatterns.Txid, "hl_txid"),
            new ConnectionHighlighter(),
            new RegexHighlighter("ip", 610, "IP addresses (IPv4, IPv6, CIDR notation)", HighlightPatterns.Ip, "hl_ip"),
            new KeywordHighlighter("backend", 620, "Backend process names (autovacuum, checkpointer, etc.)",
                HighlightKeywords.BackendNames),
            new RegexHighlighter("sql_param", 700, "Query parameters ($1, $2, etc.)", HighlightPatterns.SqlParam, "hl_param"),
            new KeywordHighlighter("sql_keyword", 710, $"SQL keywords ({sqlKeywordCount} keywords)", sqlKeywords),
            new SqlStringHighlighter(),
            new RegexHighlighter("sql_number", 730, "SQL numeric literals (42, 3.14, 1e10)", HighlightPatterns.SqlNumber, "sql_number"),
            new RegexHighlighter("sql_operator", 740, "SQL operators (=, <>, ||, ::, etc.)", HighlightPatterns.SqlOperator,
                "sql_operator"),
            new KeywordHighlighter("lock_type", 800, "Lock type names (share vs exclusive)", HighlightKeywords.Locks, caseSensitive: true),
            new RegexHighlighter("lock_wait", 810, "Lock wait information (waiting for, acquired, deadlock)", HighlightPatterns.LockWait,
                "hl_lock_wait"),
            new KeywordHighlighter("checkpoint", 900, "Checkpoint messages (starting, complete, stats)", HighlightKeywords.Checkpoint),
            new KeywordHighlighter("recovery", 910, "Recovery messages (redo, startup, standby)", HighlightKeywords.Recovery),
            new BooleanHighlighter(),
            new RegexHighlighter("null", 1010, "NULL keyword", HighlightPatterns.Null, "hl_null"),
            new RegexHighlighter("oid", 1020, "Object IDs (OID 12345, regclass)", HighlightPatterns.Oid, "hl_oid"),
            new RegexHighlighter("path", 1030, "Unix file paths (/var/lib/postgresql/...)", HighlightPatterns.Path, "hl_path"),
        ];
    }
}
