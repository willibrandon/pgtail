using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles on, true, and yes as true values and off, false, and no as false values.
/// </summary>
public sealed class BooleanHighlighter() : RegexHighlighter("boolean", 1000, "Boolean values (on/off, true/false, yes/no)",
    HighlightPatterns.Boolean(), "hl_bool_true")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in Regex.Matches(text))
        {
            var value = match.Groups[1];
            var style = value.Value.ToLowerInvariant() is "on" or "true" or "yes" ? "hl_bool_true" : "hl_bool_false";
            yield return new HighlightMatch(value.Index, value.Index + value.Length, style);
        }
    }
}
