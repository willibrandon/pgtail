using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// Collects the lines a command prints, for its host to show.
/// </summary>
internal sealed class CommandOutput
{
    private readonly List<StyledText> _lines = [];

    /// <summary>
    /// Whether any lines are waiting to be shown.
    /// </summary>
    public bool HasLines => _lines.Count > 0;

    /// <summary>
    /// Adds a line of plain or uniformly styled text; embedded newlines start more lines.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="style">The style.</param>
    public void Line(string text = "", TextStyle style = default) => _lines.Add(new StyledText(text, style));

    /// <summary>
    /// Adds a styled line; embedded newlines start more lines.
    /// </summary>
    /// <param name="text">The text.</param>
    public void Line(StyledText text)
    {
        ArgumentNullException.ThrowIfNull(text);
        _lines.Add(text);
    }

    /// <summary>
    /// Adds a line written in markup, such as <c>[bold red]✗[/] Unknown theme</c>.
    /// </summary>
    /// <param name="markup">The markup.</param>
    public void Markup(string markup) => _lines.Add(Styling.Markup.Parse(markup));

    /// <summary>
    /// Adds several plain lines.
    /// </summary>
    /// <param name="lines">The lines.</param>
    public void Lines(IEnumerable<string> lines)
    {
        ArgumentNullException.ThrowIfNull(lines);
        foreach (var line in lines)
        {
            Line(line);
        }
    }

    /// <summary>
    /// Takes the waiting lines, split at newlines.
    /// </summary>
    /// <returns>The lines, which are then forgotten.</returns>
    public List<StyledText> Take()
    {
        var lines = _lines.SelectMany(line => line.SplitLines()).ToList();
        _lines.Clear();
        return lines;
    }
}
