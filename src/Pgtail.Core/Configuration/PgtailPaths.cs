namespace Pgtail.Configuration;

/// <summary>
/// Where pgtail keeps its configuration, themes, and history.
/// </summary>
/// <param name="ConfigDirectory">The directory holding <c>config.toml</c> and <c>themes</c>.</param>
/// <param name="DataDirectory">The directory holding command history.</param>
public sealed record PgtailPaths(string ConfigDirectory, string DataDirectory)
{
    /// <summary>
    /// The application directory name.
    /// </summary>
    public const string ApplicationName = "pgtail";

    /// <summary>
    /// The configuration file.
    /// </summary>
    public string ConfigFile => Path.Combine(ConfigDirectory, "config.toml");

    /// <summary>
    /// The directory of custom themes.
    /// </summary>
    public string ThemesDirectory => Path.Combine(ConfigDirectory, "themes");

    /// <summary>
    /// The REPL command history.
    /// </summary>
    public string HistoryFile => Path.Combine(DataDirectory, "history");

    /// <summary>
    /// The tail mode command history.
    /// </summary>
    public string TailHistoryFile => Path.Combine(DataDirectory, "tail_history");

    /// <summary>
    /// The platform locations for the current user.
    /// </summary>
    /// <remarks>
    /// <list type="bullet">
    /// <item><description>macOS: <c>~/Library/Application Support/pgtail</c> for both.</description></item>
    /// <item><description>Windows: <c>%APPDATA%\pgtail</c> for both.</description></item>
    /// <item><description>Linux and other Unix systems: <c>$XDG_CONFIG_HOME/pgtail</c> (default <c>~/.config/pgtail</c>) for
    /// configuration and <c>$XDG_DATA_HOME/pgtail</c> (default <c>~/.local/share/pgtail</c>) for history.</description></item>
    /// </list>
    /// </remarks>
    /// <param name="environment">Reads an environment variable.</param>
    /// <returns>The paths.</returns>
    public static PgtailPaths ForCurrentUser(Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(environment);
        var home = environment(OperatingSystem.IsWindows() ? "USERPROFILE" : "HOME") is { Length: > 0 } profile
            ? profile
            : Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
        if (OperatingSystem.IsMacOS())
        {
            var support = Path.Combine(home, "Library", "Application Support", ApplicationName);
            return new PgtailPaths(support, support);
        }

        if (OperatingSystem.IsWindows())
        {
            var roaming = environment("APPDATA") is { Length: > 0 } appData ? appData : Path.Combine(home, "AppData", "Roaming");
            var directory = Path.Combine(roaming, ApplicationName);
            return new PgtailPaths(directory, directory);
        }

        var config = environment("XDG_CONFIG_HOME") is { Length: > 0 } xdgConfig ? xdgConfig : Path.Combine(home, ".config");
        var data = environment("XDG_DATA_HOME") is { Length: > 0 } xdgData ? xdgData : Path.Combine(home, ".local", "share");
        return new PgtailPaths(Path.Combine(config, ApplicationName), Path.Combine(data, ApplicationName));
    }
}
