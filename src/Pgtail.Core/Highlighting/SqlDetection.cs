namespace Pgtail.Highlighting;

/// <summary>
/// The SQL found in a log message and the text around it.
/// </summary>
/// <param name="Prefix">The text before the SQL, such as <c>statement: </c>.</param>
/// <param name="Sql">The SQL.</param>
/// <param name="Suffix">Trailing whitespace after the SQL.</param>
public sealed record SqlDetection(string Prefix, string Sql, string Suffix);
