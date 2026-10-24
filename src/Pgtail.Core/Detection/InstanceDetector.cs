using System.Globalization;
using Pgtail.Files;

namespace Pgtail.Detection;

/// <summary>
/// Finds PostgreSQL instances on this machine.
/// </summary>
/// <param name="environment">Reads an environment variable, such as <c>PGDATA</c>.</param>
/// <param name="home">The user's home directory.</param>
/// <param name="processes">Lists running processes.</param>
public sealed class InstanceDetector(Func<string, string?> environment, string home, Func<IReadOnlyList<ProcessEntry>> processes)
{
    /// <summary>
    /// A detector for the current user and machine.
    /// </summary>
    /// <returns>The detector.</returns>
    public static InstanceDetector ForCurrentUser() => new(
        Environment.GetEnvironmentVariable,
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
        ProcessTable.List);

    /// <summary>
    /// Detects every instance, most reliable sources first.
    /// </summary>
    /// <remarks>
    /// Running processes come first, then pgrx data directories, then ankus clusters, then <c>PGDATA</c>, then platform
    /// default locations. A data directory found more than once is listed once, under its first source.
    /// </remarks>
    /// <returns>The instances, numbered from 0.</returns>
    public IReadOnlyList<PostgresInstance> DetectAll()
    {
        var instances = new List<PostgresInstance>();
        var seen = new HashSet<string>(PathComparer);
        Dictionary<string, int> running = Running();
        void Add(string directory, DetectionSource source)
        {
            string resolved = PathResolver.Resolve(directory, home);
            if (seen.Add(resolved))
            {
                instances.Add(Describe(instances.Count, directory, source, running));
            }
        }

        foreach (string directory in running.Keys)
        {
            Add(directory, DetectionSource.Process);
        }

        foreach (string directory in FromPgrx())
        {
            Add(directory, DetectionSource.Pgrx);
        }

        foreach (string directory in FromAnkus())
        {
            Add(directory, DetectionSource.Ankus);
        }

        if (environment("PGDATA") is { Length: > 0 } pgdata && IsDataDirectory(pgdata))
        {
            Add(pgdata, DetectionSource.Pgdata);
        }

        foreach (string? directory in KnownPaths().Where(IsDataDirectory))
        {
            Add(directory, DetectionSource.KnownPath);
        }

        return instances;
    }

    /// <summary>
    /// Reads an instance again, for a server started, stopped, or reconfigured since it was detected.
    /// </summary>
    /// <param name="instance">The instance as detected.</param>
    /// <returns>The instance as it is now, with the same ID and source.</returns>
    public PostgresInstance Reread(PostgresInstance instance)
    {
        ArgumentNullException.ThrowIfNull(instance);
        return Describe(instance.Id, instance.DataDirectory, instance.Source, Running());
    }

    private static StringComparer PathComparer => OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal;

    // The data directories of running servers, resolved, with their process IDs.
    private Dictionary<string, int> Running()
    {
        var running = new Dictionary<string, int>(PathComparer);
        foreach ((string directory, int pid) in FromProcesses())
        {
            running.TryAdd(PathResolver.Resolve(directory, home), pid);
        }

        return running;
    }

    /// <summary>
    /// Finds the data directory in a postgres command line: <c>-D dir</c>, <c>-Ddir</c>, or <c>--data=dir</c>.
    /// </summary>
    /// <param name="arguments">The command line arguments.</param>
    /// <returns>The data directory, or null.</returns>
    public static string? DataDirectoryArgument(IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        for (int i = 0; i < arguments.Count; i++)
        {
            string argument = arguments[i];
            if (argument == "-D" && i + 1 < arguments.Count)
            {
                return arguments[i + 1];
            }

            if (argument.StartsWith("-D", StringComparison.Ordinal))
            {
                return argument[2..];
            }

            if (argument.StartsWith("--data=", StringComparison.Ordinal))
            {
                return argument[7..];
            }
        }

        return null;
    }

    private IEnumerable<(string Directory, int Pid)> FromProcesses()
    {
        foreach (ProcessEntry process in processes())
        {
            bool postgres = OperatingSystem.IsWindows()
                ? process.Name.Equals("postgres", StringComparison.OrdinalIgnoreCase)
                    || process.Name.Equals("pg_ctl", StringComparison.OrdinalIgnoreCase)
                : process.Name is "postgres" or "postmaster";
            if (postgres && DataDirectoryArgument(process.Arguments) is { Length: > 0 } directory && Directory.Exists(directory))
            {
                yield return (directory, process.Pid);
            }
        }
    }

    // The data directories in the pgrx home, PGRX_HOME or ~/.pgrx, which cargo pgrx names data-<major>.
    private IEnumerable<string> FromPgrx()
    {
        string pgrx = environment("PGRX_HOME") is { Length: > 0 } configured ? configured : Path.Join(home, ".pgrx");
        foreach (string directory in Matching(Path.Join(pgrx, "data-*")))
        {
            string suffix = Path.GetFileName(directory)[5..];
            if ((OperatingSystem.IsWindows() || (suffix.Length > 0 && suffix.All(char.IsAsciiDigit)))
                && File.Exists(Path.Join(directory, "PG_VERSION")))
            {
                yield return directory;
            }
        }
    }

