namespace Pgtail.Cli;

/// <summary>
/// What the command line asks pgtail to do.
/// </summary>
internal enum CliCommand
{
    /// <summary>
    /// Start the interactive REPL.
    /// </summary>
    Repl,

    /// <summary>
    /// Print the version.
    /// </summary>
    Version,

    /// <summary>
    /// Check GitHub for a newer release.
    /// </summary>
    CheckUpdate,

    /// <summary>
    /// Print help.
    /// </summary>
    Help,

    /// <summary>
    /// List detected instances.
    /// </summary>
    ListInstances,

    /// <summary>
    /// Tail an instance, files, or standard input.
    /// </summary>
    Tail,

    /// <summary>
    /// Show or manage the configuration.
    /// </summary>
    Config,

    /// <summary>
    /// Enable the logging collector for an instance.
    /// </summary>
    EnableLogging,

    /// <summary>
    /// Print a shell completion script.
    /// </summary>
    ShowCompletion,

    /// <summary>
    /// Install a shell completion script.
    /// </summary>
    InstallCompletion,

    /// <summary>
    /// Answer a completion request from a shell completion script.
    /// </summary>
    Complete,
}
