namespace Pgtail.Cli;

/// <summary>
/// The help pgtail prints for itself and its commands.
/// </summary>
internal static class CliHelp
{
    /// <summary>
    /// The help for the main command or one of its commands.
    /// </summary>
    /// <param name="command">The command, or null for the main help.</param>
    /// <returns>The help text.</returns>
    public static string For(string? command) => command switch
    {
        "list-instances" => """
            Usage: pgtail list-instances [OPTIONS]

              List detected PostgreSQL instances.

            Options:
              -v, --verbose  Show detailed instance information.
              -h, --help     Show this message and exit.
            """,
        "tail" => """
            Usage: pgtail tail [OPTIONS] [INSTANCE_ID]

              Tail logs for a PostgreSQL instance or arbitrary log file(s).

              Enters the interactive tail mode with vim-style navigation and filtering.
              Press 'q' to quit, '?' for help.

              Examples:
                pgtail tail 0                              Tail by instance ID
                pgtail tail --file ./tmp_check/log/postmaster.log
                pgtail tail --file "*.log"                 Glob pattern (multiple files)
                pgtail tail --file a.log --file b.log      Multiple explicit files
                cat log.gz | gunzip | pgtail tail --stdin  Read from a pipe
                pgtail tail --file ./test.log --since 5m   Start with a time filter

            Arguments:
              [INSTANCE_ID]  Instance ID to tail (optional if --file or --stdin is used).

            Options:
              -f, --file TEXT   Path or glob pattern to tail. Can specify multiple times.
                  --stdin       Read log data from stdin pipe (e.g., cat log.gz | gunzip | pgtail tail --stdin).
              -s, --since TEXT  Show entries from time (e.g., 5m, 1h, 14:30).
                  --stream      Print entries to standard output instead of the full screen view.
              -h, --help        Show this message and exit.
            """,
        "config" => """
            Usage: pgtail config [OPTIONS]

              Show or manage configuration.

            Options:
              -p, --path  Show config file path.
              -e, --edit  Open config in the built-in editor.
                  --reset Reset to defaults (creates backup).
              -h, --help  Show this message and exit.
            """,
        "enable-logging" => """
            Usage: pgtail enable-logging [OPTIONS] INSTANCE

              Enable logging_collector for an instance.

              Edits postgresql.conf (keeping a backup) to turn on the logging collector.
              PostgreSQL must be restarted afterward.

            Arguments:
              INSTANCE  Instance ID or data directory.

            Options:
              -h, --help  Show this message and exit.
            """,
        _ => """
            Usage: pgtail [OPTIONS] COMMAND [ARGS]...

              Interactive PostgreSQL log tailer with auto-detection and color output.

              When called without a command, starts the interactive REPL mode.
              Use --help with any command to see detailed usage.

            Options:
              -V, --version                   Show version and exit.
                  --check-update              Check for updates and exit.
                  --install-completion [SHELL]
                                              Install completion for the current shell (bash, zsh, fish, pwsh).
                  --show-completion [SHELL]   Show completion for the current shell, to copy it or customize the installation.
              -h, --help                      Show this message and exit.

            Commands:
              list-instances  List detected PostgreSQL instances.
              tail            Tail logs for a PostgreSQL instance or arbitrary log file(s).
              config          Show or manage configuration.
              enable-logging  Enable logging_collector for an instance.
            """,
    };

    /// <summary>
    /// The usage error block printed for a bad command line.
    /// </summary>
    /// <param name="error">The parse error.</param>
    /// <returns>The text.</returns>
    public static string Error(CliParseException error)
    {
        ArgumentNullException.ThrowIfNull(error);
        string usage = error.Command is { } command
            ? For(command).Split('\n')[0]
            : "Usage: pgtail [OPTIONS] COMMAND [ARGS]...";
        string help = error.Command is { } name ? $"pgtail {name} --help" : "pgtail --help";
        return $"{usage}\nTry '{help}' for help.\n\nError: {error.Message}";
    }
}
