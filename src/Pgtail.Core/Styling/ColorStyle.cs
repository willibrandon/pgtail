using System.Globalization;
using Pgtail.Toml;

namespace Pgtail.Styling;

/// <summary>
/// A theme entry: foreground and background colors by name, and attributes.
/// </summary>
/// <param name="Fg">The foreground color name, or null.</param>
/// <param name="Bg">The background color name, or null.</param>
/// <param name="Bold">Whether the text is bold.</param>
/// <param name="Dim">Whether the text is dim.</param>
/// <param name="Italic">Whether the text is italic.</param>
/// <param name="Underline">Whether the text is underlined.</param>
public sealed record ColorStyle(
    string? Fg = null,
    string? Bg = null,
    bool Bold = false,
    bool Dim = false,
    bool Italic = false,
    bool Underline = false)
{
    /// <summary>
    /// The entry as a terminal style; a color name that is not valid leaves that color unset.
    /// </summary>
    /// <returns>The style.</returns>
    public TextStyle ToTextStyle()
    {
        TextAttributes attributes = (Bold ? TextAttributes.Bold : TextAttributes.None) | (Dim ? TextAttributes.Dim : TextAttributes.None)
            | (Italic ? TextAttributes.Italic : TextAttributes.None) | (Underline ? TextAttributes.Underline : TextAttributes.None);
        return new TextStyle(Color(Fg), Color(Bg), attributes);
    }

    /// <summary>
    /// Lists the color names that are not valid.
    /// </summary>
    /// <returns>One message per invalid color.</returns>
    public IReadOnlyList<string> Validate()
    {
        var errors = new List<string>();
        if (!string.IsNullOrEmpty(Fg) && !ColorParser.IsColor(Fg))
        {
            errors.Add($"Invalid foreground color: {Fg}");
        }

        if (!string.IsNullOrEmpty(Bg) && !ColorParser.IsColor(Bg))
        {
            errors.Add($"Invalid background color: {Bg}");
        }

        return errors;
    }

    /// <summary>
    /// Reads an entry from a TOML table.
    /// </summary>
    /// <remarks>
    /// The table may have <c>fg</c>, <c>bg</c>, <c>bold</c>, <c>dim</c>, <c>italic</c>, and <c>underline</c> keys.
    /// </remarks>
    /// <param name="table">The table.</param>
    /// <returns>The entry.</returns>
    public static ColorStyle FromTable(TomlTable table)
    {
        ArgumentNullException.ThrowIfNull(table);
        return new ColorStyle(Text(table, "fg"), Text(table, "bg"), Flag(table, "bold"), Flag(table, "dim"), Flag(table, "italic"),
            Flag(table, "underline"));
    }

    private static TerminalColor? Color(string? name) =>
        !string.IsNullOrEmpty(name) && ColorParser.TryParse(name, out TerminalColor color) ? color : null;

    private static string? Text(TomlTable table, string key) =>
        table.TryGetValue(key, out object? value) ? Convert.ToString(value, CultureInfo.InvariantCulture) : null;

    private static bool Flag(TomlTable table, string key) => table.TryGetValue(key, out object? value) && value switch
    {
        bool flag => flag,
        long number => number != 0,
        double real => real is > 0 or < 0,
        string text => text.Length > 0,
        TomlArray array => array.Count > 0,
        TomlTable nested => nested.Count > 0,
        _ => true,
    };
}
