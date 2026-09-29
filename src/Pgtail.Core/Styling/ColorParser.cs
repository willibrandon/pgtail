using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Styling;

/// <summary>
/// Reads color names in every form themes and styles accept.
/// </summary>
/// <remarks>
/// <list type="bullet">
/// <item><description><c>default</c> or <c>ansidefault</c> for the terminal's own color.</description></item>
/// <item><description>ANSI names such as <c>ansired</c>, <c>ansibrightblack</c>, <c>red</c>, or <c>bright_black</c>, which
/// follow the terminal's palette.</description></item>
/// <item><description>The 256-color palette names such as <c>dark_orange</c> or <c>grey50</c>, and <c>color(N)</c>.
/// </description></item>
/// <item><description>CSS names such as <c>DarkRed</c> or <c>cornflowerblue</c>.</description></item>
/// <item><description>Hex codes <c>#rgb</c> and <c>#rrggbb</c>, and <c>rgb(r,g,b)</c>.</description></item>
/// </list>
/// Names ignore case. The eight basic names such as <c>red</c> are palette colors rather than CSS colors.
/// </remarks>
public static partial class ColorParser
{
    private static readonly string[] AnsiNames = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"];

    /// <summary>
    /// Parses a color.
    /// </summary>
    /// <param name="text">The color.</param>
    /// <param name="color">The color, when the text is one.</param>
    /// <returns>True when the text is a color.</returns>
    public static bool TryParse(string text, out TerminalColor color)
    {
        ArgumentNullException.ThrowIfNull(text);
        color = default;
        var name = text.Trim().ToLowerInvariant();
        if (name.Length == 0)
        {
            return false;
        }

        if (name is "default" or "ansidefault")
        {
            color = TerminalColor.Default;
            return true;
        }

        if (name.StartsWith("ansi", StringComparison.Ordinal) && TryAnsi(name[4..], out color))
        {
            return true;
        }

        if (ColorTables.PaletteNames.TryGetValue(name, out var index))
        {
            color = TerminalColor.FromPalette(index);
            return true;
        }

        if (ColorTables.CssNames.TryGetValue(name, out var hex))
        {
            color = FromHex(hex);
            return true;
        }

        var hexMatch = Hex().Match(name);
        if (hexMatch.Success)
        {
            var digits = hexMatch.Groups[1].Value;
            color = FromHex(digits.Length == 3 ? string.Concat(digits.Select(c => $"{c}{c}")) : digits);
            return true;
        }

        var rgb = Rgb().Match(name);
        if (rgb.Success)
        {
            var parts = new int[3];
            for (var i = 0; i < 3; i++)
            {
                parts[i] = int.Parse(rgb.Groups[i + 1].ValueSpan, CultureInfo.InvariantCulture);
                if (parts[i] > 255)
                {
                    return false;
                }
            }

            color = TerminalColor.FromRgb((byte)parts[0], (byte)parts[1], (byte)parts[2]);
            return true;
        }

        var palette = Palette().Match(name);
        if (palette.Success && int.TryParse(palette.Groups[1].ValueSpan, CultureInfo.InvariantCulture, out var number) && number <= 255)
        {
            color = TerminalColor.FromPalette(number);
            return true;
        }

        return false;
    }

    /// <summary>
    /// Whether a text names a color.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>True for a color.</returns>
    public static bool IsColor(string text) => TryParse(text, out _);

    private static bool TryAnsi(string name, out TerminalColor color)
    {
        color = default;
        var bright = name.StartsWith("bright", StringComparison.Ordinal);
        var basic = bright ? name[6..] : name;
        basic = basic switch
        {
            "gray" or "grey" or "lightgray" => "white",
            "darkgray" => bright ? "" : "brightblack",
            "teal" => "cyan",
            "turquoise" => bright ? "" : "brightcyan",
            "brown" => "yellow",
            "purple" => "magenta",
            "fuchsia" => bright ? "" : "brightmagenta",
            "darkred" => "red",
            "darkgreen" => "green",
            "darkblue" => "blue",
            _ => basic,
        };

        if (basic.StartsWith("bright", StringComparison.Ordinal))
        {
            bright = true;
            basic = basic[6..];
        }

        var index = Array.IndexOf(AnsiNames, basic);
        if (index < 0)
        {
            return false;
        }

        color = TerminalColor.FromPalette(index + (bright ? 8 : 0));
        return true;
    }

    private static TerminalColor FromHex(string hex) => TerminalColor.FromRgb(
        byte.Parse(hex.AsSpan(0, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
        byte.Parse(hex.AsSpan(2, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture),
        byte.Parse(hex.AsSpan(4, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture));

    [GeneratedRegex("^#([0-9a-f]{3}|[0-9a-f]{6})$")]
    private static partial Regex Hex();

    [GeneratedRegex(@"^rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)$")]
    private static partial Regex Rgb();

    [GeneratedRegex(@"^color\(\s*([0-9]{1,3})\s*\)$")]
    private static partial Regex Palette();
}
