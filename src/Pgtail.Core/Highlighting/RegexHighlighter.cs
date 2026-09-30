using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles every match of a regular expression.
/// </summary>
/// <param name="name">The unique name.</param>
/// <param name="priority">The processing order.</param>
/// <param name="description">A short description.</param>
/// <param name="regex">The regular expression.</param>
/// <param name="style">The style of every match.</param>
public class RegexHighlighter(string name, int priority, string description, ByteRegex regex, string style) : IHighlighter
{
    /// <inheritdoc />
    public string Name { get; } = name;

    /// <inheritdoc />
    public int Priority { get; } = priority;

    /// <inheritdoc />
    public virtual string Description { get; } = description;

    /// <summary>
    /// The regular expression.
    /// </summary>
    protected ByteRegex Regex { get; } = regex;

    /// <summary>
    /// The style of every match.
    /// </summary>
    protected string Style { get; } = style;

    /// <inheritdoc />
    public virtual IEnumerable<HighlightMatch> FindMatches(Utf8Text text) =>
        LogPattern.Spans(Regex, text).Select(span => new HighlightMatch(span.Start, span.End, Style));
}
