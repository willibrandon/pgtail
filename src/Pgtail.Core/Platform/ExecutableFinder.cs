namespace Pgtail.Platform;

/// <summary>
/// Finds programs on the search path.
/// </summary>
public static class ExecutableFinder
{
    /// <summary>
    /// The full path of a program on <c>PATH</c>, trying each <c>PATHEXT</c> extension on Windows.
    /// </summary>
    /// <param name="name">The program name, such as <c>notify-send</c>.</param>
    /// <param name="environment">Reads environment variables.</param>
    /// <returns>The path, or null when the program is not found.</returns>
    public static string? Find(string name, Func<string, string?> environment)
    {
        ArgumentException.ThrowIfNullOrEmpty(name);
        ArgumentNullException.ThrowIfNull(environment);
        string? path = environment("PATH");
        if (string.IsNullOrEmpty(path))
        {
            return null;
        }

        string[] extensions = OperatingSystem.IsWindows()
            ? [.. (environment("PATHEXT") ?? ".COM;.EXE;.BAT;.CMD").Split(';', StringSplitOptions.RemoveEmptyEntries)]
            : [""];
        foreach (string directory in path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
        {
            foreach (string extension in extensions)
            {
                string candidate = Path.Join(directory, name + extension);
                if (IsExecutable(candidate))
                {
                    return candidate;
                }
            }
        }

        return null;
    }

    private static bool IsExecutable(string path)
    {
        if (!File.Exists(path))
        {
            return false;
        }

        if (OperatingSystem.IsWindows())
        {
            return true;
        }

        const UnixFileMode anyExecute = UnixFileMode.UserExecute | UnixFileMode.GroupExecute | UnixFileMode.OtherExecute;
        return (File.GetUnixFileMode(path) & anyExecute) != 0;
    }
}
