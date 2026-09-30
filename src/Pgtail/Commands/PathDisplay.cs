namespace Pgtail.Commands;

/// <summary>
/// Shortens paths for display.
/// </summary>
internal static class PathDisplay
{
    /// <summary>
    /// Replaces a leading home directory with <c>~</c>.
    /// </summary>
    /// <param name="path">The path.</param>
    /// <param name="home">The home directory.</param>
    /// <returns>The shortened path.</returns>
    public static string Shorten(string path, string home)
    {
        ArgumentNullException.ThrowIfNull(path);
        ArgumentNullException.ThrowIfNull(home);
        return home.Length > 0 && path.StartsWith(home, StringComparison.Ordinal) ? "~" + path[home.Length..] : path;
    }

    /// <summary>
    /// Expands a leading <c>~</c> and makes a path absolute.
    /// </summary>
    /// <param name="path">The path as typed.</param>
    /// <param name="home">The home directory.</param>
    /// <param name="currentDirectory">The directory relative paths start from.</param>
    /// <returns>The full path.</returns>
    public static string Resolve(string path, string home, string currentDirectory)
    {
        ArgumentNullException.ThrowIfNull(path);
        if (path == "~" || path.StartsWith("~/", StringComparison.Ordinal) || path.StartsWith("~\\", StringComparison.Ordinal))
        {
            path = home + path[1..];
        }

        return Path.GetFullPath(path, currentDirectory);
    }
}
