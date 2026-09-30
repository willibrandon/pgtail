namespace Pgtail.Commands;

/// <summary>
/// An option a command accepts.
/// </summary>
/// <param name="Name">The option, such as <c>--since</c>, <c>-f</c>, or <c>--db=</c> for one written with its value.</param>
/// <param name="Description">What it does.</param>
/// <param name="Value">What its value completes to, or null for a switch that takes no value.</param>
internal sealed record FlagSpec(string Name, string Description, ArgumentSpec? Value = null)
{
    /// <summary>
    /// Other options that cannot be combined with this one; once any is used, this one is not offered.
    /// </summary>
    public IReadOnlyList<string> Excludes { get; init; } = [];

    /// <summary>
    /// Whether the option may be given more than once.
    /// </summary>
    public bool Repeatable { get; init; }

    /// <summary>
    /// Whether the value is attached with <c>=</c>, as in <c>--db=mydb</c>.
    /// </summary>
    public bool Attached => Name.EndsWith('=');

    /// <summary>
    /// The option name without a trailing <c>=</c>.
    /// </summary>
    public string Key => Attached ? Name[..^1] : Name;
}
