using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles the capture groups of a regular expression, each in its own style.
/// </summary>
/// <param name="name">The unique name.</param>
/// <param name="priority">The processing order.</param>
/// <param name="description">A short description.</param>
/// <param name="regex">The regular expression.</param>
/// <param name="groupStyles">The style of each group by index, in the order groups are reported.</param>
public sealed class GroupedRegexHighlighter(
    string name,
    int priority,
    string description,
    ByteRegex regex,
    IReadOnlyList<(int Group, string Style)> groupStyles) : IHighlighter
{
    /// <inheritdoc />
    public string Name { get; } = name;

    /// <inheritdoc />
    public int Priority { get; } = priority;

    /// <inheritdoc />
    public string Description { get; } = description;

    /// <inheritdoc />
    public IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        foreach ((int Start, int End)?[] groups in LogPattern.Captures(regex, text))
        {
            foreach ((int group, string style) in groupStyles)
            {
                if (group < groups.Length && groups[group] is { } span)
                {
                    yield return new HighlightMatch(span.Start, span.End, style);
                }
            }
        }
    }
}
