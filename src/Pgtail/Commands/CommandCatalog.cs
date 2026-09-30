namespace Pgtail.Commands;

/// <summary>
/// A set of commands: the single source for dispatch, completion, and help.
/// </summary>
/// <param name="commands">The commands, in the order they are offered.</param>
internal sealed class CommandCatalog(IReadOnlyList<CommandInfo> commands)
{
    /// <summary>
    /// The commands, in the order they are offered.
    /// </summary>
    public IReadOnlyList<CommandInfo> Commands { get; } = commands;

    /// <summary>
    /// Finds the command a name runs.
    /// </summary>
    /// <param name="name">The name as typed.</param>
    /// <returns>The command, or null.</returns>
    public CommandInfo? Find(string name) => Commands.FirstOrDefault(command => command.Matches(name));

    /// <summary>
    /// Every name and alias with its description, in catalog order.
    /// </summary>
    /// <returns>The names.</returns>
    public IEnumerable<CompletionItem> Names() => Commands.SelectMany(command =>
        new[] { command.Name }.Concat(command.Aliases).Select(name => new CompletionItem(name, command.Description)));

    /// <summary>
    /// The candidates for the word being typed at the end of a line.
    /// </summary>
    /// <param name="line">The text before the caret.</param>
    /// <param name="host">The host, for the session and current directory.</param>
    /// <param name="style">How options are offered.</param>
    /// <returns>Where the word being typed starts, and the candidates.</returns>
    public (int Start, List<CompletionItem> Items) Complete(string line, ICommandHost host, CompletionStyle style)
    {
        ArgumentNullException.ThrowIfNull(line);
        ArgumentNullException.ThrowIfNull(host);
        List<CommandToken> tokens = CommandLineSplitter.Split(line);
        bool endsInSpace = line.Length == 0 || char.IsWhiteSpace(line[^1]);
        CommandToken? partialToken = endsInSpace || tokens.Count == 0 ? null : tokens[^1];
        string partial = partialToken?.Text ?? "";
        int start = partialToken?.Start ?? line.Length;
        List<CommandToken> finished = partialToken is null ? tokens : [.. tokens.Take(tokens.Count - 1)];
        if (finished.Count == 0)
        {
            return (start, partial.Length == 0 && style == CompletionStyle.Inline ? [] : ArgumentCompleter.Filter(Names(), partial));
        }

        if (Find(finished[0].Text) is not { } command)
        {
            return (start, []);
        }

        var arguments = finished.Skip(1).Select(token => token.Text).ToList();
        var context = new CompletionContext(host.Session, arguments, partial, host.CurrentDirectory);
        return (start, ArgumentCompleter.Complete(command.Arguments, context, style));
    }
}
