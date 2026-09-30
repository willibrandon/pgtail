using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles the name of a relation after a keyword such as <c>relation</c>, <c>table</c>, or <c>index</c>.
/// </summary>
public sealed class RelationHighlighter() : RegexHighlighter("relation", 410, "Table/index/sequence names (relation X, table Y)",
    HighlightPatterns.Relation, "hl_relation")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(Utf8Text text) =>
        LogPattern.Captures(Regex, text)
            .Select(groups => groups[2])
            .OfType<(int Start, int End)>()
            .Select(name => new HighlightMatch(name.Start, name.End, Style));
}
