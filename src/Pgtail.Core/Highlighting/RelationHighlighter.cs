using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles the name of a relation after a keyword such as <c>relation</c>, <c>table</c>, or <c>index</c>.
/// </summary>
public sealed class RelationHighlighter() : RegexHighlighter("relation", 410, "Table/index/sequence names (relation X, table Y)",
    HighlightPatterns.Relation, "hl_relation")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        foreach (var groups in LogPattern.Captures(Regex, text))
        {
            if (groups[2] is { } name)
            {
                yield return new HighlightMatch(name.Start, name.End, Style);
            }
        }
    }
}
