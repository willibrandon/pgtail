using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles SQL string literals, dollar-quoted or single-quoted.
/// </summary>
/// <remarks>
/// Dollar-quoted strings look like <c>$$...$$</c> or <c>$tag$...$tag$</c>; single-quoted strings double a quote to
/// include one. A dollar-quoted string opens with a dollar sign, an optional tag, and a dollar sign, and closes at the first
/// <c>$tag$</c> or <c>$$</c> after it. A single-quoted string whose closing quote is missing ends at the last doubled
/// quote, the first quote of which then closes it.
/// </remarks>
public sealed class SqlStringHighlighter : IHighlighter
{
    /// <inheritdoc />
    public string Name => "sql_string";

    /// <inheritdoc />
    public int Priority => 720;

    /// <inheritdoc />
    public string Description => "SQL string literals ('...', $$...$$)";

    /// <inheritdoc />
    public IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var s = text.Text;
        var position = 0;
        while (position < s.Length)
        {
            var end = s[position] switch
            {
                '$' => DollarQuoted(s, position),
                '\'' => SingleQuoted(s, position),
                _ => -1,
            };

            if (end > position)
            {
                yield return new HighlightMatch(position, end, "sql_string");
                position = end;
            }
            else
            {
                position++;
            }
        }
    }

    private static int DollarQuoted(string s, int start)
    {
        var tagEnd = start + 1;
        if (tagEnd < s.Length && (char.IsAsciiLetter(s[tagEnd]) || s[tagEnd] == '_'))
        {
            while (tagEnd < s.Length && (char.IsAsciiLetterOrDigit(s[tagEnd]) || s[tagEnd] == '_'))
            {
                tagEnd++;
            }
        }

        if (tagEnd >= s.Length || s[tagEnd] != '$')
        {
            return -1;
        }

        var tag = s[(start + 1)..tagEnd];
        for (var i = tagEnd + 1; i < s.Length; i++)
        {
            if (s[i] != '$')
            {
                continue;
            }

            if (tag.Length > 0 && string.CompareOrdinal(s, i + 1, tag, 0, tag.Length) == 0 && i + 1 + tag.Length < s.Length
                && s[i + 1 + tag.Length] == '$')
            {
                return i + tag.Length + 2;
            }

            if (i + 1 < s.Length && s[i + 1] == '$')
            {
                return i + 2;
            }
        }

        return -1;
    }

    private static int SingleQuoted(string s, int start)
    {
        var lastPair = -1;
        var i = start + 1;
        while (i < s.Length)
        {
            if (s[i] != '\'')
            {
                i++;
            }
            else if (i + 1 < s.Length && s[i + 1] == '\'')
            {
                lastPair = i;
                i += 2;
            }
            else
            {
                return i + 1;
            }
        }

        return lastPair >= 0 ? lastPair + 1 : -1;
    }
}
