namespace Pgtail.Commands;

/// <summary>
/// One completion candidate.
/// </summary>
/// <param name="Text">The text that replaces the word being typed.</param>
/// <param name="Description">A short description shown beside it.</param>
/// <param name="Continues">True when accepting it should not add a space, as for <c>--db=</c> or a directory.</param>
internal sealed record CompletionItem(string Text, string Description, bool Continues = false)
{
    /// <summary>
    /// The text shown in the completion menu, when different from <see cref="Text"/>.
    /// </summary>
    public string? Display { get; init; }

    /// <summary>
    /// The menu label.
    /// </summary>
    public string Label => Display ?? Text;
}
