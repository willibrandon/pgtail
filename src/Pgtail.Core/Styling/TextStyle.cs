namespace Pgtail.Styling;

/// <summary>
/// Colors and attributes for a run of text.
/// </summary>
/// <param name="Foreground">The foreground color, or null to inherit.</param>
/// <param name="Background">The background color, or null to inherit.</param>
/// <param name="Attributes">The attributes set.</param>
/// <param name="Cleared">Attributes explicitly turned off, as with <c>not bold</c>, which win over inherited ones.</param>
public readonly record struct TextStyle(
    TerminalColor? Foreground = null,
    TerminalColor? Background = null,
    TextAttributes Attributes = TextAttributes.None,
    TextAttributes Cleared = TextAttributes.None)
{
    /// <summary>
    /// The style that changes nothing.
    /// </summary>
    public static TextStyle Plain { get; } = new();

    /// <summary>
    /// Whether the style changes nothing.
    /// </summary>
    public bool IsPlain => Foreground is null && Background is null && Attributes == TextAttributes.None
        && Cleared == TextAttributes.None;

    /// <summary>
    /// A bold style.
    /// </summary>
    /// <returns>The style with bold added.</returns>
    public TextStyle WithBold() => this with { Attributes = Attributes | TextAttributes.Bold };

    /// <summary>
    /// Applies another style on top of this one.
    /// </summary>
    /// <remarks>
    /// Its colors replace these where it sets them, and its attributes add to these.
    /// </remarks>
    /// <param name="over">The style on top.</param>
    /// <returns>The combined style.</returns>
    public TextStyle Then(TextStyle over) => new(
        over.Foreground ?? Foreground,
        over.Background ?? Background,
        (Attributes & ~over.Cleared) | over.Attributes,
        (Cleared & ~over.Attributes) | over.Cleared);
}
