using Hex1b.Documents;
using Hex1b.Widgets;
using Pgtail.Commands;

namespace Pgtail.Repl;

/// <summary>
/// The REPL prompt's editable line, history position, and completion menu.
/// </summary>
/// <param name="history">The command history.</param>
internal sealed class PromptState(ReplHistory history)
{
    /// <summary>
    /// The number of completions shown at once.
    /// </summary>
    public const int MenuRows = 8;

    /// <summary>
    /// The editor holding the line.
    /// </summary>
    public EditorState Editor { get; } = new(new Hex1bDocument(""));

    /// <summary>
    /// The command history.
    /// </summary>
    public ReplHistory History { get; } = history;

    /// <summary>
    /// The line being edited.
    /// </summary>
    public string Text => Editor.Document.GetText();

    /// <summary>
    /// The caret's offset in the line.
    /// </summary>
    public int Caret => Editor.Cursor.Position.Value;

    /// <summary>
    /// The completions offered for the word being typed.
    /// </summary>
    public List<CompletionItem> Candidates { get; private set; } = [];

    /// <summary>
    /// Where the word being completed starts.
    /// </summary>
    public int CompletionStart { get; private set; }

    /// <summary>
    /// The chosen completion, or -1 before one is chosen.
    /// </summary>
    public int Selected { get; private set; } = -1;

    /// <summary>
    /// The first completion shown, for scrolling a long menu.
    /// </summary>
    public int MenuTop { get; private set; }

    /// <summary>
    /// Whether the completion menu is showing.
    /// </summary>
    public bool MenuVisible => Candidates.Count > 0;

    /// <summary>
    /// The document version last seen, to tell typing from programmatic changes.
    /// </summary>
    public long SeenVersion { get; set; }

    /// <summary>
    /// Replaces the whole line and puts the caret at its end, forgetting undo history.
    /// </summary>
    /// <param name="text">The new line.</param>
    public void SetText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var document = Editor.Document;
        Editor.Cursor.ClearSelection();
        _ = document.Apply(new ReplaceOperation(new DocumentRange(DocumentOffset.Zero, new DocumentOffset(document.Length)), text));
        Editor.History.Clear();
        Editor.SetCursorPosition(new DocumentOffset(document.Length));
        SeenVersion = document.Version;
    }

    /// <summary>
    /// Replaces part of the line as one undoable edit and puts the caret after the new text.
    /// </summary>
    /// <param name="start">The first offset replaced.</param>
    /// <param name="end">The offset just past the replaced text.</param>
    /// <param name="replacement">The new text.</param>
    public void Replace(int start, int end, string replacement)
    {
        var document = Editor.Document;
        var range = new DocumentRange(new DocumentOffset(start), new DocumentOffset(end));
        var operation = new ReplaceOperation(range, replacement);
        var inverse = new ReplaceOperation(
            new DocumentRange(range.Start, new DocumentOffset(start + replacement.Length)), document.GetText(range));
        var before = document.Version;
        Editor.History.BeginGroup(Editor.Cursors, before);
        _ = document.Apply(operation, "prompt");
        Editor.History.RecordEdit(operation, inverse, Editor.Cursors, before, document.Version);
        Editor.SetCursorPosition(new DocumentOffset(start + replacement.Length));
        Editor.History.CommitGroup(Editor.Cursors, document.Version);
        SeenVersion = document.Version;
    }

    /// <summary>
    /// Shows completions for the word starting at an offset.
    /// </summary>
    /// <param name="start">Where the word starts.</param>
    /// <param name="candidates">The completions.</param>
    public void ShowCompletions(int start, List<CompletionItem> candidates)
    {
        ArgumentNullException.ThrowIfNull(candidates);
        CompletionStart = start;
        Candidates = candidates;
        Selected = -1;
        MenuTop = 0;
    }

    /// <summary>
    /// Hides the completion menu.
    /// </summary>
    public void HideCompletions()
    {
        Candidates = [];
        Selected = -1;
        MenuTop = 0;
    }

    /// <summary>
    /// Chooses the next or previous completion and puts it in the line in place of the word.
    /// </summary>
    /// <param name="delta">One for the next completion, minus one for the previous.</param>
    public void MoveSelection(int delta)
    {
        if (Candidates.Count == 0)
        {
            return;
        }

        var count = Candidates.Count;
        Selected = Selected < 0 ? (delta > 0 ? 0 : count - 1) : (Selected + delta + count) % count;
        if (Selected < MenuTop)
        {
            MenuTop = Selected;
        }
        else if (Selected >= MenuTop + MenuRows)
        {
            MenuTop = Selected - MenuRows + 1;
        }

        Replace(CompletionStart, WordEnd(), Candidates[Selected].Text);
    }

    /// <summary>
    /// Inserts a lone completion and a space after it unless it continues, then hides the menu.
    /// </summary>
    /// <param name="item">The completion.</param>
    public void Accept(CompletionItem item)
    {
        ArgumentNullException.ThrowIfNull(item);
        Replace(CompletionStart, WordEnd(), item.Continues ? item.Text : item.Text + " ");
        HideCompletions();
    }

    /// <summary>
    /// Clears the line and the menu.
    /// </summary>
    public void Reset()
    {
        SetText("");
        HideCompletions();
        History.ResetNavigation();
    }

    private int WordEnd()
    {
        var text = Text;
        var end = CompletionStart;
        while (end < text.Length && !char.IsWhiteSpace(text[end]))
        {
            end++;
        }

        return Math.Max(end, Math.Min(Caret, text.Length));
    }
}
