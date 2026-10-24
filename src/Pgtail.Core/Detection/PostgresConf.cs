using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Detection;

/// <summary>
/// Reads what pgtail needs from a data directory: the configuration file, version, port, and log location.
/// </summary>
public static partial class PostgresConf
{
    /// <summary>
    /// Finds <c>postgresql.conf</c> for a data directory.
    /// </summary>
    /// <remarks>
    /// The standard location is the data directory itself. A Debian or Ubuntu cluster in
    /// <c>/var/lib/postgresql/&lt;version&gt;/&lt;cluster&gt;</c> keeps it in <c>/etc/postgresql/&lt;version&gt;/&lt;cluster&gt;</c>.
    /// </remarks>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The file, or null when neither location has one.</returns>
    public static string? FindConfFile(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        string standard = Path.Join(dataDirectory, "postgresql.conf");
        if (File.Exists(standard))
        {
            return standard;
        }

        return DebianConfFile(dataDirectory) is { } debian && File.Exists(debian) ? debian : null;
    }

    /// <summary>
    /// The Debian or Ubuntu location of <c>postgresql.conf</c> for a data directory.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The path, or null when the data directory is not a Debian cluster directory.</returns>
    public static string? DebianConfFile(string dataDirectory)
    {
        return DebianCluster(dataDirectory) is (string version, string cluster)
            ? $"/etc/postgresql/{version}/{cluster}/postgresql.conf"
            : null;
    }

    /// <summary>
    /// The directory <c>pg_ctlcluster</c> writes Debian and Ubuntu cluster logs to.
    /// </summary>
    public const string DebianLogDirectory = "/var/log/postgresql";

    /// <summary>
    /// The version and the name of the Debian or Ubuntu cluster that a data directory belongs to.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The version and the cluster, or null when the data directory is not a Debian cluster directory.</returns>
    public static (string Version, string Cluster)? DebianCluster(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        Match match = DebianDataDirectory().Match(dataDirectory);
        return match.Success ? (match.Groups[1].Value, match.Groups[2].Value) : null;
    }

    /// <summary>
    /// Reads the version from <c>PG_VERSION</c>, or from a Debian cluster path when the file cannot be read.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The version, or <c>unknown</c>.</returns>
    public static string GetVersion(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        try
        {
            return File.ReadAllText(Path.Join(dataDirectory, "PG_VERSION")).Trim();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            Match match = DebianVersion().Match(dataDirectory);
            return match.Success ? match.Groups[1].Value : "unknown";
        }
    }

    /// <summary>
    /// Finds the port: the <c>port</c> setting, or line 4 of <c>postmaster.pid</c> when nothing sets it.
    /// </summary>
    /// <param name="settings">The server's settings.</param>
    /// <returns>The port, or null.</returns>
    public static int? GetPort(ServerSettings settings)
    {
        ArgumentNullException.ThrowIfNull(settings);
        if (settings["port"] is { } configured
            && int.TryParse(configured.Value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int port))
        {
            return port;
        }

        string[]? lines = ReadText(Path.Join(settings.DataDirectory, "postmaster.pid"))?.Split('\n');
        return lines is { Length: >= 4 }
            && int.TryParse(lines[3].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int running)
                ? running
                : null;
    }

