using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Highlighting;

/// <summary>
/// Finds SQL in log messages so SQL highlighters touch only the SQL.
/// </summary>
/// <remarks>
/// SQL follows <c>statement:</c>, <c>execute name:</c>, <c>parse name:</c>, <c>bind name:</c>, the same after
/// <c>duration: N ms</c>, or a leading <c>DETAIL:</c>. Keeping SQL highlighters inside it stops words such as
/// "for" or "at" in ordinary messages from being styled as keywords.
/// </remarks>
public static class SqlDetector
{
    // The prefixes that introduce SQL, tried in this order; the SQL runs from the end of the first one found to the end
    // of the message. Plain searches without captures keep this cheap for the many lines that have no SQL.
    private static readonly ByteRegex[] Prefixes =
    [
        ByteRegex.Compile(@"(?i)duration:\s*[\d.]+\s*ms\s+(?:statement|parse|bind|execute)\s*(?:\S+)?:\s*"),
        ByteRegex.Compile(@"(?i)statement:\s*"),
        ByteRegex.Compile(@"(?i)execute\s+\S+:\s*"),
        ByteRegex.Compile(@"(?i)parse\s+\S+:\s*"),
        ByteRegex.Compile(@"(?i)bind\s+\S+:\s*"),
        ByteRegex.Compile(@"(?i)^DETAIL:\s*"),
    ];

    /// <summary>
    /// Finds the SQL in a message.
    /// </summary>
    /// <param name="message">The message.</param>
    /// <returns>The prefix, SQL, and trailing whitespace, or null when the message has no SQL.</returns>
    public static SqlDetection? Detect(string message)
    {
        ArgumentNullException.ThrowIfNull(message);
        using var text = new Utf8Text(message);
        return Detect(text);
    }

    /// <summary>
    /// Finds the SQL in a message already encoded as UTF-8.
    /// </summary>
    /// <param name="text">The message.</param>
    /// <returns>The prefix, SQL, and trailing whitespace, or null when the message has no SQL.</returns>
    public static SqlDetection? Detect(Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (text.Length == 0)
        {
            return null;
        }

        var bytes = text.Bytes;
        foreach (var prefix in Prefixes)
        {
            if (prefix.Find(bytes) is not { } match)
            {
                continue;
            }

            var sqlStart = text.ToCharOffset(match.End);
            var rest = text.Text[sqlStart..];
            var sql = rest.TrimEnd();
            if (sql.Length > 0)
            {
                return new SqlDetection(text.Text[..sqlStart], sql, rest[sql.Length..]);
            }
        }

        return null;
    }
}
