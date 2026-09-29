using Pgtail.Commands;
using Pgtail.Rendering;
using Pgtail.Sessions;

namespace Pgtail.Cli;

/// <summary>
/// Runs REPL command handlers from the command line, printing their output to standard output.
/// </summary>
/// <param name="session">The session.</param>
internal sealed class ConsoleCommandHost(PgtailSession session) : ICommandHost
{
    /// <inheritdoc/>
    public PgtailSession Session { get; } = session;

    /// <inheritdoc/>
    public CommandOutput Output { get; } = new();

    /// <inheritdoc/>
    public string CurrentDirectory { get; } = Environment.CurrentDirectory;

    /// <summary>
    /// Prints the waiting output, styled when standard output is a terminal.
    /// </summary>
    public void Flush()
    {
        foreach (var line in Output.Take())
        {
            Console.Out.WriteLine(AnsiText.Render(line, Session.ColorEnabled, styled: !Console.IsOutputRedirected));
        }
    }
}
