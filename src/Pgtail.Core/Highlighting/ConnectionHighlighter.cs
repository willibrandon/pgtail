using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles connection settings such as <c>host=...</c> and <c>user=...</c>, each in the style of its setting.
/// </summary>
public sealed class ConnectionHighlighter() : RegexHighlighter("connection", 600, "Connection info (host, port, user, database)",
    HighlightPatterns.Connection(), "hl_connection")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in Regex.Matches(text))
        {
            var style = match.Groups[1].Value.ToLowerInvariant() switch
            {
                "host" => "hl_host",
                "port" => "hl_port",
                "user" => "hl_user",
                "database" or "application_name" => "hl_database",
                _ => Style,
            };

            yield return new HighlightMatch(match.Index, match.Index + match.Length, style);
        }
    }
}
