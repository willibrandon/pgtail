using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Detection;

/// <summary>
/// Finds PostgreSQL instances on this machine.
/// </summary>
/// <param name="environment">Reads an environment variable, such as <c>PGDATA</c>.</param>
/// <param name="home">The user's home directory.</param>
/// <param name="processes">Lists running processes.</param>
public sealed partial class InstanceDetector(Func<string, string?> environment, string home, Func<IReadOnlyList<ProcessEntry>> processes)
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
        if (!Directory.Exists(pgrx))
        {
            yield break;
        }

        IEnumerable<string> entries;
        try
        {
            entries = Directory.EnumerateDirectories(pgrx).ToList();
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            yield break;
        }

        foreach (var entry in entries)
        {
            var name = Path.GetFileName(entry);
            var matches = OperatingSystem.IsWindows() ? name.StartsWith("data-", StringComparison.Ordinal) : PgrxName().IsMatch(name);
            if (matches && File.Exists(Path.Combine(entry, "PG_VERSION")))
            {
                yield return entry;
            }
        }
    }

    private List<string> KnownPaths()
    {
        if (!OperatingSystem.IsWindows())
        {
            return
            [
                "/usr/local/var/postgres",
                "/opt/homebrew/var/postgres",
                "/usr/local/var/postgresql@16",
                "/usr/local/var/postgresql@15",
                "/usr/local/var/postgresql@14",
                "/opt/homebrew/var/postgresql@16",
                "/opt/homebrew/var/postgresql@15",
                "/opt/homebrew/var/postgresql@14",
                "/var/lib/postgresql",
                "/var/lib/pgsql/data",
                "/var/lib/postgresql/16/main",
                "/var/lib/postgresql/15/main",
                "/var/lib/postgresql/14/main",
                Path.Combine(home, "postgres"),
                Path.Combine(home, "postgresql"),
                Path.Combine(home, ".postgres"),
            ];
        }

        var paths = new List<string>();
        foreach (var programFiles in new[]
        {
            environment("ProgramFiles") ?? @"C:\Program Files",
            environment("ProgramFiles(x86)") ?? @"C:\Program Files (x86)",
        })
        {
            var postgres = Path.Combine(programFiles, "PostgreSQL");
            if (!Directory.Exists(postgres))
            {
                continue;
            }

            try
            {
                paths.AddRange(Directory.EnumerateDirectories(postgres).Select(version => Path.Combine(version, "data"))
                    .Where(Directory.Exists));
            }
            catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
            {
                // A PostgreSQL directory we cannot list holds nothing we can tail.
            }
        }

        if (environment("APPDATA") is { Length: > 0 } appData)
        {
            paths.Add(Path.Combine(appData, "PostgreSQL", "data"));
        }

        if (environment("LOCALAPPDATA") is { Length: > 0 } localAppData)
        {
            paths.Add(Path.Combine(localAppData, "PostgreSQL", "data"));
        }

        paths.Add(Path.Combine(home, "postgres"));
        paths.Add(Path.Combine(home, "postgresql"));
        paths.Add(Path.Combine(home, "PostgreSQL", "data"));
        return paths;
    }

    private static bool IsDataDirectory(string path)
    {
        try
        {
            return Directory.Exists(path) && File.Exists(Path.Combine(path, "PG_VERSION"));
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

    [GeneratedRegex("^data-[0-9]+$")]
    private static partial Regex PgrxName();
}
