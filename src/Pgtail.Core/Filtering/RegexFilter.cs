using Pgtail.Matching;

namespace Pgtail.Filtering;

/// <summary>
/// A compiled regex filter.
/// </summary>
/// <param name="pattern">The compiled pattern.</param>
/// <param name="type">How the filter combines with the others.</param>
public sealed class RegexFilter(LogPattern pattern, FilterType type)
{
    /// <summary>
    /// The pattern as typed.
    /// </summary>
    public string Pattern => Compiled.Pattern;

    /// <summary>
    /// How the filter combines with the others.
    /// </summary>
    public FilterType Type { get; } = type;

    /// <summary>
    /// Whether the pattern matches case.
    /// </summary>
    public bool CaseSensitive => Compiled.CaseSensitive;

    /// <summary>
    /// The compiled pattern.
    /// </summary>
    public LogPattern Compiled { get; } = pattern;

    /// <summary>
    /// Compiles a filter.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="type">How the filter combines.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The filter.</returns>
    /// <exception cref="FormatException">The pattern is not a valid regular expression.</exception>
    public static RegexFilter Create(string pattern, FilterType type, bool caseSensitive = false) =>
        new(LogPattern.Compile(pattern, caseSensitive), type);

    /// <summary>
    /// Whether the pattern occurs in a UTF-8 line.
    /// </summary>
    /// <param name="utf8">The line.</param>
    /// <returns>True on a match.</returns>
    public bool Matches(ReadOnlySpan<byte> utf8) => Compiled.IsMatch(utf8);
}
