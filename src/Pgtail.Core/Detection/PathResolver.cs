namespace Pgtail.Detection;

/// <summary>
/// Makes paths absolute and follows symbolic links, so two spellings of one directory compare equal.
/// </summary>
public static class PathResolver
{
    /// <summary>
    /// Resolves a path: absolute, with <c>~</c> expanded and every link along it followed.
    /// </summary>
    /// <remarks>
    /// The part of the path that exists is resolved; the rest is kept as written.
    /// </remarks>
    /// <param name="path">The path.</param>
    /// <param name="home">The home directory that <c>~</c> stands for.</param>
    /// <returns>The resolved path.</returns>
    public static string Resolve(string path, string? home = null)
    {
        ArgumentNullException.ThrowIfNull(path);
        home ??= Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (path == "~" || path.StartsWith("~/", StringComparison.Ordinal) || path.StartsWith("~\\", StringComparison.Ordinal))
        {
            path = home + path[1..];
        }

        string full = Path.GetFullPath(path);
        string root = Path.GetPathRoot(full) ?? "";
        string[] parts = full[root.Length..].Split([Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar],
            StringSplitOptions.RemoveEmptyEntries);
        string current = root;
        for (int i = 0; i < parts.Length; i++)
        {
            string next = Path.Combine(current, parts[i]);
            FileSystemInfo info = Directory.Exists(next) ? new DirectoryInfo(next) : new FileInfo(next);
            if (!info.Exists)
            {
                return Path.Combine([current, .. parts[i..]]);
            }

            try
            {
                current = info.LinkTarget is not null && info.ResolveLinkTarget(returnFinalTarget: true) is { } target
                    ? Path.GetFullPath(target.FullName)
                    : next;
            }
            catch (IOException)
            {
                current = next;
            }
        }

        return current;
    }
}
