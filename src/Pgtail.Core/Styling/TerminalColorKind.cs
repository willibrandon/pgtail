namespace Pgtail.Styling;

/// <summary>
/// How a color is encoded for the terminal.
/// </summary>
public enum TerminalColorKind
{
    /// <summary>
    /// The terminal's own default color.
    /// </summary>
    Default,

    /// <summary>
    /// One of the eight standard palette colors (SGR 30-37).
    /// </summary>
    Standard,

    /// <summary>
    /// One of the eight bright palette colors (SGR 90-97).
    /// </summary>
    Bright,

    /// <summary>
    /// One of the 256 palette colors (SGR 38;5;N).
    /// </summary>
    Indexed,

    /// <summary>
    /// A 24-bit color (SGR 38;2;R;G;B).
    /// </summary>
    Rgb,
}
