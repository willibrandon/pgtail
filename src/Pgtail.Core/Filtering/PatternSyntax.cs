using System.Text.RegularExpressions;

namespace Pgtail.Filtering;

/// <summary>
/// Compiles the regular expressions users type for filters, highlights, and notifications.
/// </summary>
public static class PatternSyntax
{
    /// <summary>
    /// Compiles a pattern.
    /// </summary>
    /// <param name="pattern">The pattern as typed.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <returns>The regular expression.</returns>
    /// <exception cref="ArgumentException">The pattern is not a valid regular expression.</exception>
    public static Regex Compile(string pattern, bool caseSensitive)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        var options = RegexOptions.CultureInvariant | (caseSensitive ? RegexOptions.None : RegexOptions.IgnoreCase);
        return new Regex(pattern, options);
    }

    /// <summary>
    /// Compiles a pattern, reporting a syntax error as a message instead of an exception.
    /// </summary>
    /// <param name="pattern">The pattern as typed.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <param name="regex">The regular expression, when the pattern is valid.</param>
    /// <param name="error">The reason the pattern is invalid.</param>
    /// <returns>True when the pattern is valid.</returns>
    public static bool TryCompile(string pattern, bool caseSensitive, out Regex regex, out string error)
    {
        try
        {
            regex = Compile(pattern, caseSensitive);
            error = "";
            return true;
        }
        catch (ArgumentException exception)
        {
            regex = null!;
            error = Describe(exception);
            return false;
        }
    }

    /// <summary>
    /// The readable part of a regular expression syntax error.
    /// </summary>
    /// <param name="exception">The error.</param>
    /// <returns>The message.</returns>
    public static string Describe(ArgumentException exception)
    {
        ArgumentNullException.ThrowIfNull(exception);
        return exception is RegexParseException parse ? $"{Reason(parse.Error)} at position {parse.Offset}" : exception.Message;
    }

    private static string Reason(RegexParseError error) => error switch
    {
        RegexParseError.InsufficientClosingParentheses => "missing ), unterminated subpattern",
        RegexParseError.InsufficientOpeningParentheses => "unbalanced parenthesis",
        RegexParseError.UnterminatedBracket => "unterminated character set",
        RegexParseError.QuantifierAfterNothing => "nothing to repeat",
        RegexParseError.NestedQuantifiersNotParenthesized => "multiple repeat",
        RegexParseError.UnescapedEndingBackslash => "bad escape (end of pattern)",
        RegexParseError.ReversedCharacterRange => "bad character range",
        RegexParseError.ReversedQuantifierRange => "min repeat greater than max repeat",
        RegexParseError.UndefinedNamedReference or RegexParseError.UndefinedNumberedReference => "unknown group name",
        RegexParseError.UnrecognizedEscape => "bad escape",
        _ => "invalid pattern",
    };
}
