using Pgtail.Matching;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles connection settings such as <c>host=...</c> and <c>user=...</c>, each in the style of its setting.
/// </summary>
public sealed class ConnectionHighlighter() : RegexHighlighter("connection", 600, "Connection info (host, port, user, database)",
    HighlightPatterns.Connection, "hl_connection")
{
    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(Utf8Text text)
    {
        foreach ((int Start, int End)?[] groups in LogPattern.Captures(Regex, text))
        {
            if (groups[0] is not { } whole || groups[1] is not { } setting)
            {
                continue;
            }

            string style = text.Text[setting.Start..setting.End].ToLowerInvariant() switch
            {
                "host" => "hl_host",
                "port" => "hl_port",
                "user" => "hl_user",
                "database" or "application_name" => "hl_database",
                _ => Style,
            };

            yield return new HighlightMatch(whole.Start, whole.End, style);
        }
    }
}
