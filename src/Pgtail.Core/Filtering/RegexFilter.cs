using System.Text.RegularExpressions;

namespace Pgtail.Filtering;

/// <summary>
/// A compiled regex filter.
/// </summary>
public sealed class RegexFilter
{
    private RegexFilter(string pattern, FilterType type, bool caseSensitive, Regex regex)
    {
        Pattern = pattern;
        Type = type;
        CaseSensitive = caseSensitive;
        Regex = regex;
    }

    /// <summary>
    /// The pattern as typed.
    /// </summary>
    public string Pattern { get; }

    /// <summary>
    /// How the filter combines with the others.
    /// </summary>
    public FilterType Type { get; }

    /// <summary>
    /// Whether the pattern matches case.
    /// </summary>
    public bool CaseSensitive { get; }

    /// <summary>
    /// The compiled pattern.
    /// </summary>
    public Regex Regex { get; }

    /// <summary>
    /// Compiles a filter.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="type">How the filter combines.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The filter.</returns>
    /// <exception cref="ArgumentException">The pattern is not a valid regular expression.</exception>
    public static RegexFilter Create(string pattern, FilterType type, bool caseSensitive = false)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        return new RegexFilter(pattern, type, caseSensitive, PatternSyntax.Compile(pattern, caseSensitive));
    }

    /// <summary>
    /// Whether the pattern occurs in a text.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>True on a match.</returns>
    public bool Matches(string text) => Regex.IsMatch(text);
}
