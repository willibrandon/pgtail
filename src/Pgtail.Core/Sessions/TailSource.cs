using System.Globalization;
using Pgtail.Detection;

namespace Pgtail.Sessions;

/// <summary>
/// What a tail reads: a detected instance, files, or standard input.
/// </summary>
/// <param name="Instance">The instance, when tailing one.</param>
/// <param name="Files">The files, when tailing files.</param>
/// <param name="GlobPattern">The glob the files came from, watched for new matches, or null.</param>
/// <param name="Stdin">True when reading standard input.</param>
public sealed record TailSource(
    PostgresInstance? Instance = null,
    IReadOnlyList<string>? Files = null,
    string? GlobPattern = null,
    bool Stdin = false)
{
    /// <summary>
    /// A short name for the status bar and messages: the instance ID, a file name, a file count, or <c>stdin</c>.
    /// </summary>
    public string DisplayName => this switch
    {
        { Stdin: true } => "stdin",
        { Instance: { } instance } => instance.Id.ToString(CultureInfo.InvariantCulture),
        { Files: [var only] } => Path.GetFileName(only),
        { Files: { Count: > 1 } files } => $"{files.Count} files",
        _ => "",
    };
}
