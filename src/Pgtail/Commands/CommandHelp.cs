namespace Pgtail.Commands;

/// <summary>
/// The detailed help <c>help &lt;command&gt;</c> shows in tail mode.
/// </summary>
/// <param name="Usage">The syntax.</param>
/// <param name="Short">A one-line summary.</param>
/// <param name="Description">What the command does.</param>
/// <param name="Examples">Examples, each with its explanation.</param>
internal sealed record CommandHelp(string Usage, string Short, string Description, IReadOnlyList<string> Examples)
{
    /// <summary>
    /// Abbreviations the command accepts, or null.
    /// </summary>
    public string? Aliases { get; init; }

    /// <summary>
    /// Related commands and keys, or null.
    /// </summary>
    public string? SeeAlso { get; init; }
}
