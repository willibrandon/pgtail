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
    /// Running processes come first, then pgrx data directories, then <c>PGDATA</c>, then platform default locations.
    /// A data directory found more than once is listed once, under its first source.
    /// </remarks>
    /// <returns>The instances, numbered from 0.</returns>
    public IReadOnlyList<PostgresInstance> DetectAll()
    {
        var instances = new List<PostgresInstance>();
        var seen = new HashSet<string>(OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
        var running = new Dictionary<string, int>(seen.Comparer);
        foreach (var (directory, pid) in FromProcesses())
        {
            running.TryAdd(PathResolver.Resolve(directory, home), pid);
        }

        void Add(string directory, DetectionSource source)
        {
            var resolved = PathResolver.Resolve(directory, home);
            if (!seen.Add(resolved))
            {
                return;
            }

            var (isRunning, pid) = IsRunning(resolved, running);
            var (logPath, logDirectory, loggingEnabled) = PostgresConf.GetLogInfo(directory);
            instances.Add(new PostgresInstance(
                instances.Count,
                PostgresConf.GetVersion(directory),
                directory,
                logPath,
                logDirectory,
                source,
                source == DetectionSource.Process || isRunning,
                pid,
                PostgresConf.GetPort(directory),
                loggingEnabled,
                PostgresConf.FindConfFile(directory)));
        }

        foreach (var directory in running.Keys)
        {
            Add(directory, DetectionSource.Process);
        }

        foreach (var directory in FromPgrx())
        {
            Add(directory, DetectionSource.Pgrx);
        }

        if (environment("PGDATA") is { Length: > 0 } pgdata && IsDataDirectory(pgdata))
        {
            Add(pgdata, DetectionSource.Pgdata);
        }

        foreach (var directory in KnownPaths().Where(IsDataDirectory))
        {
            Add(directory, DetectionSource.KnownPath);
        }

        return instances;
    }

    /// <summary>
    /// Finds the data directory in a postgres command line: <c>-D dir</c>, <c>-Ddir</c>, or <c>--data=dir</c>.
    /// </summary>
    /// <param name="arguments">The command line arguments.</param>
    /// <returns>The data directory, or null.</returns>
    public static string? DataDirectoryArgument(IReadOnlyList<string> arguments)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        for (var i = 0; i < arguments.Count; i++)
        {
            var argument = arguments[i];
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
        foreach (var process in processes())
        {
            var postgres = OperatingSystem.IsWindows()
                ? process.Name.Equals("postgres", StringComparison.OrdinalIgnoreCase)
                    || process.Name.Equals("pg_ctl", StringComparison.OrdinalIgnoreCase)
                : process.Name is "postgres" or "postmaster";
            if (postgres && DataDirectoryArgument(process.Arguments) is { Length: > 0 } directory && Directory.Exists(directory))
            {
                yield return (directory, process.Pid);
            }
        }
    }

    private IEnumerable<string> FromPgrx()
    {
        var pgrx = Path.Combine(home, ".pgrx");
        foreach (var directory in Matching(Path.Combine(pgrx, "data-*")))
        {
            var suffix = Path.GetFileName(directory)[5..];
            if ((OperatingSystem.IsWindows() || (suffix.Length > 0 && suffix.All(char.IsAsciiDigit)))
                && File.Exists(Path.Combine(directory, "PG_VERSION")))
            {
                yield return directory;
            }
        }
    }

    private IEnumerable<string> KnownPaths()
    {
        if (OperatingSystem.IsWindows())
        {
            var programFiles = environment("ProgramFiles") ?? @"C:\Program Files";
            var programFilesX86 = environment("ProgramFiles(x86)") ?? @"C:\Program Files (x86)";
            foreach (var directory in Matching(Path.Combine(programFiles, "PostgreSQL", "*", "data"))
                .Concat(Matching(Path.Combine(programFilesX86, "PostgreSQL", "*", "data"))))
            {
                yield return directory;
            }

            if (environment("APPDATA") is { Length: > 0 } appData)
            {
                yield return Path.Combine(appData, "PostgreSQL", "data");
            }

            if (environment("LOCALAPPDATA") is { Length: > 0 } localAppData)
            {
                yield return Path.Combine(localAppData, "PostgreSQL", "data");
            }

            yield return Path.Combine(home, "postgres");
            yield return Path.Combine(home, "postgresql");
            yield return Path.Combine(home, "PostgreSQL", "data");
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
            Path.Combine(home, "Library", "Application Support", "Postgres", "var-*"),
            Path.Combine(home, "postgres"),
            Path.Combine(home, "postgresql"),
            Path.Combine(home, ".postgres"),
        ];

        foreach (var pattern in patterns)
        {
            foreach (var directory in GlobPattern.IsGlob(pattern) ? Matching(pattern) : [pattern])
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
            return Directory.Exists(path) && (File.Exists(Path.Combine(path, "PG_VERSION"))
                || (PostgresConf.DebianConfFile(path) is { } conf && File.Exists(conf)));
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return false;
        }
    }

    private static (bool Running, int? Pid) IsRunning(string resolved, Dictionary<string, int> running)
    {
        if (running.TryGetValue(resolved, out var known))
        {
            return (true, known);
        }

        try
        {
            var lines = File.ReadAllText(Path.Combine(resolved, "postmaster.pid")).Split('\n');
            if (int.TryParse(lines[0].Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var pid)
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
