namespace Pgtail.Styling;

/// <summary>
/// A run of text in one style.
/// </summary>
/// <param name="Text">The text.</param>
/// <param name="Style">The style.</param>
public readonly record struct StyledSpan(string Text, TextStyle Style);
