namespace Pgtail.Commands;

/// <summary>
/// The shape of a command's arguments, used to complete them.
/// </summary>
/// <remarks>
/// A spec offers static values, values computed when completing, subcommands, options, and positional arguments.
/// The same spec drives the REPL's completion menu and tail mode's inline suggestions.
/// </remarks>
internal sealed class ArgumentSpec
{
    /// <summary>
    /// A spec for a command that takes nothing.
    /// </summary>
    public static ArgumentSpec None { get; } = new() { NoArguments = true };

    /// <summary>
    /// A spec for free-form text that offers no completions.
    /// </summary>
    public static ArgumentSpec FreeForm { get; } = new();

    /// <summary>
    /// Fixed values, in the order they are offered.
    /// </summary>
    public IReadOnlyList<CompletionItem> Values { get; init; } = [];

    /// <summary>
    /// Values computed when completing, offered after <see cref="Values"/>.
    /// </summary>
    public Func<CompletionContext, IEnumerable<CompletionItem>>? Source { get; init; }

    /// <summary>
    /// Subcommands offered in the first position.
    /// </summary>
    public IReadOnlyList<SubcommandSpec> Subcommands { get; init; } = [];

    /// <summary>
    /// The options.
    /// </summary>
    public IReadOnlyList<FlagSpec> Flags { get; init; } = [];

    /// <summary>
    /// What each positional argument completes to; a null slot is free-form.
    /// </summary>
    public IReadOnlyList<ArgumentSpec?> Positionals { get; init; } = [];

    /// <summary>
    /// What positional arguments past <see cref="Positionals"/> complete to, or null when there are no more.
    /// </summary>
    public ArgumentSpec? Rest { get; init; }

    /// <summary>
    /// Whether the command takes no arguments at all.
    /// </summary>
    public bool NoArguments { get; init; }

    /// <summary>
    /// A spec that offers fixed values.
    /// </summary>
    /// <param name="values">The values and their descriptions.</param>
    /// <returns>The spec.</returns>
    public static ArgumentSpec Of(params (string Value, string Description)[] values) =>
        new() { Values = [.. values.Select(value => new CompletionItem(value.Value, value.Description))] };

    /// <summary>
    /// A spec that offers computed values.
    /// </summary>
    /// <param name="source">Computes the values.</param>
    /// <returns>The spec.</returns>
    public static ArgumentSpec From(Func<CompletionContext, IEnumerable<CompletionItem>> source) => new() { Source = source };

    /// <summary>
    /// A spec whose only positional argument completes as given.
    /// </summary>
    /// <param name="argument">The argument.</param>
    /// <returns>The spec.</returns>
    public static ArgumentSpec Positional(ArgumentSpec? argument) => new() { Positionals = [argument] };
}
