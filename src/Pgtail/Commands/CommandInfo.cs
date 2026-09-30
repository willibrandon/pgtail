namespace Pgtail.Commands;

/// <summary>
/// One entry of a command catalog: its name, what it does, how its arguments complete, and how it runs.
/// </summary>
/// <param name="Name">The name.</param>
/// <param name="Description">A one-line description, shown beside completions.</param>
/// <param name="Arguments">How its arguments complete.</param>
/// <param name="Handler">Runs it.</param>
internal sealed record CommandInfo(string Name, string Description, ArgumentSpec Arguments, CommandHandler Handler)
{
    /// <summary>
    /// Other names that run the same command, each offered with the same description.
    /// </summary>
    public IReadOnlyList<string> Aliases { get; init; } = [];

    /// <summary>
    /// Detailed help, or null.
    /// </summary>
    public CommandHelp? Help { get; init; }

    /// <summary>
    /// Whether a name runs this command, ignoring case.
    /// </summary>
    /// <param name="name">The name as typed.</param>
    /// <returns>True for the name or an alias.</returns>
    public bool Matches(string name) => Name.Equals(name, StringComparison.OrdinalIgnoreCase)
        || Aliases.Any(alias => alias.Equals(name, StringComparison.OrdinalIgnoreCase));
}
