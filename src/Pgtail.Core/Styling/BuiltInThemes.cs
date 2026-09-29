namespace Pgtail.Styling;

/// <summary>
/// The built-in themes.
/// </summary>
public static partial class BuiltInThemes
{
    /// <summary>
    /// The name of the default theme.
    /// </summary>
    public const string DefaultName = "dark";

    /// <summary>
    /// Every built-in theme by name.
    /// </summary>
    public static IReadOnlyDictionary<string, Theme> All => field ??= new Dictionary<string, Theme>(StringComparer.Ordinal)
    {
        [Dark.Name] = Dark,
        [Light.Name] = Light,
        [HighContrast.Name] = HighContrast,
        [Monokai.Name] = Monokai,
        [SolarizedDark.Name] = SolarizedDark,
        [SolarizedLight.Name] = SolarizedLight,
    };
}
