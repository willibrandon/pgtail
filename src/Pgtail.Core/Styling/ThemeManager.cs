namespace Pgtail.Styling;

/// <summary>
/// The built-in and custom themes, and the one in use.
/// </summary>
/// <param name="themesDirectory">The directory custom themes are read from.</param>
public sealed class ThemeManager(string themesDirectory)
{
    private readonly Dictionary<string, Theme> _custom = new(StringComparer.Ordinal);

    /// <summary>
    /// The directory custom themes are read from.
    /// </summary>
    public string ThemesDirectory { get; } = themesDirectory;

    /// <summary>
    /// The theme in use.
    /// </summary>
    public Theme Current { get; private set; } = BuiltInThemes.Dark;

    /// <summary>
    /// Whether a name is a built-in theme.
    /// </summary>
    /// <param name="name">The theme name.</param>
    /// <returns>True for a built-in theme.</returns>
    public static bool IsBuiltIn(string name) => BuiltInThemes.All.ContainsKey(name);

    /// <summary>
    /// The file a custom theme is kept in.
    /// </summary>
    /// <param name="name">The theme name.</param>
    /// <returns>The path.</returns>
    public string ThemeFile(string name) => Path.Combine(ThemesDirectory, name + ".toml");

    /// <summary>
    /// Reads every custom theme file again.
    /// </summary>
    /// <remarks>
    /// Files that resolve outside the themes directory through links are ignored, as are files that cannot be parsed.
    /// </remarks>
    public void ScanCustomThemes()
    {
        _custom.Clear();
        if (!Directory.Exists(ThemesDirectory))
        {
            return;
        }

        string root = Path.GetFullPath(ThemesDirectory);
        string resolvedRoot = ResolvePath(root);
        foreach (string file in Directory.EnumerateFiles(root, "*.toml"))
        {
            if (!ResolvePath(file).StartsWith(resolvedRoot, StringComparison.Ordinal))
            {
                continue;
            }

            if (ThemeLoader.Load(file).Theme is { } theme)
            {
                _custom[theme.Name] = theme;
            }
        }
    }

    /// <summary>
    /// Lists the built-in and custom theme names, reading custom themes again first.
    /// </summary>
    /// <returns>The sorted names of each kind.</returns>
    public (IReadOnlyList<string> BuiltIn, IReadOnlyList<string> Custom) ListThemes()
    {
        ScanCustomThemes();
        return ([.. BuiltInThemes.All.Keys.Order(StringComparer.Ordinal)], [.. _custom.Keys.Order(StringComparer.Ordinal)]);
    }

    /// <summary>
    /// Finds a theme, preferring a custom theme to a built-in one of the same name.
    /// </summary>
    /// <param name="name">The theme name.</param>
    /// <returns>The theme, or null.</returns>
    public Theme? GetTheme(string name) =>
        _custom.TryGetValue(name, out Theme? custom) ? custom : BuiltInThemes.All.GetValueOrDefault(name);

    /// <summary>
    /// Switches to a theme, reading custom themes again first.
    /// </summary>
    /// <param name="name">The theme name.</param>
    /// <returns>True when the theme exists.</returns>
    public bool Switch(string name)
    {
        ScanCustomThemes();
        if (GetTheme(name) is not { } theme)
        {
            return false;
        }

        Current = theme;
        return true;
    }

    /// <summary>
    /// Reads the current theme from disk again.
    /// </summary>
    /// <returns>Whether it was reloaded, and the message to show.</returns>
    public (bool Success, string Message) ReloadCurrent()
    {
        string name = Current.Name;
        if (IsBuiltIn(name) && !File.Exists(ThemeFile(name)))
        {
            return (true, $"Theme '{name}' reloaded.");
        }

        string file = ThemeFile(name);
        if (!File.Exists(file))
        {
            Current = BuiltInThemes.Dark;
            return (false, $"Theme file not found: {file}\nSwitched to the default theme: {BuiltInThemes.DefaultName}");
        }

        (Theme? theme, IReadOnlyList<string>? errors) = ThemeLoader.Load(file);
        if (theme is null)
        {
            return (false, $"Failed to reload theme '{name}':\n  {string.Join("\n  ", errors)}\n\nKeeping previous theme active.");
        }

        _custom[name] = theme;
        Current = theme;
        return (true, $"Theme '{name}' reloaded.");
    }

    private static string ResolvePath(string path)
    {
        string full = Path.GetFullPath(path);
        var info = new FileInfo(full);
        return info.LinkTarget is not null && info.ResolveLinkTarget(returnFinalTarget: true) is { } target ? target.FullName : full;
    }
}
