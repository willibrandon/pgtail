using Pgtail.Matching;

namespace Pgtail.Filtering;

/// <summary>
/// A pattern whose matches are shown with a highlighted background.
/// </summary>
/// <param name="pattern">The compiled pattern.</param>
public sealed class RegexHighlight(LogPattern pattern)
{
    /// <summary>
    /// The pattern as typed.
    /// </summary>
    public string Pattern => Compiled.Pattern;

    /// <summary>
    /// Whether the pattern matches case.
    /// </summary>
    public bool CaseSensitive => Compiled.CaseSensitive;

    /// <summary>
    /// The compiled pattern.
    /// </summary>
    public LogPattern Compiled { get; } = pattern;

    /// <summary>
    /// Compiles a highlight.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The highlight.</returns>
    /// <exception cref="FormatException">The pattern is not a valid regular expression.</exception>
    public static RegexHighlight Create(string pattern, bool caseSensitive = false) => new(LogPattern.Compile(pattern, caseSensitive));

    /// <summary>
    /// The character ranges of every match in a text.
    /// </summary>
    /// <param name="text">The encoded text.</param>
    /// <returns>The ranges, in order.</returns>
    public IReadOnlyList<(int Start, int End)> FindSpans(Utf8Text text) => Compiled.FindSpans(text);
}
