namespace Pgtail.Detection;

/// <summary>
/// A Debian or Ubuntu cluster, which <c>pg_ctlcluster</c> starts.
/// </summary>
/// <remarks>
/// The data directory is <c>/var/lib/postgresql/&lt;version&gt;/&lt;cluster&gt;</c>. <c>pg_ctlcluster</c> sends the
/// server's output to the target of the <c>log</c> link in <c>/etc/postgresql/&lt;version&gt;/&lt;cluster&gt;</c>, which
/// <c>pg_createcluster --logfile</c> makes, or else to
/// <c>/var/log/postgresql/postgresql-&lt;version&gt;-&lt;cluster&gt;.log</c>.
/// </remarks>
/// <param name="Version">The major version, such as <c>16</c>.</param>
/// <param name="Cluster">The cluster's name, such as <c>main</c>.</param>
/// <param name="LogFile">The file the server writes.</param>
public sealed record DebianLauncher(string Version, string Cluster, string LogFile) : ServerLauncher
{
    /// <inheritdoc/>
    public override string? OutputFile => LogFile;

    /// <inheritdoc/>
    public override string Name => "pg_ctlcluster";

    /// <summary>
    /// Finds the Debian or Ubuntu cluster in a data directory.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The launcher, or null when the directory is not a Debian cluster's.</returns>
    public static DebianLauncher? Find(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        if (PostgresConf.DebianCluster(dataDirectory) is not (string version, string cluster))
        {
            return null;
        }

        string log = $"{PostgresConf.DebianLogDirectory}/postgresql-{version}-{cluster}.log";
        try
        {
            var link = new FileInfo($"/etc/postgresql/{version}/{cluster}/log");
            if (link.LinkTarget is not null && link.ResolveLinkTarget(returnFinalTarget: false) is { } target)
            {
                log = target.FullName;
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            // The link cannot be read, so the default file is the one to try.
        }

        return new DebianLauncher(version, cluster, log);
    }

    /// <inheritdoc/>
    public override IReadOnlyList<string> RestartCommands(bool running) =>
        [$"sudo pg_ctlcluster {Version} {Cluster} {(running ? "restart" : "start")}"];
}
