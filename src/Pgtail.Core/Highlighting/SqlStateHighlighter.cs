using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles SQLSTATE codes by their class: success, warning, internal error, or error.
/// </summary>
public sealed class SqlStateHighlighter() : RegexHighlighter("sqlstate", 200, "SQLSTATE error codes with class-based coloring",
    HighlightPatterns.SqlState(), "hl_sqlstate_error")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in Regex.Matches(text))
        {
            var code = match.Groups[1];
            var style = code.Value[..2] switch
            {
                "00" => "hl_sqlstate_success",
                "01" or "02" => "hl_sqlstate_warning",
                "XX" or "YY" or "ZZ" or "P0" or "F0" => "hl_sqlstate_internal",
                _ => "hl_sqlstate_error",
            };

            yield return new HighlightMatch(code.Index, code.Index + code.Length, style);
        }
    }
}
