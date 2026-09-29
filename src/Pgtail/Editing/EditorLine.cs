using Hex1b.Documents;
using Hex1b.Widgets;

namespace Pgtail.Editing;

/// <summary>
/// The line of a one-line Hex1b editor, as the REPL prompt uses.
/// </summary>
/// <param name="editor">The editor's state.</param>
internal sealed class EditorLine(EditorState editor) : IEditableLine
{
    /// <inheritdoc/>
    public string Text => editor.Document.GetText();

    /// <inheritdoc/>
    public int Caret
    {
        get => Math.Clamp(editor.Cursor.Position.Value, 0, Text.Length);
        set => editor.SetCursorPosition(new DocumentOffset(value));
    }

    /// <inheritdoc/>
    public void Replace(int start, int end, string text)
    {
        _ = editor.Document.Apply(new ReplaceOperation(new DocumentRange(new DocumentOffset(start), new DocumentOffset(end)), text));
        editor.SetCursorPosition(new DocumentOffset(start + text.Length));
    }
}
