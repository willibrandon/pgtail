using Pgtail.Sessions;

namespace Pgtail.Commands;

/// <summary>
/// Where a command runs: the REPL, tail mode, or the command line.
/// </summary>
internal interface ICommandHost
{
    /// <summary>
    /// The session.
    /// </summary>
    PgtailSession Session { get; }

    /// <summary>
    /// Where the command's output goes.
    /// </summary>
    CommandOutput Output { get; }

    /// <summary>
    /// The directory relative paths start from.
    /// </summary>
    string CurrentDirectory { get; }
}
