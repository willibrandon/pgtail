namespace Pgtail.Detection;

/// <summary>
/// A development cluster that <c>ankus start</c> runs.
/// </summary>
/// <remarks>
/// The data directory is <c>~/.ankus/clusters/&lt;label&gt;</c>, or the same under another ankus home.
/// ankus writes its own settings to <c>ankus.conf</c> on each start, with <c>logging_collector = off</c>, and starts the
/// server with <c>pg_ctl start -l</c>. The data directory holds <c>.ankus-cluster</c>, the cluster's label, and, from
/// ankus 0.1.6, <c>.ankus-log</c>, the path of the file the server writes. A cluster that an older ankus started has no
/// <c>.ankus-log</c>; its server writes <c>&lt;label&gt;.log</c> beside the data directory, or
/// <c>&lt;label&gt;.log.stderr.log</c> on Windows, where <c>&lt;label&gt;.log</c> is a copy that ankus puts together.
/// </remarks>
/// <param name="Label">The cluster's label, such as <c>pg18</c>.</param>
/// <param name="Home">The ankus home, which holds the <c>clusters</c> directory.</param>
/// <param name="LogFile">The file the server writes.</param>
public sealed record AnkusLauncher(string Label, string Home, string LogFile) : ServerLauncher
{
    /// <summary>
    /// The file in the data directory that holds the cluster's label.
    /// </summary>
    public const string MarkerFileName = ".ankus-cluster";

    /// <summary>
    /// The file in the data directory that holds the path of the file the server writes.
    /// </summary>
    public const string LogPathFileName = ".ankus-log";

    /// <inheritdoc/>
    public override string? OutputFile => LogFile;

    /// <inheritdoc/>
    public override string Name => "ankus";

    /// <inheritdoc/>
    public override bool ManagesLogging => true;

    /// <summary>
    /// Finds the ankus cluster in a data directory.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The launcher, or null when ankus does not manage the directory.</returns>
    public static AnkusLauncher? Find(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        string data = Path.TrimEndingDirectorySeparator(Path.GetFullPath(dataDirectory));
        if (FirstLine(Path.Join(data, MarkerFileName)) is not { Length: > 0 } label)
        {
            return null;
        }

        string clusters = Path.GetDirectoryName(data) ?? data;
        string home = Path.GetDirectoryName(clusters) ?? clusters;
        string log = FirstLine(Path.Join(data, LogPathFileName)) is { Length: > 0 } recorded
            ? recorded
            : Path.Join(clusters, OperatingSystem.IsWindows() ? $"{label}.log.stderr.log" : $"{label}.log");
        return new AnkusLauncher(label, home, log);
    }

    /// <inheritdoc/>
    public override IReadOnlyList<string> RestartCommands(bool running)
    {
        string version = Label.StartsWith("pg", StringComparison.Ordinal) ? Label[2..] : Label;
        string standard = Path.Join(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".ankus");
        string options = $"--pg {version}" + (PathsEqual(Home, standard) ? "" : $" --home {Argument(Home)}");
        return running ? [$"ankus stop {options}", $"ankus start {options}"] : [$"ankus start {options}"];
    }

    private static bool PathsEqual(string first, string second) => string.Equals(
        Path.TrimEndingDirectorySeparator(first),
        Path.TrimEndingDirectorySeparator(second),
        OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal);

    private static string? FirstLine(string path)
    {
        try
        {
            return File.Exists(path) ? File.ReadAllText(path).Split('\n')[0].Trim() : null;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }
}
