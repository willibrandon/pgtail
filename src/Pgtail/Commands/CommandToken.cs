namespace Pgtail.Commands;

/// <summary>
/// One word of a command line, with where it came from.
/// </summary>
/// <param name="Text">The word after quotes are removed.</param>
/// <param name="Start">The offset of its first character in the line.</param>
/// <param name="End">The offset just past its last character in the line.</param>
internal readonly record struct CommandToken(string Text, int Start, int End);
