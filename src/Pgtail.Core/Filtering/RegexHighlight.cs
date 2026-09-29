using System.Text.RegularExpressions;

namespace Pgtail.Filtering;

/// <summary>
/// A pattern whose matches are shown with a highlighted background.
/// </summary>
public sealed class RegexHighlight
{
    private RegexHighlight(string pattern, bool caseSensitive, Regex regex)
    {
        Pattern = pattern;
        CaseSensitive = caseSensitive;
        Regex = regex;
    }

    /// <summary>
    /// The pattern as typed.
    /// </summary>
    public string Pattern { get; }

    /// <summary>
    /// Whether the pattern matches case.
    /// </summary>
    public bool CaseSensitive { get; }

    /// <summary>
    /// The compiled pattern.
    /// </summary>
    public Regex Regex { get; }

    /// <summary>
    /// Compiles a highlight.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The highlight.</returns>
    /// <exception cref="ArgumentException">The pattern is not a valid regular expression.</exception>
    public static RegexHighlight Create(string pattern, bool caseSensitive = false)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        return new RegexHighlight(pattern, caseSensitive, PatternSyntax.Compile(pattern, caseSensitive));
    }

    /// <summary>
    /// The start and end of every match in a text.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The spans, in order.</returns>
    public IReadOnlyList<(int Start, int End)> FindSpans(string text) =>
        [.. Regex.Matches(text).Select(match => (match.Index, match.Index + match.Length))];
}
