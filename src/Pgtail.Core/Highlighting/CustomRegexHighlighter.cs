using System.Text.RegularExpressions;
using Pgtail.Filtering;

namespace Pgtail.Highlighting;

/// <summary>
/// A highlighter built from a user's pattern.
/// </summary>
public sealed class CustomRegexHighlighter : RegexHighlighter
{
    private CustomRegexHighlighter(CustomHighlighterDefinition definition, Regex regex)
        : base(definition.Name, (int)Math.Clamp(definition.Priority, int.MinValue, int.MaxValue),
            $"Custom pattern: {definition.Pattern}", regex, definition.Style)
    {
    }

    /// <summary>
    /// Checks a pattern for use in a custom highlighter.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <returns>The problem, or null when the pattern is usable.</returns>
    public static string? Validate(string pattern)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        if (pattern.Length == 0)
        {
            return "Pattern cannot be empty";
        }

        if (!PatternSyntax.TryCompile(pattern, caseSensitive: true, out var regex, out var error))
        {
            return $"Invalid regex: {error}";
        }

        return regex.Match("") is { Success: true, Index: 0 } ? "Pattern matches zero-length strings" : null;
    }

    /// <summary>
    /// Builds the highlighter for a definition.
    /// </summary>
    /// <param name="definition">The definition.</param>
    /// <returns>The highlighter, or null when its pattern is not usable.</returns>
    public static CustomRegexHighlighter? Create(CustomHighlighterDefinition definition)
    {
        ArgumentNullException.ThrowIfNull(definition);
        return Validate(definition.Pattern) is null
            ? new CustomRegexHighlighter(definition, PatternSyntax.Compile(definition.Pattern, caseSensitive: true))
            : null;
    }
}
