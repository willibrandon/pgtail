using Scout.Text.Regex;

namespace Pgtail.Highlighting;

/// <summary>
/// The regular expressions of the built-in highlighters, compiled once and shared.
/// </summary>
internal static class HighlightPatterns
{
    /// <summary>
    /// Timestamps: date (1), time (2), fraction (3), and zone (4).
    /// </summary>
    public static readonly ByteRegex Timestamp =
        ByteRegex.Compile(@"(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})(?:\.(\d{3,6}))?(?: ?([A-Z]{2,4}|[+-]\d{2}:?\d{2}))?");

    /// <summary>
    /// Process IDs in brackets.
    /// </summary>
    public static readonly ByteRegex Pid = ByteRegex.Compile(@"\[(\d+)(?:-\d+)?\]");

    /// <summary>
    /// Context labels such as <c>DETAIL:</c>.
    /// </summary>
    public static readonly ByteRegex ContextLabel = ByteRegex.Compile("(DETAIL|HINT|CONTEXT|STATEMENT|QUERY|LOCATION):");

    /// <summary>
    /// Five character SQLSTATE codes (1).
    /// </summary>
    public static readonly ByteRegex SqlState = ByteRegex.Compile(@"\b([0-9A-Z]{5})\b");

    /// <summary>
    /// Durations in milliseconds: the value is group 1.
    /// </summary>
    public static readonly ByteRegex Duration = ByteRegex.Compile(@"\b(\d+(?:\.\d+)?)\s*(ms)\b");

    /// <summary>
    /// Memory sizes: value (1) and unit (2).
    /// </summary>
    public static readonly ByteRegex Memory = ByteRegex.Compile(@"(?i)(\d+(?:\.\d+)?)\s*(bytes|kB|MB|GB|TB)\b");

    /// <summary>
    /// Counts of buffers, pages, tuples, and similar statistics.
    /// </summary>
    public static readonly ByteRegex Statistics =
        ByteRegex.Compile(@"(?i)\b(\d+(?:\.\d+)?)\s*(buffers?|pages?|tuples?|rows?|transactions?|blocks?|segments?|files?|%)");

    /// <summary>
    /// Double-quoted identifiers.
    /// </summary>
    public static readonly ByteRegex Identifier = ByteRegex.Compile("\"(?:[^\"\\\\]|\"\"|\\\\.)*\"");

    /// <summary>
    /// Relation names after a keyword such as <c>relation</c> or <c>table</c>; the name is group 2.
    /// </summary>
    public static readonly ByteRegex Relation = ByteRegex.Compile(
        "(?i)\\b(relation|table|index|sequence|constraint|view|materialized view|foreign table)\\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?");

    /// <summary>
    /// Schema-qualified names.
    /// </summary>
    public static readonly ByteRegex Schema = ByteRegex.Compile("\\b([a-zA-Z_][a-zA-Z0-9_]*)\\.(?:\"[^\"]+\"|[a-zA-Z_][a-zA-Z0-9_]*)");

    /// <summary>
    /// Log sequence numbers: segment (1) and offset (2).
    /// </summary>
    public static readonly ByteRegex Lsn = ByteRegex.Compile(@"\b([0-9A-Fa-f]{1,8})/([0-9A-Fa-f]{1,8})\b");

    /// <summary>
    /// WAL segment file names.
    /// </summary>
    public static readonly ByteRegex WalSegment = ByteRegex.Compile(@"\b[0-9A-Fa-f]{24}\b");

    /// <summary>
    /// Transaction IDs after <c>xid</c>, <c>xmin</c>, <c>xmax</c>, or <c>transaction</c>.
    /// </summary>
    public static readonly ByteRegex Txid = ByteRegex.Compile(@"(?i)\b(xid|xmin|xmax|transaction)\s*:?\s*(\d+)\b");

    /// <summary>
    /// Connection settings such as <c>host=...</c>; the setting is group 1.
    /// </summary>
    public static readonly ByteRegex Connection =
        ByteRegex.Compile("(?i)\\b(host|port|user|database|application_name)=(\"[^\"]*\"|[^\\s,]+)");

    /// <summary>
    /// IPv4 and IPv6 addresses with optional prefix lengths.
    /// </summary>
    public static readonly ByteRegex Ip = ByteRegex.Compile(
        @"(?:\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/\d{1,2})?\b)"
        + @"|(?:\b(?:[0-9A-Fa-f]{1,4}:){1,7}[0-9A-Fa-f]{1,4}\b|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4}"
        + @"|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}(?:/\d{1,3})?)");

    /// <summary>
    /// Lock wait phrases.
    /// </summary>
    public static readonly ByteRegex LockWait =
        ByteRegex.Compile(@"(?i)\b(waiting for|acquired|still waiting for|deadlock detected|process \d+ still waiting|lock timeout)\b");

    /// <summary>
    /// Boolean words (1).
    /// </summary>
    public static readonly ByteRegex Boolean = ByteRegex.Compile(@"(?i)\b(on|off|true|false|yes|no)\b");

    /// <summary>
    /// The NULL keyword.
    /// </summary>
    public static readonly ByteRegex Null = ByteRegex.Compile(@"(?i)\bNULL\b");

    /// <summary>
    /// Object IDs after <c>OID</c>, <c>regclass</c>, <c>regtype</c>, or <c>regproc</c>.
    /// </summary>
    public static readonly ByteRegex Oid = ByteRegex.Compile(@"(?i)\b(OID|regclass|regtype|regproc)\s*[=:]?\s*(\d+)\b");

    /// <summary>
    /// Unix file paths with at least two segments.
    /// </summary>
    public static readonly ByteRegex Path = ByteRegex.Compile(@"\B(/(?:[\w.-]+/)+[\w.-]+)\b");

    /// <summary>
    /// Query parameters such as <c>$1</c>.
    /// </summary>
    public static readonly ByteRegex SqlParam = ByteRegex.Compile(@"\$\d+");

    /// <summary>
    /// SQL numeric literals.
    /// </summary>
    public static readonly ByteRegex SqlNumber = ByteRegex.Compile(@"\b(?:0x[0-9A-Fa-f]+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\b");

    /// <summary>
    /// SQL operators.
    /// </summary>
    public static readonly ByteRegex SqlOperator = ByteRegex.Compile(@"<>|!=|<=|>=|\|\||::|[=<>+\-*/%!|:&^~@#]");
}
