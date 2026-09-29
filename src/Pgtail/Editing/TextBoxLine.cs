using Hex1b.Widgets;

namespace Pgtail.Editing;

/// <summary>
/// The line of a Hex1b text box, as tail mode's command input uses.
/// </summary>
/// <param name="state">The text box's state.</param>
internal sealed class TextBoxLine(TextBoxState state) : IEditableLine
{
    /// <inheritdoc/>
    public string Text => state.Text;

    /// <inheritdoc/>
    public int Caret
    {
        get => state.CursorPosition;
        set
        {
            state.ClearSelection();
            state.CursorPosition = value;
        }
    }

    /// <inheritdoc/>
    public void Replace(int start, int end, string text)
    {
        state.ClearSelection();
        state.Text = string.Concat(state.Text.AsSpan(0, start), text, state.Text.AsSpan(end));
        state.CursorPosition = start + text.Length;
    }
}
