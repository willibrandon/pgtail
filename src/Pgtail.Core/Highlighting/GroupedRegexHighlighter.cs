using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles the named groups of a regular expression, each in its own style.
/// </summary>
/// <param name="name">The unique name.</param>
/// <param name="priority">The processing order.</param>
/// <param name="description">A short description.</param>
/// <param name="regex">The regular expression with named groups.</param>
/// <param name="groupStyles">The style of each group, in the order groups are reported.</param>
public sealed class GroupedRegexHighlighter(
    string name,
    int priority,
    string description,
    Regex regex,
    IReadOnlyList<(string Group, string Style)> groupStyles) : IHighlighter
{
    /// <inheritdoc />
    public string Name { get; } = name;

    /// <inheritdoc />
    public int Priority { get; } = priority;

    /// <inheritdoc />
    public string Description { get; } = description;

    /// <inheritdoc />
    public IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in regex.Matches(text))
        {
            foreach (var (group, style) in groupStyles)
            {
                var captured = match.Groups[group];
                if (captured.Success)
                {
                    yield return new HighlightMatch(captured.Index, captured.Index + captured.Length, style);
                }
            }
        }
    }
}
