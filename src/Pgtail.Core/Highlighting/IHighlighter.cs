namespace Pgtail.Highlighting;

/// <summary>
/// Finds the parts of a log message that deserve a style.
/// </summary>
public interface IHighlighter
{
    /// <summary>
    /// The unique name, lower case with underscores.
    /// </summary>
    string Name { get; }

    /// <summary>
    /// The processing order: lower runs first and wins overlaps.
    /// </summary>
    int Priority { get; }

    /// <summary>
    /// A short description for the highlighter list.
    /// </summary>
    string Description { get; }

    /// <summary>
    /// Finds every match in a text; matches may overlap.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The matches.</returns>
    IEnumerable<HighlightMatch> FindMatches(string text);
}
