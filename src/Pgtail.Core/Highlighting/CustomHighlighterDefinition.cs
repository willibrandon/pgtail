namespace Pgtail.Highlighting;

/// <summary>
/// A user-defined regex highlighter as it is saved in the configuration.
/// </summary>
/// <param name="Name">The unique name.</param>
/// <param name="Pattern">The regular expression, matching case.</param>
/// <param name="Style">The style of every match, such as <c>bold magenta</c> or a theme element name.</param>
/// <param name="Priority">The processing order; custom highlighters default to 1050, after the built-ins.</param>
/// <param name="Enabled">Whether the highlighter runs.</param>
public sealed record CustomHighlighterDefinition(
    string Name,
    string Pattern,
    string Style = "yellow",
    long Priority = 1050,
    bool Enabled = true);
