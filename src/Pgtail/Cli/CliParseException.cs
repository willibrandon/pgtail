namespace Pgtail.Cli;

/// <summary>
/// A command line that could not be parsed.
/// </summary>
/// <param name="message">What was wrong, as in <c>No such option: --x</c>.</param>
/// <param name="command">The command it applies to, or null for the main command.</param>
internal sealed class CliParseException(string message, string? command) : Exception(message)
{
    /// <summary>
    /// The command it applies to, or null for the main command.
    /// </summary>
    public string? Command { get; } = command;
}
