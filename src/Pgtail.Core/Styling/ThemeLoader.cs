using System.Globalization;
using System.Text;
using Pgtail.Toml;

namespace Pgtail.Styling;

/// <summary>
/// Reads custom themes from TOML files.
/// </summary>
/// <remarks>
/// A theme file has an optional <c>[meta]</c> table with a <c>description</c>, a <c>[levels]</c> table of level styles,
/// and a <c>[ui]</c> table of element styles. Each style is a table such as <c>{ fg = "red", bold = true }</c>. The
/// theme's name is the file name without its extension.
/// </remarks>
public static class ThemeLoader
{
    /// <summary>
    /// The template written for a new custom theme; <c>{name}</c> stands for the theme name.
    /// </summary>
    public const string Template = """
        # Custom pgtail theme
        # See: https://pgtail.dev/guide/themes/

        [meta]
        name = "{name}"
        description = "Custom color scheme"

        [levels]
        # Log level colors - use ANSI names, hex codes (#rgb/#rrggbb), or CSS colors
        PANIC = { fg = "white", bg = "red", bold = true }
        FATAL = { fg = "red", bold = true }
        ERROR = { fg = "#ff6b6b" }
        WARNING = { fg = "#ffd93d" }
        NOTICE = { fg = "#6bcb77" }
        LOG = { fg = "default" }
        INFO = { fg = "#4d96ff" }
        DEBUG = { fg = "#888888" }
        # DEBUG1-5 inherit from DEBUG if not specified

        [ui]
        # UI element colors
        prompt = { fg = "green" }
        timestamp = { fg = "gray" }
        pid = { fg = "gray" }
        highlight = { bg = "yellow", fg = "black" }
        slow_warning = { fg = "yellow" }
        slow_slow = { fg = "yellow", bold = true }
        slow_critical = { fg = "red", bold = true }
        detail = { fg = "default" }

        # SQL syntax highlighting colors (optional - falls back to default text if omitted)
        sql_keyword = { fg = "blue", bold = true }
        sql_identifier = { fg = "cyan" }
        sql_string = { fg = "green" }
        sql_number = { fg = "magenta" }
        sql_operator = { fg = "yellow" }
        sql_comment = { fg = "gray" }
        sql_function = { fg = "blue" }

        """;

    /// <summary>
    /// Loads a theme file, reporting every problem found.
    /// </summary>
    /// <param name="path">The file.</param>
    /// <returns>The theme, or null when the file cannot be read or parsed, and the problems found.</returns>
    public static (Theme? Theme, IReadOnlyList<string> Errors) Load(string path)
    {
        ArgumentNullException.ThrowIfNull(path);
        TomlDocument document;
        try
        {
            document = TomlDocument.Load(path);
        }
        catch (IOException exception)
        {
            return (null, [$"Cannot read file: {exception.Message}"]);
        }
        catch (UnauthorizedAccessException exception)
        {
            return (null, [$"Cannot read file: {exception.Message}"]);
        }
        catch (TomlException exception)
        {
            return (null, [$"TOML parse error: {exception.Message}"]);
        }

        return FromDocument(Path.GetFileNameWithoutExtension(path), document);
    }

    /// <summary>
    /// Reads a theme from TOML text, as the built-in editor checks it before saving.
    /// </summary>
    /// <param name="name">The theme name.</param>
    /// <param name="text">The TOML text.</param>
    /// <returns>The theme, or null when the text cannot be parsed, and the problems found.</returns>
    public static (Theme? Theme, IReadOnlyList<string> Errors) FromText(string name, string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        try
        {
            return FromDocument(name, TomlDocument.Parse(Encoding.UTF8.GetBytes(text)));
        }
        catch (TomlException exception)
        {
            return (null, [$"TOML parse error: {exception.Message}"]);
        }
    }

    private static (Theme? Theme, IReadOnlyList<string> Errors) FromDocument(string name, TomlDocument document)
    {
        var errors = new List<string>();
        string description = document.Root.TryGetTable("meta", out TomlTable? meta) && meta.TryGetValue("description", out object? text)
            ? Convert.ToString(text, CultureInfo.InvariantCulture) ?? ""
            : "";
        Dictionary<string, ColorStyle> levels = ReadStyles(document.Root, "levels", errors, upperCase: true);
        Dictionary<string, ColorStyle> ui = ReadStyles(document.Root, "ui", errors, upperCase: false);
        var theme = new Theme(name, description, levels, ui);
        errors.AddRange(theme.Validate());
        return (theme, errors);
    }

    private static Dictionary<string, ColorStyle> ReadStyles(TomlTable root, string section, List<string> errors, bool upperCase)
    {
        var styles = new Dictionary<string, ColorStyle>(StringComparer.Ordinal);
        if (!root.TryGetTable(section, out TomlTable? table))
        {
            return styles;
        }

        foreach ((string name, object value) in table)
        {
            if (value is not TomlTable entry)
            {
                errors.Add($"[{section}.{name}] Expected table, got {TypeName(value)}");
                continue;
            }

            var style = ColorStyle.FromTable(entry);
            errors.AddRange(style.Validate().Select(error => $"[{section}.{name}] {error}"));
            styles[upperCase ? name.ToUpperInvariant() : name] = style;
        }

        return styles;
    }

    private static string TypeName(object value) => value switch
    {
        string => "str",
        long => "int",
        double => "float",
        bool => "bool",
        TomlArray => "list",
        _ => "datetime",
    };
}
