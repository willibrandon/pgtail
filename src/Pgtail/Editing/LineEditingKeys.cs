using Hex1b.Documents;
using Hex1b.Input;
using Hex1b.Widgets;

namespace Pgtail.Editing;

/// <summary>
/// The line editing keys of a shell prompt, for the REPL prompt and tail mode's command input.
/// </summary>
/// <remarks>
/// These are the keys prompt_toolkit and readline give a prompt: Ctrl+A and Ctrl+E move to the start and end, Ctrl+B and
/// Ctrl+F by a character, Alt+B and Alt+F by a word, Ctrl+K and Ctrl+U cut to the end and start of the line, Ctrl+W
/// cuts the word before the caret, Alt+D the word after it, and Ctrl+Y pastes the last cut text.
/// </remarks>
/// <param name="editor">The line's editor.</param>
/// <param name="changed">Called after a key changes the line, for an owner that does not watch the document's version.</param>
internal sealed class LineEditingKeys(EditorState editor, Action? changed = null)
{
    private string _cut = "";

    /// <summary>
    /// Adds the keys, replacing the editor's own for Ctrl+A (select all), Ctrl+K (hover), and Ctrl+Y (redo).
    /// </summary>
    /// <param name="bindings">The editor's bindings.</param>
    public void Bind(InputBindingsBuilder bindings)
    {
        ArgumentNullException.ThrowIfNull(bindings);
        foreach (var key in new[] { Hex1bKey.A, Hex1bKey.E, Hex1bKey.B, Hex1bKey.F, Hex1bKey.K, Hex1bKey.U, Hex1bKey.W, Hex1bKey.Y })
        {
            bindings.Remove(key, Hex1bModifiers.Control);
        }

        bindings.Remove(Hex1bKey.B, Hex1bModifiers.Alt);
        bindings.Remove(Hex1bKey.F, Hex1bModifiers.Alt);
        bindings.Remove(Hex1bKey.D, Hex1bModifiers.Alt);
        bindings.Ctrl().Key(Hex1bKey.A).Triggers(EditorWidget.MoveToLineStart);
        bindings.Ctrl().Key(Hex1bKey.E).Triggers(EditorWidget.MoveToLineEnd);
        bindings.Ctrl().Key(Hex1bKey.B).Triggers(EditorWidget.MoveLeft);
        bindings.Ctrl().Key(Hex1bKey.F).Triggers(EditorWidget.MoveRight);
        bindings.Alt().Key(Hex1bKey.B).Triggers(EditorWidget.MoveWordLeft);
        bindings.Alt().Key(Hex1bKey.F).Triggers(EditorWidget.MoveWordRight);
        bindings.Ctrl().Key(Hex1bKey.K).Action(_ => Cut(Caret, Text.Length), "Cut to the end of the line");
        bindings.Ctrl().Key(Hex1bKey.U).Action(_ => Cut(0, Caret), "Cut to the start of the line");
        bindings.Ctrl().Key(Hex1bKey.W).Action(_ => Cut(WordStartBefore(Caret), Caret), "Cut the word before the caret");
        bindings.Alt().Key(Hex1bKey.D).Action(_ => Cut(Caret, WordEndAfter(Caret)), "Cut the word after the caret");
        bindings.Ctrl().Key(Hex1bKey.Y).Action(_ => Paste(), "Paste the last cut text");
    }

    private string Text => editor.Document.GetText();

    private int Caret => Math.Clamp(editor.Cursor.Position.Value, 0, Text.Length);

    private void Cut(int start, int end)
    {
        if (end <= start)
        {
            return;
        }

        _cut = Text[start..end];
        _ = editor.Document.Apply(new ReplaceOperation(new DocumentRange(new DocumentOffset(start), new DocumentOffset(end)), ""));
        editor.SetCursorPosition(new DocumentOffset(start));
        changed?.Invoke();
    }

    private void Paste()
    {
        if (_cut.Length > 0)
        {
            editor.InsertText(_cut);
            changed?.Invoke();
        }
    }

    // As readline's Ctrl+W: back over spaces, then over the word before them.
    private int WordStartBefore(int caret)
    {
        var text = Text;
        var start = caret;
        while (start > 0 && char.IsWhiteSpace(text[start - 1]))
        {
            start--;
        }

        while (start > 0 && !char.IsWhiteSpace(text[start - 1]))
        {
            start--;
        }

        return start;
    }

    private int WordEndAfter(int caret)
    {
        var text = Text;
        var end = caret;
        while (end < text.Length && !char.IsLetterOrDigit(text[end]))
        {
            end++;
        }

        while (end < text.Length && char.IsLetterOrDigit(text[end]))
        {
            end++;
        }

        return end;
    }
}
