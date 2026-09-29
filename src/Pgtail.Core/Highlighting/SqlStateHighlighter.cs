using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles SQLSTATE codes by their class: success, warning, internal error, or error.
/// </summary>
public sealed class SqlStateHighlighter() : RegexHighlighter("sqlstate", 200, "SQLSTATE error codes with class-based coloring",
    HighlightPatterns.SqlState, "hl_sqlstate_error")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        foreach (var groups in LogPattern.Captures(Regex, text))
        {
            if (groups[1] is not { } code)
            {
                continue;
            }

            var style = text.Text.Substring(code.Start, 2) switch
            {
                "00" => "hl_sqlstate_success",
                "01" or "02" => "hl_sqlstate_warning",
                "XX" or "YY" or "ZZ" or "P0" or "F0" => "hl_sqlstate_internal",
                _ => "hl_sqlstate_error",
            };

            yield return new HighlightMatch(code.Start, code.End, style);
        }
    }
}
