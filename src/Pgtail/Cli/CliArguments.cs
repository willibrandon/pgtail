namespace Pgtail.Cli;

/// <summary>
/// The parsed command line.
/// </summary>
internal sealed record CliArguments
{
    /// <summary>
    /// What to do.
    /// </summary>
    public CliCommand Command { get; init; } = CliCommand.Repl;

    /// <summary>
    /// The command whose help to print, or null for the main help.
    /// </summary>
    public string? HelpFor { get; init; }

    /// <summary>
    /// <c>list-instances --verbose</c>.
    /// </summary>
    public bool Verbose { get; init; }

    /// <summary>
    /// The instance ID or data directory for <c>tail</c> and <c>enable-logging</c>.
    /// </summary>
    public string? Instance { get; init; }

    /// <summary>
    /// The files and patterns given with <c>--file</c>.
    /// </summary>
    public IReadOnlyList<string> Files { get; init; } = [];

    /// <summary>
    /// <c>tail --stdin</c>.
    /// </summary>
    public bool Stdin { get; init; }

    /// <summary>
    /// The <c>tail --since</c> time.
    /// </summary>
    public string? Since { get; init; }

    /// <summary>
    /// <c>tail --stream</c>.
    /// </summary>
    public bool Stream { get; init; }

    /// <summary>
    /// <c>config --path</c>.
    /// </summary>
    public bool ConfigPath { get; init; }

    /// <summary>
    /// <c>config --edit</c>.
    /// </summary>
    public bool ConfigEdit { get; init; }

    /// <summary>
    /// <c>config --reset</c>.
    /// </summary>
    public bool ConfigReset { get; init; }

    /// <summary>
    /// The shell named for completion, or null to detect it.
    /// </summary>
    public string? Shell { get; init; }

    /// <summary>
    /// The words being completed, for <see cref="CliCommand.Complete"/>.
    /// </summary>
    public IReadOnlyList<string> Words { get; init; } = [];
}
