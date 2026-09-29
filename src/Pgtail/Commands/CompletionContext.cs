using Pgtail.Sessions;

namespace Pgtail.Commands;

/// <summary>
/// What a completion source needs to know about the line being completed.
/// </summary>
/// <param name="Session">The session, for instances, themes, and settings.</param>
/// <param name="Arguments">The finished words after the command (and subcommand) name.</param>
/// <param name="Partial">The word being typed, possibly empty.</param>
/// <param name="CurrentDirectory">The directory relative paths start from.</param>
internal sealed record CompletionContext(
    PgtailSession Session,
    IReadOnlyList<string> Arguments,
    string Partial,
    string CurrentDirectory);
