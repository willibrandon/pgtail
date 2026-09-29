using Pgtail.Detection;
using Pgtail.Files;

namespace Pgtail.Commands;

/// <summary>
/// Resolves what <c>tail</c> reads: files and glob patterns, or an instance's log file.
/// </summary>
internal static class TailTargets
{
    /// <summary>
    /// Resolves file arguments, expanding glob patterns.
    /// </summary>
    /// <param name="arguments">The files and patterns as typed.</param>
    /// <param name="home">The home directory.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    /// <param name="warn">Receives a warning when a pattern matches many files.</param>
    /// <returns>The files and the first glob pattern, or the error to report.</returns>
    public static (List<string> Files, string? Glob, string? Error) ResolveFiles(
        IReadOnlyList<string> arguments,
        string home,
        string currentDirectory,
        Action<string> warn)
    {
        ArgumentNullException.ThrowIfNull(arguments);
        ArgumentNullException.ThrowIfNull(warn);
        var files = new List<string>();
        string? glob = null;
        foreach (var argument in arguments)
        {
            if (GlobPattern.IsGlob(argument))
            {
                var matches = GlobPattern.FromPath(argument, home, currentDirectory).Expand();
                if (matches.Count == 0)
                {
                    return ([], null, $"No files match pattern: {argument}");
                }

                if (matches.Count > 10)
                {
                    warn($"Pattern matches {matches.Count} files");
                }

                glob ??= argument;
                files.AddRange(matches);
                continue;
            }

            var (path, error) = ValidateFile(argument, home, currentDirectory);
            if (error is not null)
            {
                return ([], null, error);
            }

            files.Add(path);
        }

        return (files, glob, null);
    }

    /// <summary>
    /// Checks that a path names a readable file.
    /// </summary>
    /// <param name="argument">The path as typed.</param>
    /// <param name="home">The home directory.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    /// <returns>The resolved path, and the error, if any.</returns>
    public static (string Path, string? Error) ValidateFile(string argument, string home, string currentDirectory)
    {
        var path = PathResolver.Resolve(PathDisplay.Resolve(argument, home, currentDirectory), home);
        if (Directory.Exists(path))
        {
            return (path, $"Not a file: {path} (is a directory)");
        }

        if (!File.Exists(path))
        {
            return (path, $"File not found: {path}");
        }

        try
        {
            using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        }
        catch (UnauthorizedAccessException)
        {
            return (path, $"Permission denied: {path}");
        }
        catch (IOException exception)
        {
            return (path, $"Cannot access file: {path} ({exception.Message})");
        }

        return (path, null);
    }

    /// <summary>
    /// The log file to tail for an instance: its current log, or the newest in its log directory.
    /// </summary>
    /// <param name="instance">The instance.</param>
    /// <returns>The log file, or null.</returns>
    public static string? LogFile(PostgresInstance instance)
    {
        ArgumentNullException.ThrowIfNull(instance);
        return instance.LogPath ?? (instance.LogDirectory is { } directory && Directory.Exists(directory)
            ? PostgresConf.FindLatestLog(directory)
            : null);
    }
}
