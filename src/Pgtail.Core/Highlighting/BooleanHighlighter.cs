using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles on, true, and yes as true values and off, false, and no as false values.
/// </summary>
public sealed class BooleanHighlighter() : RegexHighlighter("boolean", 1000, "Boolean values (on/off, true/false, yes/no)",
    HighlightPatterns.Boolean, "hl_bool_true")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        foreach ((int Start, int End)?[] groups in LogPattern.Captures(Regex, text))
        {
            if (groups[1] is not { } value)
            {
                continue;
            }

            string word = text.Text[value.Start..value.End].ToLowerInvariant();
            yield return new HighlightMatch(value.Start, value.End, word is "on" or "true" or "yes" ? "hl_bool_true" : "hl_bool_false");
        }
    }
}
