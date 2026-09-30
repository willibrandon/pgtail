using System.Text;
using Pgtail.Detection;
using Scout.IO.Globbing;
using Scout.IO.Ignore;

namespace Pgtail.Files;

/// <summary>
/// A path pattern such as <c>*.log</c>, <c>/var/log/postgresql/*.log</c>, or <c>logs/**/*.csv</c>.
/// </summary>
/// <remarks>
/// The pattern is split into the directory before its first wildcard and the relative pattern after it. Patterns use
/// <c>*</c>, <c>?</c>, <c>[...]</c>, <c>{a,b}</c>, and <c>**</c> for any number of directories; wildcards do not cross
/// directory separators. Hidden files match, and ignore files such as <c>.gitignore</c> are not consulted, because log
/// directories are usually ignored by version control. Matching ignores case on Windows.
/// </remarks>
/// <param name="Directory">The directory the pattern is relative to.</param>
/// <param name="Pattern">The relative pattern, with <c>/</c> separators.</param>
/// <param name="Original">The pattern as the user wrote it.</param>
public sealed record GlobPattern(string Directory, string Pattern, string Original)
{
    private static readonly char[] s_wildcards = ['*', '?', '[', '{'];

    /// <summary>
    /// Whether a path contains wildcard characters.
    /// </summary>
    /// <param name="path">The path.</param>
    /// <returns>True for a pattern.</returns>
    public static bool IsGlob(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        return path.IndexOfAny(s_wildcards) >= 0;
    }

    /// <summary>
    /// Splits a user's path pattern into a directory and a relative pattern.
    /// </summary>
    /// <param name="path">The pattern, possibly starting with <c>~</c>.</param>
    /// <param name="home">The home directory that <c>~</c> stands for.</param>
    /// <param name="currentDirectory">The directory a relative pattern starts from.</param>
    /// <returns>The pattern.</returns>
    public static GlobPattern FromPath(string path, string home, string currentDirectory)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(home);
        ArgumentNullException.ThrowIfNull(currentDirectory);
        string expanded = path == "~" || path.StartsWith("~/", StringComparison.Ordinal) || path.StartsWith("~\\", StringComparison.Ordinal)
            ? home + path[1..]
            : path;
        string root = Path.IsPathRooted(expanded) ? Path.GetPathRoot(expanded) ?? "" : "";
        string[] parts = expanded[root.Length..].Split(['/', '\\'], StringSplitOptions.RemoveEmptyEntries);
        int first = Array.FindIndex(parts, part => part.IndexOfAny(s_wildcards) >= 0);
        string directory;
        string pattern;
        if (first < 0)
        {
            directory = root + string.Join(Path.DirectorySeparatorChar, parts[..^1]);
            pattern = parts.Length > 0 ? parts[^1] : "*";
        }
        else
        {
            directory = root + string.Join(Path.DirectorySeparatorChar, parts[..first]);
            pattern = string.Join('/', parts[first..]);
        }

        directory = directory.Length == 0 ? currentDirectory
            : Path.IsPathRooted(directory) ? directory
            : Path.Join(currentDirectory, directory);
        return new GlobPattern(PathResolver.Resolve(directory, home), pattern, path);
    }

    /// <summary>
    /// Finds the files the pattern matches.
    /// </summary>
    /// <returns>The files, most recently modified first.</returns>
    public IReadOnlyList<string> Expand() =>
        [.. Walk(directories: false).OrderByDescending(File.GetLastWriteTimeUtc).ThenBy(file => file, StringComparer.Ordinal)];

    /// <summary>
    /// Finds the directories the pattern matches.
    /// </summary>
    /// <returns>The directories in name order.</returns>
    public IReadOnlyList<string> ExpandDirectories() => [.. Walk(directories: true).Order(StringComparer.Ordinal)];

    private IEnumerable<string> Walk(bool directories)
    {
        if (!System.IO.Directory.Exists(Directory))
        {
            yield break;
        }

        GlobOptions globOptions = OperatingSystem.IsWindows()
            ? new GlobOptions(literalSeparator: true, backslashEscapes: false, asciiCaseInsensitive: true,
                pathSeparators: "/\\"u8.ToArray())
            : GlobOptions.UnixLiteralSeparator;
        Glob glob;
        try
        {
            glob = Glob.Parse(Encoding.UTF8.GetBytes(Pattern), globOptions);
        }
        catch (GlobParseException)
        {
            yield break;
        }

        string[] segments = Pattern.Split('/');
        var options = new FileWalkerOptions
        {
            MaxDepth = segments.Contains("**") ? null : segments.Length,
            IgnoreHidden = false,
            ReadIgnoreFiles = false,
            ReadParentIgnoreFiles = false,
            ReadGitIgnoreFiles = false,
            ReadGitExcludeFiles = false,
            ReadGlobalGitIgnore = false,
            FollowSymbolicLinks = false,
        };

        foreach (FileWalkEntry entry in new FileWalker(options).Enumerate(Directory))
        {
            bool isDirectory = entry.IsDirectory || (entry.IsSymbolicLink && System.IO.Directory.Exists(entry.FullPath));
            bool isFile = entry.IsFile || (entry.IsSymbolicLink && File.Exists(entry.FullPath));
            if ((directories ? !isDirectory : !isFile) || entry.IsStdin)
            {
                continue;
            }

            string relative = Path.GetRelativePath(Directory, entry.FullPath).Replace('\\', '/');
            if (glob.IsMatch(Encoding.UTF8.GetBytes(relative)))
            {
                yield return entry.FullPath;
            }
        }
    }
}
