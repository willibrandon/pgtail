namespace Pgtail.Tests;

/// <summary>
/// Creates PostgreSQL data directories on disk for detection to find.
/// </summary>
internal static class DataDirectories
{
    /// <summary>
    /// Creates a data directory with the logging collector on and an empty log file for today.
    /// </summary>
    /// <param name="root">The directory to create it under.</param>
    /// <param name="version">The major version written to <c>PG_VERSION</c>.</param>
    /// <param name="port">The port written to <c>postgresql.conf</c>.</param>
    /// <returns>The data directory and its log file.</returns>
    public static (string DataDirectory, string LogFile) Create(string root, string version, int port) =>
        CreateAt(Path.Join(root, "pgdata"), version, port);

    /// <summary>
    /// Creates a data directory at a given place, such as where a platform's installer puts one.
    /// </summary>
    /// <param name="data">The data directory.</param>
    /// <param name="version">The major version written to <c>PG_VERSION</c>.</param>
    /// <param name="port">The port written to <c>postgresql.conf</c>.</param>
    /// <returns>The data directory and its log file.</returns>
    public static (string DataDirectory, string LogFile) CreateAt(string data, string version, int port)
    {
        string logs = Path.Join(data, "log");
        Directory.CreateDirectory(logs);
        File.WriteAllText(Path.Join(data, "PG_VERSION"), version + "\n");
        File.WriteAllText(Path.Join(data, "postgresql.conf"), $"""
            port = {port}
            logging_collector = on
            log_directory = 'log'
            log_filename = 'postgresql.log'

            """);
        string log = Path.Join(logs, "postgresql.log");
        File.WriteAllText(log, "");
        return (data, log);
    }

    /// <summary>
    /// Creates a cluster as <c>ankus start</c> makes it, stopped and with no log yet.
    /// </summary>
    /// <remarks>
    /// The data directory holds the label marker, and its postgresql.conf includes ankus.conf, which turns the logging
    /// collector off after postgresql.conf turns it on.
    /// </remarks>
    /// <param name="home">The ankus home, which holds the <c>clusters</c> directory.</param>
    /// <param name="label">The cluster's label, such as <c>pg18</c>.</param>
    /// <returns>The data directory.</returns>
    public static string CreateAnkusCluster(string home, string label)
    {
        string data = Path.Join(home, "clusters", label);
        Directory.CreateDirectory(data);
        File.WriteAllText(Path.Join(data, "PG_VERSION"), label[2..] + "\n");
        File.WriteAllText(Path.Join(data, ".ankus-cluster"), label);
        File.WriteAllText(Path.Join(data, "postgresql.conf"),
            "logging_collector = on\n\n# Settings supplied by ankus start.\ninclude = 'ankus.conf'\n");
        File.WriteAllText(Path.Join(data, "ankus.conf"),
            "port = 28818\nlisten_addresses = '127.0.0.1'\nunix_socket_directories = ''\n"
            + "log_destination = 'stderr'\nlogging_collector = off\n");
        return data;
    }

    /// <summary>
    /// Creates a cluster as <c>cargo pgrx init</c> makes it: <c>data-&lt;major&gt;</c> beside <c>config.toml</c>.
    /// </summary>
    /// <param name="home">The pgrx home.</param>
    /// <param name="major">The major version, such as <c>16</c>.</param>
    /// <returns>The data directory.</returns>
    public static string CreatePgrxCluster(string home, string major)
    {
        string data = Path.Join(home, $"data-{major}");
        Directory.CreateDirectory(data);
        File.WriteAllText(Path.Join(home, "config.toml"), $"[configs]\npg{major} = \"/usr/bin/pg_config\"\n");
        File.WriteAllText(Path.Join(data, "PG_VERSION"), major + "\n");
        File.WriteAllText(Path.Join(data, "postgresql.conf"), "port = 28816\n");
        return data;
    }
}
