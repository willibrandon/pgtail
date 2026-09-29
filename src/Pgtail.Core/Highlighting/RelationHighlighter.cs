using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles the name of a relation after a keyword such as <c>relation</c>, <c>table</c>, or <c>index</c>.
/// </summary>
public sealed class RelationHighlighter() : RegexHighlighter("relation", 410, "Table/index/sequence names (relation X, table Y)",
    HighlightPatterns.Relation(), "hl_relation")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in Regex.Matches(text))
        {
            var name = match.Groups[2];
            if (name.Success)
            {
                yield return new HighlightMatch(name.Index, name.Index + name.Length, Style);
            }
        }
    }
}