    // The clusters in the ankus home, ANKUS_HOME or ~/.ankus, each marked with the file that holds its label.
    private IEnumerable<string> FromAnkus()
    {
        string ankus = environment("ANKUS_HOME") is { Length: > 0 } configured ? configured : Path.Join(home, ".ankus");
        foreach (string directory in Matching(Path.Join(ankus, "clusters", "*")))
        {
            if (File.Exists(Path.Join(directory, AnkusLauncher.MarkerFileName)) && File.Exists(Path.Join(directory, "PG_VERSION")))
            {
                yield return directory;
            }
        }
    }

    private IEnumerable<string> KnownPaths()
    {
        if (OperatingSystem.IsWindows())
        {
            string programFiles = environment("ProgramFiles") ?? @"C:\Program Files";
            string programFilesX86 = environment("ProgramFiles(x86)") ?? @"C:\Program Files (x86)";
            foreach (string? directory in Matching(Path.Join(programFiles, "PostgreSQL", "*", "data"))
                .Concat(Matching(Path.Join(programFilesX86, "PostgreSQL", "*", "data"))))
            {
                yield return directory;
            }

            if (environment("APPDATA") is { Length: > 0 } appData)
            {
                yield return Path.Join(appData, "PostgreSQL", "data");
            }

            if (environment("LOCALAPPDATA") is { Length: > 0 } localAppData)
            {
                yield return Path.Join(localAppData, "PostgreSQL", "data");
            }

            yield return Path.Join(home, "postgres");
            yield return Path.Join(home, "postgresql");
            yield return Path.Join(home, "PostgreSQL", "data");
            yield break;
        }

        // Homebrew, Debian and Ubuntu clusters, PGDG and distribution RPM layouts, Arch, and Postgres.app, for every version.
        string[] patterns =
        [
            "/usr/local/var/postgres",
            "/opt/homebrew/var/postgres",
            "/usr/local/var/postgresql@*",
            "/opt/homebrew/var/postgresql@*",
            "/var/lib/postgresql",
            "/var/lib/postgresql/data",
            "/var/lib/postgresql/*/*",
            "/var/lib/pgsql/data",
            "/var/lib/pgsql/*/data",
            "/var/lib/postgres/data",
            Path.Join(home, "Library", "Application Support", "Postgres", "var-*"),
            Path.Join(home, "postgres"),
            Path.Join(home, "postgresql"),
            Path.Join(home, ".postgres"),
        ];

        foreach (string pattern in patterns)
        {
            foreach (string directory in GlobPattern.IsGlob(pattern) ? Matching(pattern) : [pattern])
            {
                yield return directory;
            }
        }
    }

    private IReadOnlyList<string> Matching(string pattern)
    {
        try
        {
            return GlobPattern.FromPath(pattern, home, home).ExpandDirectories();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return [];
        }
    }

    // A Debian or Ubuntu cluster's data directory is closed to other users, but its configuration directory is not.
    private static bool IsDataDirectory(string path)
    {
        try
        {
            return Directory.Exists(path) && (File.Exists(Path.Join(path, "PG_VERSION"))
                || (PostgresConf.DebianConfFile(path) is { } conf && File.Exists(conf)));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }

    // An instance with its settings read once for its version, port, log, and launcher.
    private PostgresInstance Describe(int id, string directory, DetectionSource source, Dictionary<string, int> running)
    {
        (bool isRunning, int? pid) = IsRunning(PathResolver.Resolve(directory, home), running);
        ServerSettings settings = ServerSettings.Read(directory);
        ServerLauncher launcher = ServerLauncher.For(directory);
        (string? logPath, string? logDirectory, bool loggingEnabled) = PostgresConf.GetLogInfo(settings, launcher);
        return new PostgresInstance(
            id,
            PostgresConf.GetVersion(directory),
            directory,
            logPath,
            logDirectory,
            source,
            isRunning,
            launcher,
            pid,
            PostgresConf.GetPort(settings),
            loggingEnabled);
    }

    private static (bool Running, int? Pid) IsRunning(string resolved, Dictionary<string, int> running)
    {
        if (running.TryGetValue(resolved, out int known))
        {
            return (true, known);
        }

        try
        {
            string[] lines = File.ReadAllText(Path.Join(resolved, "postmaster.pid")).Split('\n');
            if (int.TryParse(lines[0].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int pid)
                && ProcessTable.NameOf(pid) is { } name && name.Contains("postgres", StringComparison.OrdinalIgnoreCase))
            {
                return (true, pid);
            }
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return (false, null);
        }

        return (false, null);
    }
}
