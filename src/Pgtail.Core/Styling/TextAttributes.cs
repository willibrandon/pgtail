namespace Pgtail.Styling;

/// <summary>
/// Text attributes a style may set.
/// </summary>
[Flags]
public enum TextAttributes
{
    /// <summary>
    /// No attributes.
    /// </summary>
    None = 0,

    /// <summary>
    /// Bold or increased intensity.
    /// </summary>
    Bold = 1,

    /// <summary>
    /// Dim or decreased intensity.
    /// </summary>
    Dim = 2,

    /// <summary>
    /// Italic.
    /// </summary>
    Italic = 4,

    /// <summary>
    /// Underlined.
    /// </summary>
    Underline = 8,

    /// <summary>
    /// Blinking.
    /// </summary>
    Blink = 16,

    /// <summary>
    /// Foreground and background swapped.
    /// </summary>
    Reverse = 32,

    /// <summary>
    /// Struck through.
    /// </summary>
    Strikethrough = 64,

    /// <summary>
    /// Hidden.
    /// </summary>
    Hidden = 128,

    /// <summary>
    /// Overlined.
    /// </summary>
    Overline = 256,
}
