namespace Pgtail.Detection;

/// <summary>
/// What starts and stops a server, and where it sends the server's output when the logging collector is off.
/// </summary>
/// <remarks>
/// A tool that manages development clusters, such as ankus or cargo pgrx, starts the server with <c>pg_ctl -l</c> and
/// keeps the output in a file of its own. A Debian or Ubuntu cluster starts through <c>pg_ctlcluster</c>, which does the
/// same. Any other server is started with <c>pg_ctl</c>, which leaves the output on the console unless told otherwise.
/// </remarks>
public abstract record ServerLauncher
{
    /// <summary>
    /// The command that starts and stops the server, such as <c>ankus</c> or <c>pg_ctl</c>.
    /// </summary>
    public abstract string Name { get; }

    /// <summary>
    /// The file the server's output goes to, or null when the launcher leaves it on the console.
    /// </summary>
    public abstract string? OutputFile { get; }

    /// <summary>
    /// Whether the launcher decides where the server logs.
    /// </summary>
    /// <remarks>
    /// If the logging collector is turned on for such a server, the file that the launcher keeps stops getting the log.
    /// </remarks>
    public virtual bool ManagesLogging => false;

    /// <summary>
    /// Finds the launcher of a data directory: ankus, cargo pgrx, or pg_ctlcluster, or else pg_ctl.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The launcher.</returns>
    public static ServerLauncher For(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        return AnkusLauncher.Find(dataDirectory)
            ?? PgrxLauncher.Find(dataDirectory)
            ?? DebianLauncher.Find(dataDirectory)
            ?? (ServerLauncher)new PgCtlLauncher(dataDirectory);
    }

    /// <summary>
    /// The commands that restart the server, or that start it when it is stopped.
    /// </summary>
    /// <param name="running">Whether the server is running.</param>
    /// <returns>The commands, to run in order.</returns>
    public abstract IReadOnlyList<string> RestartCommands(bool running);

    /// <summary>
    /// A path as a command argument, in double quotes when it holds a space.
    /// </summary>
    /// <param name="path">The path.</param>
    /// <returns>The argument.</returns>
    protected static string Argument(string path) => path.Contains(' ', StringComparison.Ordinal) ? $"\"{path}\"" : path;
}
