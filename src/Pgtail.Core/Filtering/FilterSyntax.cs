namespace Pgtail.Filtering;

/// <summary>
/// Reads the <c>/pattern/</c> syntax of filter and highlight arguments.
/// </summary>
public static class FilterSyntax
{
    /// <summary>
    /// Parses <c>/pattern/</c> (ignoring case) or <c>/pattern/c</c> (matching case).
    /// </summary>
    /// <param name="argument">The argument.</param>
    /// <returns>The pattern and whether it matches case.</returns>
    /// <exception cref="FormatException">The argument is not in either form, or the pattern is empty.</exception>
    public static (string Pattern, bool CaseSensitive) Parse(string argument)
    {
        ArgumentNullException.ThrowIfNull(argument);
        if (!argument.StartsWith('/'))
        {
            throw new FormatException($"Filter pattern must start with /: {argument}");
        }

        string inner;
        bool caseSensitive;
        if (argument.EndsWith("/c", StringComparison.Ordinal))
        {
            inner = argument.Length >= 3 ? argument[1..^2] : "";
            caseSensitive = true;
        }
        else if (argument.EndsWith('/'))
        {
            inner = argument.Length >= 2 ? argument[1..^1] : "";
            caseSensitive = false;
        }
        else
        {
            throw new FormatException($"Filter pattern must end with / or /c: {argument}");
        }

        if (inner.Length == 0)
        {
            throw new FormatException("Empty pattern not allowed");
        }

        return (inner, caseSensitive);
    }
}
