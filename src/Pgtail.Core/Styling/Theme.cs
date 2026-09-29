using System.Collections.Concurrent;
using System.Text.RegularExpressions;

namespace Pgtail.Styling;

/// <summary>
/// A named set of styles for log levels and interface elements.
/// </summary>
/// <param name="name">The theme name, such as <c>dark</c> or <c>monokai</c>.</param>
/// <param name="description">A short description.</param>
/// <param name="levels">Styles by upper case level name, such as <c>ERROR</c>; <c>DEBUG</c> covers DEBUG1 through DEBUG5.</param>
/// <param name="ui">Styles by element name, such as <c>timestamp</c> or <c>hl_sqlstate_error</c>.</param>
public sealed partial class Theme(
    string name,
    string description,
    IReadOnlyDictionary<string, ColorStyle> levels,
    IReadOnlyDictionary<string, ColorStyle> ui)
{
    private static readonly string[] RequiredLevels = ["ERROR", "LOG", "WARNING"];
    private readonly ConcurrentDictionary<string, TextStyle> _resolved = new(StringComparer.Ordinal);
    private static readonly string[] RequiredElements = ["highlight", "timestamp"];

    /// <summary>
    /// The theme name.
    /// </summary>
    public string Name { get; } = name;

    /// <summary>
    /// A short description.
    /// </summary>
    public string Description { get; } = description;

    /// <summary>
    /// Styles by upper case level name.
    /// </summary>
    public IReadOnlyDictionary<string, ColorStyle> Levels { get; } = levels;

    /// <summary>
    /// Styles by element name.
    /// </summary>
    public IReadOnlyDictionary<string, ColorStyle> Ui { get; } = ui;

    /// <summary>
    /// Lists what is missing or invalid.
    /// </summary>
    /// <remarks>
    /// A theme needs a lower case alphanumeric name with hyphens, the ERROR, WARNING, and LOG levels, and the
    /// <c>timestamp</c> and <c>highlight</c> elements, and every color must be valid.
    /// </remarks>
    /// <returns>The problems, empty for a valid theme.</returns>
    public IReadOnlyList<string> Validate()
    {
        var errors = new List<string>();
        if (Name.Length == 0)
        {
            errors.Add("Theme name is required");
        }
        else if (!ThemeName().IsMatch(Name))
        {
            errors.Add("Theme name must be lowercase alphanumeric with hyphens");
        }

        var missingLevels = RequiredLevels.Where(level => !Levels.ContainsKey(level)).ToList();
        if (missingLevels.Count > 0)
        {
            errors.Add($"Missing required log levels: {string.Join(", ", missingLevels)}");
        }

        var missingUi = RequiredElements.Where(element => !Ui.ContainsKey(element)).ToList();
        if (missingUi.Count > 0)
        {
            errors.Add($"Missing required UI elements: {string.Join(", ", missingUi)}");
        }

        foreach (var (level, style) in Levels)
        {
            errors.AddRange(style.Validate().Select(error => $"levels.{level}: {error}"));
        }

        foreach (var (element, style) in Ui)
        {
            errors.AddRange(style.Validate().Select(error => $"ui.{element}: {error}"));
        }

        return errors;
    }

    /// <summary>
    /// The style of a level, inheriting DEBUG for DEBUG1 through DEBUG5 and LOG for anything else missing.
    /// </summary>
    /// <param name="level">The upper case level name.</param>
    /// <returns>The style.</returns>
    public ColorStyle GetLevelStyle(string level)
    {
        ArgumentNullException.ThrowIfNull(level);
        if (Levels.TryGetValue(level, out var style))
        {
            return style;
        }

        if (level.StartsWith("DEBUG", StringComparison.Ordinal) && Levels.TryGetValue("DEBUG", out var debug))
        {
            return debug;
        }

        return Levels.TryGetValue("LOG", out var log) ? log : new ColorStyle();
    }

    /// <summary>
    /// The terminal style of an element, plain when the theme does not define it.
    /// </summary>
    /// <param name="element">The element name.</param>
    /// <returns>The style.</returns>
    public TextStyle Style(string element) => Ui.TryGetValue(element, out var style) ? style.ToTextStyle() : TextStyle.Plain;

    /// <summary>
    /// Resolves a highlight style: a theme element name, or else a style string such as <c>bold red</c>.
    /// </summary>
    /// <remarks>
    /// A name that is neither an element of the theme nor a valid style string resolves to the plain style.
    /// </remarks>
    /// <param name="key">The element name or style string.</param>
    /// <returns>The style.</returns>
    public TextStyle ResolveStyle(string key)
    {
        ArgumentNullException.ThrowIfNull(key);
        return _resolved.GetOrAdd(key, static (name, theme) => theme.Ui.TryGetValue(name, out var style)
            ? style.ToTextStyle()
            : StyleParser.TryParse(name, out var parsed, out _) ? parsed : TextStyle.Plain, this);
    }

    [GeneratedRegex("^[a-z0-9-]+$")]
    private static partial Regex ThemeName();
}
