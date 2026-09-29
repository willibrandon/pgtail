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
    // Each alternative captures its prefix, SQL, and trailing whitespace, in that order.
    private static readonly ByteRegex Pattern = ByteRegex.Compile(
        @"(?is)^(?:(.*?duration:\s*[\d.]+\s*ms\s+(?:statement|parse|bind|execute)\s*(?:\S+)?:\s*)(.*?)(\s*)$"
        + @"|(.*?statement:\s*)(.*?)(\s*)$"
        + @"|(.*?execute\s+\S+:\s*)(.*?)(\s*)$"
        + @"|(.*?parse\s+\S+:\s*)(.*?)(\s*)$"
        + @"|(.*?bind\s+\S+:\s*)(.*?)(\s*)$"
        + @"|(DETAIL:\s*)(.*?)(\s*)$)");

    /// <summary>
    /// Detects the SQL in a message.
    /// </summary>
    /// <param name="message">The message.</param>
    /// <returns>The SQL and the text around it, or null when the message has none.</returns>
    public static SqlDetection? Detect(string message)
    {
        ArgumentNullException.ThrowIfNull(message);
        using var text = new Utf8Text(message);
        return Detect(text);
    }

    /// <summary>
    /// Detects the SQL in an encoded message.
    /// </summary>
    /// <param name="text">The encoded message.</param>
    /// <returns>The SQL and the text around it, or null when the message has none.</returns>
    public static SqlDetection? Detect(Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (text.Length == 0 || Pattern.FindCaptures(text.Bytes) is not { } captures)
        {
            return null;
        }

        for (var alternative = 0; alternative < 6; alternative++)
        {
            var group = 1 + (alternative * 3);
            if (captures.GetGroup(group + 1) is not { } sql)
            {
                continue;
            }

            var value = Slice(text, sql);
            if (!string.IsNullOrWhiteSpace(value))
            {
                var prefix = Slice(text, captures.GetGroup(group)!.Value);
                return new SqlDetection(prefix, value, Slice(text, captures.GetGroup(group + 2)!.Value));
            }
        }

        return null;
    }

    private static string Slice(Utf8Text text, ByteRegexMatch match) =>
        text.Text[text.ToCharOffset(match.Start)..text.ToCharOffset(match.End)];
}
