namespace Pgtail.Commands;

/// <summary>
/// A subcommand, such as <c>highlight enable</c>.
/// </summary>
/// <param name="Name">The subcommand name.</param>
/// <param name="Description">What it does.</param>
/// <param name="Arguments">What follows it.</param>
internal sealed record SubcommandSpec(string Name, string Description, ArgumentSpec Arguments);
