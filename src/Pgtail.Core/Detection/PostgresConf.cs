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
        ArgumentNullException.ThrowIfNull(dataDirectory);
        Match match = DebianDataDirectory().Match(dataDirectory);
        return match.Success ? $"/etc/postgresql/{match.Groups[1].Value}/{match.Groups[2].Value}/postgresql.conf" : null;
    }

    /// <summary>
    /// The directory <c>pg_ctlcluster</c> writes Debian and Ubuntu cluster logs to.
    /// </summary>
    public const string DebianLogDirectory = "/var/log/postgresql";

    /// <summary>
    /// Reads a setting from <c>postgresql.conf</c> text: the first line setting the key, with quotes and comments removed.
    /// </summary>
    /// <param name="content">The file contents.</param>
    /// <param name="key">The setting name, matched ignoring case.</param>
    /// <returns>The value, or null when the key is not set.</returns>
    public static string? GetValue(string content, string key)
    {
        ArgumentNullException.ThrowIfNull(content);
        ArgumentNullException.ThrowIfNull(key);
        var pattern = new Regex($@"^\s*{Regex.Escape(key)}\s*=\s*['""]?([^'""#\n]+)['""]?",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);
        Match? match = content.Split('\n').Select(line => pattern.Match(line.TrimEnd('\r'))).FirstOrDefault(found => found.Success);
        return match?.Groups[1].Value.Trim();
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
    /// Reads the port from <c>postgresql.conf</c>, or from line 4 of <c>postmaster.pid</c> when it is not configured.
    /// </summary>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The port, or null.</returns>
    public static int? GetPort(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        if (FindConfFile(dataDirectory) is { } conf && ReadText(conf) is { } content && GetValue(content, "port") is { } configured
            && int.TryParse(configured, NumberStyles.Integer, CultureInfo.InvariantCulture, out int port))
        {
            return port;
        }

        string[]? lines = ReadText(Path.Join(dataDirectory, "postmaster.pid"))?.Split('\n');
        return lines is { Length: >= 4 }
            && int.TryParse(lines[3].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int running)
                ? running
                : null;
    }

    /// <summary>
    /// Finds where an instance logs.
    /// </summary>
    /// <remarks>
    /// Logging is on when <c>logging_collector</c> is on. The directory is <c>log_directory</c> (default <c>log</c>,
    /// relative to the data directory), or <c>pg_log</c> for older versions. The current file comes from
    /// <c>current_logfiles</c>, or else is the newest log file in the directory. With the collector off, a Debian or Ubuntu
    /// cluster still logs: <c>pg_ctlcluster</c> sends the server's output to one file, which is then the log and has no
    /// directory to follow, since the directory holds every cluster's log.
    /// </remarks>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The current log file, the log directory, and whether logging is on.</returns>
    public static (string? LogPath, string? LogDirectory, bool LoggingEnabled) GetLogInfo(string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(dataDirectory);
        if (FindConfFile(dataDirectory) is not { } conf || ReadText(conf) is not { } content)
        {
            return (null, null, false);
        }

        string? collector = GetValue(content, "logging_collector");
        if (collector is null || collector.ToLowerInvariant() is not ("on" or "true" or "yes" or "1"))
        {
            return DebianServerLog(dataDirectory) is { } serverLog ? (serverLog, null, true) : (null, null, false);
        }

        string configured = GetValue(content, "log_directory") ?? "log";
        string directory = configured.StartsWith('/') ? configured : Path.Join(dataDirectory, configured);
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
                string path = parts[1];
                bool absolute = path.StartsWith('/') || (path.Length >= 2 && path[1] == ':');
                return absolute ? path : Path.Join(dataDirectory, path);
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

    // pg_ctlcluster logs to the target of the log link in the cluster's configuration directory, which
    // pg_createcluster --logfile makes, or else to postgresql-<version>-<cluster>.log.
    private static string? DebianServerLog(string dataDirectory)
    {
        if (DebianDataDirectory().Match(dataDirectory) is not { Success: true } match)
        {
            return null;
        }

        (string? version, string? cluster) = (match.Groups[1].Value, match.Groups[2].Value);
        try
        {
            var link = new FileInfo($"/etc/postgresql/{version}/{cluster}/log");
            string log = (link.LinkTarget is null ? null : link.ResolveLinkTarget(returnFinalTarget: false)?.FullName)
                ?? $"{DebianLogDirectory}/postgresql-{version}-{cluster}.log";
            return File.Exists(log) ? log : null;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return null;
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
