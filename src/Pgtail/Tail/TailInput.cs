using Hex1b.Documents;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Editing;

namespace Pgtail.Tail;

/// <summary>
/// The <c>tail&gt;</c> command input: editing, history, and grey suggestions.
/// </summary>
/// <remarks>
/// Right or End at the end of the line accepts the suggestion, Up and Down walk the history, Enter runs the command and
/// keeps the input for the next one, Page Up and Page Down scroll the command output or else the log, Escape closes the
/// command output or else clears the line and moves to the log, and <c>q</c> on an empty line leaves tail mode.
/// </remarks>
internal sealed class TailInput
{
    private readonly TailScreen _screen;
    private readonly TailHistory _history;
    private readonly TailSuggester _suggester;
    private long _seenVersion;
    private string? _suffix;
    private bool _programmatic;
    private LineEditingKeys? _lineKeys;

    /// <summary>
    /// Creates the input for a screen.
    /// </summary>
    /// <param name="screen">The tail screen.</param>
    /// <param name="history">The command history.</param>
    public TailInput(TailScreen screen, TailHistory history)
    {
        _screen = screen;
        _history = history;
        _suggester = new TailSuggester(Commands.TailCatalog.Catalog, screen, history);
    }

    /// <summary>
    /// The editor holding the line.
    /// </summary>
    public EditorState Editor { get; } = new(new Hex1bDocument(""));

    /// <summary>
    /// The suggestion hints.
    /// </summary>
    public TailInputHints Hints { get; } = new();

    /// <summary>
    /// The line being typed.
    /// </summary>
    public string Text => Editor.Document.GetText();

    /// <summary>
    /// Called from a key's action to move focus to the log at once.
    /// </summary>
    public Action<InputBindingActionContext>? FocusLog { get; set; }

    /// <summary>
    /// Loads the history.
    /// </summary>
    public void Load() => _history.Load();

    /// <summary>
    /// Updates the suggestion for the current line; called on every frame.
    /// </summary>
    public void UpdateHints()
    {
        var version = Editor.Document.Version;
        if (version != _seenVersion)
        {
            _seenVersion = version;
            _suffix = _suggester.Suffix(Text);
            if (!_programmatic)
            {
                _history.ResetNavigation();
            }

            _programmatic = false;
        }

        var text = Text;
        Hints.Show(text.Length, Editor.Cursor.Position.Value == text.Length ? _suffix : null);
    }

    /// <summary>
    /// Inserts typed text at the caret, as when keys typed on the log belong to a command.
    /// </summary>
    /// <param name="text">The text.</param>
    public void Type(string text) => Editor.InsertText(text);

    /// <summary>
    /// Adds the input's keys to the editor's bindings.
    /// </summary>
    /// <param name="bindings">The editor's bindings.</param>
    public void Bind(InputBindingsBuilder bindings)
    {
        ArgumentNullException.ThrowIfNull(bindings);
        bindings.Remove(EditorWidget.InsertNewline);
        bindings.Remove(EditorWidget.InsertTab);
        bindings.Remove(EditorWidget.MoveUp);
        bindings.Remove(EditorWidget.MoveDown);
        bindings.Remove(EditorWidget.AddCursorAtNextMatch);
        bindings.Remove(Hex1bKey.Escape);
        _lineKeys ??= new LineEditingKeys(Editor);
        _lineKeys.Bind(bindings);
        bindings.Key(Hex1bKey.Enter).Action(_ => SubmitAsync(), "Run the command");
        bindings.Key(Hex1bKey.Escape).Action(context =>
        {
            if (_screen.ResultVisible)
            {
                _screen.CloseResult();
                return;
            }

            SetText("");
            FocusLog?.Invoke(context);
        }, "Close the command output, or clear and return to the log");

        bindings.Key(Hex1bKey.PageUp).Action(_ => _screen.Scroll(-1), "Scroll the command output or the log up");
        bindings.Key(Hex1bKey.PageDown).Action(_ => _screen.Scroll(1), "Scroll the command output or the log down");

        bindings.Key(Hex1bKey.UpArrow).Action(_ =>
        {
            if (_history.Back(Text) is { } entry)
            {
                SetText(entry);
            }
        }, "Previous command");

        bindings.Key(Hex1bKey.DownArrow).Action(_ =>
        {
            if (_history.Forward() is { } entry)
            {
                SetText(entry);
            }
        }, "Next command");

        if (_suffix is { Length: > 0 } && Editor.Cursor.Position.Value == Text.Length)
        {
            bindings.Remove(EditorWidget.MoveRight);
            bindings.Remove(EditorWidget.MoveToLineEnd);
            bindings.Key(Hex1bKey.RightArrow).Action(_ => Accept(), "Accept the suggestion");
            bindings.Key(Hex1bKey.End).Action(_ => Accept(), "Accept the suggestion");
        }

        if (Text.Length == 0)
        {
            bindings.Key(Hex1bKey.Q).Action(_ => _screen.Stop(), "Leave tail mode");
        }
    }

    /// <summary>
    /// Replaces the line and puts the caret at its end.
    /// </summary>
    /// <param name="text">The new line.</param>
    public void SetText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var document = Editor.Document;
        _programmatic = true;
        _ = document.Apply(new ReplaceOperation(new DocumentRange(DocumentOffset.Zero, new DocumentOffset(document.Length)), text));
        Editor.History.Clear();
        Editor.SetCursorPosition(new DocumentOffset(document.Length));
    }

    private void Accept()
    {
        if (_suffix is { Length: > 0 } suffix)
        {
            Editor.SetCursorPosition(new DocumentOffset(Editor.Document.Length));
            Editor.InsertText(suffix);
            _history.ResetNavigation();
        }
    }

    private async Task SubmitAsync()
    {
        var text = Text;
        SetText("");
        _history.ResetNavigation();
        await _screen.RunCommandAsync(text);
    }
}
