namespace Pgtail.Detection;

/// <summary>
/// Paths in PostgreSQL settings and files, read as the server reads them.
/// </summary>
public static class PostgresPath
{
    /// <summary>
    /// Whether PostgreSQL takes a path as absolute on this platform, as <c>is_absolute_path</c> does.
    /// </summary>
    /// <param name="path">The path.</param>
    /// <returns>True when the path is absolute.</returns>
    public static bool IsAbsolute(string path) => IsAbsolute(path, OperatingSystem.IsWindows());

    /// <summary>
    /// Whether PostgreSQL takes a path as absolute on Windows or on another platform, as <c>is_absolute_path</c> does.
    /// </summary>
    /// <remarks>
    /// On Windows a path is absolute when it starts with a slash or a backslash, or with a drive letter, a colon, and a
    /// separator. A drive-relative path such as <c>C:pglogs</c> is relative. Elsewhere only a leading slash makes a path
    /// absolute.
    /// </remarks>
    /// <param name="path">The path.</param>
    /// <param name="windows">True for the Windows rule.</param>
    /// <returns>True when the path is absolute.</returns>
    public static bool IsAbsolute(string path, bool windows)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (!windows)
        {
            return path.StartsWith('/');
        }

        return path.StartsWith('/') || path.StartsWith('\\')
            || (path.Length >= 3 && char.IsAsciiLetter(path[0]) && path[1] == ':' && path[2] is '/' or '\\');
    }

    /// <summary>
    /// The full path of a file or directory the server opens, such as <c>log_directory</c>.
    /// </summary>
    /// <remarks>
    /// The files in <c>current_logfiles</c> are the same. The server opens these paths as they are, from the data
    /// directory, which is its working directory. An absolute path keeps its place, and on Windows one that starts with a
    /// separator is on the data directory's drive. A relative path, a drive-relative one included, starts from the data
    /// directory.
    /// </remarks>
    /// <param name="path">The path as the setting or the file gives it.</param>
    /// <param name="dataDirectory">The data directory.</param>
    /// <returns>The full path.</returns>
    public static string Resolve(string path, string dataDirectory)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(dataDirectory);
        return Path.GetFullPath(path, Path.GetFullPath(dataDirectory));
    }

    /// <summary>
    /// The full path of a file or directory that an include line names, as <c>AbsoluteConfigLocation</c> finds it.
    /// </summary>
    /// <remarks>
    /// The lines are <c>include</c>, <c>include_if_exists</c>, and <c>include_dir</c>.
    /// </remarks>
    /// <param name="location">The path the line gives.</param>
    /// <param name="includingFile">The file that holds the line.</param>
    /// <returns>An absolute path in its place, or a relative one joined to the including file's directory.</returns>
    public static string Include(string location, string includingFile)
    {
        ArgumentNullException.ThrowIfNull(location);
        ArgumentNullException.ThrowIfNull(includingFile);
        string directory = Path.GetDirectoryName(Path.GetFullPath(includingFile)) ?? Path.GetFullPath(includingFile);
        return IsAbsolute(location) ? Path.GetFullPath(location, directory) : Path.GetFullPath(Path.Join(directory, location));
    }
}
