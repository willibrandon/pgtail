namespace Pgtail.Detection;

/// <summary>
/// A development cluster that <c>cargo pgrx start</c> runs.
/// </summary>
/// <remarks>
/// The data directory is <c>data-&lt;major&gt;</c> in the pgrx home, <c>~/.pgrx</c> or <c>PGRX_HOME</c>, which holds
/// the <c>config.toml</c> that <c>cargo pgrx init</c> writes. pgrx starts the server with <c>pg_ctl start -l</c>, which
/// sends the output to <c>&lt;major&gt;.log</c> in the pgrx home.
/// </remarks>
/// <param name="Major">The major version, such as <c>16</c>.</param>
/// <param name="LogFile">The file the server writes.</param>
public sealed record PgrxLauncher(string Major, string LogFile) : ServerLauncher
{
    /// <inheritdoc/>
    public override string? OutputFile => LogFile;

    /// <inheritdoc/>
    public override string Name => "cargo pgrx";

    /// <inheritdoc/>
    public override bool ManagesLogging => true;

    /// <summary>
    /// Finds the pgrx cluster in a data directory.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The launcher, or null when pgrx does not manage the directory.</returns>
    public static PgrxLauncher? Find(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        string data = Path.TrimEndingDirectorySeparator(Path.GetFullPath(dataDirectory));
        string name = Path.GetFileName(data);
        if (!name.StartsWith("data-", StringComparison.Ordinal) || name.Length == 5 || !name[5..].All(char.IsAsciiDigit)
            || Path.GetDirectoryName(data) is not { } home || !File.Exists(Path.Join(home, "config.toml")))
        {
            return null;
        }

        return new PgrxLauncher(name[5..], Path.Join(home, $"{name[5..]}.log"));
    }

    /// <inheritdoc/>
    public override IReadOnlyList<string> RestartCommands(bool running) => running
        ? [$"cargo pgrx stop pg{Major}", $"cargo pgrx start pg{Major}"]
        : [$"cargo pgrx start pg{Major}"];
}
