using System.Globalization;

namespace Pgtail.Styling;

/// <summary>
/// A terminal color that keeps its palette encoding, so ANSI colors follow the user's terminal palette.
/// </summary>
/// <param name="Kind">How the color is encoded.</param>
/// <param name="Index">The palette index: 0-7 for standard and bright colors, 0-255 for indexed colors.</param>
/// <param name="R">The red component, exact for RGB colors and approximate otherwise.</param>
/// <param name="G">The green component.</param>
/// <param name="B">The blue component.</param>
public readonly record struct TerminalColor(TerminalColorKind Kind, byte Index, byte R, byte G, byte B)
{
    /// <summary>
    /// The terminal's default color.
    /// </summary>
    public static TerminalColor Default { get; } = new(TerminalColorKind.Default, 0, 0, 0, 0);

    /// <summary>
    /// A palette color by its 256-color index, encoded as a standard or bright color when it is one of the first sixteen.
    /// </summary>
    /// <param name="index">The index.</param>
    /// <returns>The color.</returns>
    public static TerminalColor FromPalette(int index)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(index);
        ArgumentOutOfRangeException.ThrowIfGreaterThan(index, 255);
        var (r, g, b) = ColorTables.Palette[index];
        return index switch
        {
            < 8 => new TerminalColor(TerminalColorKind.Standard, (byte)index, r, g, b),
            < 16 => new TerminalColor(TerminalColorKind.Bright, (byte)(index - 8), r, g, b),
            _ => new TerminalColor(TerminalColorKind.Indexed, (byte)index, r, g, b),
        };
    }

    /// <summary>
    /// A 24-bit color.
    /// </summary>
    /// <param name="r">The red component.</param>
    /// <param name="g">The green component.</param>
    /// <param name="b">The blue component.</param>
    /// <returns>The color.</returns>
    public static TerminalColor FromRgb(byte r, byte g, byte b) => new(TerminalColorKind.Rgb, 0, r, g, b);

    /// <summary>
    /// The SGR parameters that select this color.
    /// </summary>
    /// <param name="background">True for the background.</param>
    /// <returns>The parameters, such as <c>31</c>, <c>38;5;208</c>, or <c>48;2;26;26;26</c>.</returns>
    public string ToSgr(bool background) => Kind switch
    {
        TerminalColorKind.Default => background ? "49" : "39",
        TerminalColorKind.Standard => ((background ? 40 : 30) + Index).ToString(CultureInfo.InvariantCulture),
        TerminalColorKind.Bright => ((background ? 100 : 90) + Index).ToString(CultureInfo.InvariantCulture),
        TerminalColorKind.Indexed => $"{(background ? 48 : 38)};5;{Index}",
        _ => $"{(background ? 48 : 38)};2;{R};{G};{B}",
    };
}
