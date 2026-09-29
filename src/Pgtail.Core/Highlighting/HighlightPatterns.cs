using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// The regular expressions of the built-in highlighters, compiled ahead of time.
/// </summary>
internal static partial class HighlightPatterns
{
    /// <summary>
    /// Timestamps: date, time, fraction, and zone groups.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"(?<date>\d{4}-\d{2}-\d{2})[T ](?<time>\d{2}:\d{2}:\d{2})(?:\.(?<ms>\d{3,6}))?"
        + @"(?: ?(?<tz>[A-Z]{2,4}|[+-]\d{2}:?\d{2}))?")]
    public static partial Regex Timestamp();

    /// <summary>
    /// Process IDs in brackets.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\[(\d+)(?:-\d+)?\]")]
    public static partial Regex Pid();

    /// <summary>
    /// Context labels such as <c>DETAIL:</c>.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex("(DETAIL|HINT|CONTEXT|STATEMENT|QUERY|LOCATION):")]
    public static partial Regex ContextLabel();

    /// <summary>
    /// Five character SQLSTATE codes.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b([0-9A-Z]{5})\b")]
    public static partial Regex SqlState();

    /// <summary>
    /// Durations in milliseconds.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(\d+(?:\.\d+)?)\s*(ms)\b")]
    public static partial Regex Duration();

    /// <summary>
    /// Memory sizes: value and unit groups.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"(?<value>\d+(?:\.\d+)?)\s*(?<unit>bytes|kB|MB|GB|TB)\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Memory();

    /// <summary>
    /// Counts of buffers, pages, tuples, and similar statistics.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(\d+(?:\.\d+)?)\s*(buffers?|pages?|tuples?|rows?|transactions?|blocks?|segments?|files?|%)",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Statistics();

    /// <summary>
    /// Double-quoted identifiers.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex("\"(?:[^\"\\\\]|\"\"|\\\\.)*\"")]
    public static partial Regex Identifier();

    /// <summary>
    /// Relation names after a keyword such as <c>relation</c> or <c>table</c>; the name is group 2.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex("\\b(relation|table|index|sequence|constraint|view|materialized view|foreign table)\\s+\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Relation();

    /// <summary>
    /// Schema-qualified names.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex("\\b([a-zA-Z_][a-zA-Z0-9_]*)\\.(?:\"[^\"]+\"|[a-zA-Z_][a-zA-Z0-9_]*)")]
    public static partial Regex Schema();

    /// <summary>
    /// Log sequence numbers: segment and offset groups.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(?<segment>[0-9A-Fa-f]{1,8})/(?<offset>[0-9A-Fa-f]{1,8})\b")]
    public static partial Regex Lsn();

    /// <summary>
    /// WAL segment file names.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b[0-9A-Fa-f]{24}\b")]
    public static partial Regex WalSegment();

    /// <summary>
    /// Transaction IDs after <c>xid</c>, <c>xmin</c>, <c>xmax</c>, or <c>transaction</c>.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(xid|xmin|xmax|transaction)\s*:?\s*(\d+)\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Txid();

    /// <summary>
    /// Connection settings such as <c>host=...</c>; the setting is group 1.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex("\\b(host|port|user|database|application_name)=(\"[^\"]*\"|[^\\s,]+)",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Connection();

    /// <summary>
    /// IPv4 and IPv6 addresses with optional prefix lengths.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"(?:\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?:/\d{1,2})?\b)"
        + @"|(?:\b(?:[0-9A-Fa-f]{1,4}:){1,7}[0-9A-Fa-f]{1,4}\b|::(?:[0-9A-Fa-f]{1,4}:){0,6}[0-9A-Fa-f]{1,4}"
        + @"|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}(?:/\d{1,3})?)")]
    public static partial Regex Ip();

    /// <summary>
    /// Lock wait phrases.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(waiting for|acquired|still waiting for|deadlock detected|process \d+ still waiting|lock timeout)\b",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex LockWait();

    /// <summary>
    /// Boolean words.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(on|off|true|false|yes|no)\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Boolean();

    /// <summary>
    /// The NULL keyword.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\bNULL\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Null();

    /// <summary>
    /// Object IDs after <c>OID</c>, <c>regclass</c>, <c>regtype</c>, or <c>regproc</c>.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(OID|regclass|regtype|regproc)\s*[=:]?\s*(\d+)\b", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    public static partial Regex Oid();

    /// <summary>
    /// Unix file paths with at least two segments.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\B(/(?:[\w.-]+/)+[\w.-]+)\b")]
    public static partial Regex Path();

    /// <summary>
    /// Query parameters such as <c>$1</c>.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\$\d+")]
    public static partial Regex SqlParam();

    /// <summary>
    /// SQL string literals, dollar-quoted or single-quoted.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\$([a-zA-Z_][a-zA-Z0-9_]*)?\$.*?\$\1?\$|'(?:[^']|'')*'", RegexOptions.Singleline)]
    public static partial Regex SqlString();

    /// <summary>
    /// SQL numeric literals.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"\b(?:0x[0-9A-Fa-f]+|[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)\b")]
    public static partial Regex SqlNumber();

    /// <summary>
    /// SQL operators.
    /// </summary>
    /// <returns>The expression.</returns>
    [GeneratedRegex(@"<>|!=|<=|>=|\|\||::|[=<>+\-*/%!|:&^~@#]")]
    public static partial Regex SqlOperator();
}
