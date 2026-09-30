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
}
