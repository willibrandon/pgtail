namespace Pgtail.Editing;

/// <summary>
/// A line of text and its caret, for an input that draws itself.
/// </summary>
internal sealed class TextLine : IEditableLine
{
    private int _caret;

    /// <inheritdoc/>
    public string Text { get; private set; } = "";

    /// <inheritdoc/>
    public int Caret
    {
        get => _caret;
        set => _caret = Math.Clamp(value, 0, Text.Length);
    }

    /// <inheritdoc/>
    public void Replace(int start, int end, string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        Text = string.Concat(Text.AsSpan(0, start), text, Text.AsSpan(end));
        _caret = start + text.Length;
    }
}
