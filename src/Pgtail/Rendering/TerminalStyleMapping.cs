using Hex1b;
using Hex1b.Theming;
using Pgtail.Styling;

namespace Pgtail.Rendering;

/// <summary>
/// Converts pgtail's terminal colors and attributes to Hex1b's.
/// </summary>
internal static class TerminalStyleMapping
{
    /// <summary>
    /// The Hex1b color with the same palette encoding.
    /// </summary>
    /// <param name="color">The color.</param>
    /// <returns>The Hex1b color.</returns>
    public static Hex1bColor ToHex1b(this TerminalColor color) => color.Kind switch
    {
        TerminalColorKind.Default => Hex1bColor.Default,
        TerminalColorKind.Standard => Hex1bColor.FromStandard(color.Index, color.R, color.G, color.B),
        TerminalColorKind.Bright => Hex1bColor.FromBright(color.Index, color.R, color.G, color.B),
        TerminalColorKind.Indexed => Hex1bColor.FromIndexed(color.Index, color.R, color.G, color.B),
        _ => Hex1bColor.FromRgb(color.R, color.G, color.B),
    };

    /// <summary>
    /// The cell attributes for a set of text attributes.
    /// </summary>
    /// <param name="attributes">The attributes.</param>
    /// <returns>The cell attributes.</returns>
    public static CellAttributes ToCellAttributes(this TextAttributes attributes)
    {
        var result = CellAttributes.None;
        if (attributes.HasFlag(TextAttributes.Bold))
        {
            result |= CellAttributes.Bold;
        }

        if (attributes.HasFlag(TextAttributes.Dim))
        {
            result |= CellAttributes.Dim;
        }

        if (attributes.HasFlag(TextAttributes.Italic))
        {
            result |= CellAttributes.Italic;
        }

        if (attributes.HasFlag(TextAttributes.Underline))
        {
            result |= CellAttributes.Underline;
        }

        if (attributes.HasFlag(TextAttributes.Blink))
        {
            result |= CellAttributes.Blink;
        }

        if (attributes.HasFlag(TextAttributes.Reverse))
        {
            result |= CellAttributes.Reverse;
        }

        if (attributes.HasFlag(TextAttributes.Strikethrough))
        {
            result |= CellAttributes.Strikethrough;
        }

        if (attributes.HasFlag(TextAttributes.Hidden))
        {
            result |= CellAttributes.Hidden;
        }

        if (attributes.HasFlag(TextAttributes.Overline))
        {
            result |= CellAttributes.Overline;
        }

        return result;
    }
}
