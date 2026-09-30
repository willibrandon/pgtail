namespace Pgtail.Commands;

/// <summary>
/// A command as typed, with where it runs.
/// </summary>
/// <param name="Command">The command.</param>
/// <param name="Name">The name as typed, which may be an alias.</param>
/// <param name="Line">The whole line.</param>
/// <param name="Tokens">The words after the name.</param>
/// <param name="Host">Where it runs.</param>
internal sealed record CommandInvocation(
    CommandInfo Command,
    string Name,
    string Line,
    IReadOnlyList<CommandToken> Tokens,
    ICommandHost Host)
{
    /// <summary>
    /// The words after the name.
    /// </summary>
    public IReadOnlyList<string> Args { get; } = [.. Tokens.Select(token => token.Text)];

    /// <summary>
    /// Where the output goes.
    /// </summary>
    public CommandOutput Output => Host.Output;

    /// <summary>
    /// The session.
    /// </summary>
    public Sessions.PgtailSession Session => Host.Session;

    /// <summary>
    /// The rest of the line as typed, from one of the words on, with its quotes.
    /// </summary>
    /// <param name="index">The index of the first word.</param>
    /// <returns>The raw text.</returns>
    public string RawFrom(int index) => index < Tokens.Count ? Line[Tokens[index].Start..].TrimEnd() : "";
}