    /// <summary>
    /// Finds where an instance logs.
    /// </summary>
    /// <remarks>
    /// <para>
    /// With <c>logging_collector</c> on, the directory is <c>log_directory</c> (default <c>log</c>, from the data
    /// directory), or <c>pg_log</c> for older versions. The current file comes from <c>current_logfiles</c>, or else is
    /// the newest log file in the directory.
    /// </para>
    /// <para>
    /// With the collector off, the log is the server's output, so it is wherever the program that started the server
    /// sends it. On Linux, the output of a running server shows in <c>/proc</c>; if it goes to the console, a pipe, or
    /// nowhere, the server logs to no file. Otherwise the launcher tells: ankus, cargo pgrx, and <c>pg_ctlcluster</c>
    /// each send it to a file of their own. That file is then the log, with no directory to follow.
    /// </para>
    /// </remarks>
    /// <param name="settings">The server's settings.</param>
    /// <param name="launcher">What starts the server.</param>
    /// <returns>The current log file, the log directory, and whether logging is on.</returns>
    public static (string? LogPath, string? LogDirectory, bool LoggingEnabled) GetLogInfo(ServerSettings settings, ServerLauncher launcher)
    {
        ArgumentNullException.ThrowIfNull(settings);
        ArgumentNullException.ThrowIfNull(launcher);
        string dataDirectory = settings.DataDirectory;
        if (!settings.IsOn("logging_collector"))
        {
            (bool known, string? output) = RunningServerOutput(dataDirectory);
            if (known)
            {
                return output is null ? (null, null, false) : (output, null, true);
            }

            return launcher.OutputFile is { } file && File.Exists(file) ? (file, null, true) : (null, null, false);
        }

        string directory = PostgresPath.Resolve(settings["log_directory"]?.Value ?? "log", dataDirectory);
        bool accessible = false;
        try
        {
            if (Directory.Exists(directory))
            {
                accessible = true;
            }
            else if (Directory.Exists(Path.Join(dataDirectory, "pg_log")))
            {
                directory = Path.Join(dataDirectory, "pg_log");
                accessible = true;
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            accessible = false;
        }

        // A listed file that cannot be checked because its directory is closed to us is still the one to tail.
        if (ReadCurrentLogfiles(dataDirectory) is { } current && (File.Exists(current) || !accessible))
        {
            return (current, directory, true);
        }

        return (accessible ? FindLatestLog(directory) : null, directory, true);
    }

    /// <summary>
    /// Reads the current log file from <c>current_logfiles</c>, which PostgreSQL 10 and later keep up to date.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The first stderr, csvlog, or jsonlog file listed, or null.</returns>
    public static string? ReadCurrentLogfiles(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        if (ReadText(Path.Join(dataDirectory, "current_logfiles")) is not { } content)
        {
            return null;
        }

        foreach (string line in content.Split('\n'))
        {
            string[] parts = line.Trim().Split((char[]?)null, 2, StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length == 2 && parts[0] is "stderr" or "csvlog" or "jsonlog")
            {
                return PostgresPath.Resolve(parts[1], dataDirectory);
            }
        }

        return null;
    }

    /// <summary>
    /// Finds the most recently modified log file in a directory.
    /// </summary>
    /// <remarks>
    /// Log files end in <c>.log</c> or start with <c>postgresql</c>, unless an extension is given.
    /// </remarks>
    /// <param name="directory">The directory.</param>
    /// <param name="extension">Only files with this extension, such as <c>.csv</c>, or null for any log file.</param>
    /// <returns>The file, or null when there is none.</returns>
    public static string? FindLatestLog(string directory, string? extension = null)
    {
        ArgumentNullException.ThrowIfNull(directory);
        try
        {
            return new DirectoryInfo(directory).EnumerateFileSystemInfos()
                .Where(file => extension is null
                    ? file.Extension == ".log" || file.Name.StartsWith("postgresql", StringComparison.Ordinal)
                    : file.Extension == extension)
                .OrderByDescending(ModifiedTime)
                .Select(file => file.FullName)
                .FirstOrDefault();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    // Where the output of the server running from a data directory goes, from its standard error in /proc on Linux. Known
    // is false when that cannot be seen: on another platform, with no server running, or with the process closed to us.
    // The file is null when the output goes to the console, a pipe, a device, or a file since deleted.
    private static (bool Known, string? File) RunningServerOutput(string dataDirectory)
    {
        if (!OperatingSystem.IsLinux() || ReadText(Path.Join(dataDirectory, "postmaster.pid")) is not { } pidFile
            || !int.TryParse(pidFile.Split('\n')[0].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int pid)
            || ProcessTable.NameOf(pid) is not { } name || !name.Contains("postgres", StringComparison.Ordinal))
        {
            return (false, null);
        }

        try
        {
            if (new FileInfo($"/proc/{pid}/fd/2").LinkTarget is not { } target)
            {
                return (false, null);
            }

            bool file = target.StartsWith('/') && !target.StartsWith("/dev/", StringComparison.Ordinal)
                && !target.EndsWith(" (deleted)", StringComparison.Ordinal) && File.Exists(target);
            return (true, file ? target : null);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return (false, null);
        }
    }

    private static DateTime ModifiedTime(FileSystemInfo file)
    {
        try
        {
            return file.LastWriteTimeUtc;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return DateTime.MinValue;
        }
    }

    private static string? ReadText(string path)
    {
        try
        {
            return File.ReadAllText(path);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
        }
    }

    [GeneratedRegex("^/var/lib/postgresql/([0-9]+)/([^/]+)/?$")]
    private static partial Regex DebianDataDirectory();

    [GeneratedRegex("/postgresql/([0-9]+)/[^/]+/?$")]
    private static partial Regex DebianVersion();
}
