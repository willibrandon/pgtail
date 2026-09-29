namespace Pgtail.Commands;

/// <summary>
/// A file to open in the built-in editor.
/// </summary>
/// <param name="Path">The file; it is created on save when missing.</param>
/// <param name="Title">The title shown above the editor.</param>
/// <param name="InitialText">The text to start with when the file does not exist.</param>
/// <param name="Validate">Checks text before it is saved, returning the problems found.</param>
internal sealed record EditRequest(string Path, string Title, string InitialText, Func<string, IReadOnlyList<string>> Validate);
