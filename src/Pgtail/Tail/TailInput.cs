using Hex1b;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Editing;

namespace Pgtail.Tail;

/// <summary>
/// The <c>tail&gt;</c> command input: editing, history, and grey suggestions.
/// </summary>
/// <remarks>
/// The terminal's own cursor marks the caret, and the rest of a command the input suggests follows it in grey; Right, or
/// End at the end of the line, accepts it. Up and Down walk the history, Enter runs the command and keeps the input for
/// the next one, Page Up and Page Down scroll the command output or else the log, and Escape closes the command output
/// or else clears the line and moves to the log. Every character typed is text, <c>q</c> included; the <c>q</c> command
/// leaves tail mode once Enter runs it.
/// </remarks>
internal sealed class TailInput
{
    private readonly TailScreen _screen;
    private readonly TailHistory _history;
    private readonly TextBoxLine _line;
    private readonly LineEditingKeys _lineKeys;
    private readonly Func<string, CancellationToken, Task<string?>> _suggest;
    private bool _dropSuggestion;

    /// <summary>
    /// Creates the input for a screen.
    /// </summary>
    /// <param name="screen">The tail screen.</param>
    /// <param name="history">The command history.</param>
    public TailInput(TailScreen screen, TailHistory history)
    {
        _screen = screen;
        _history = history;
        _line = new TextBoxLine(State);
        _lineKeys = new LineEditingKeys(_line, history.ResetNavigation);
        var suggester = new TailSuggester(Commands.TailCatalog.Catalog, screen, history);
        _suggest = (text, _) => Task.FromResult(suggester.Suffix(text));
    }

    /// <summary>
    /// The text box's state, holding the line and the caret.
    /// </summary>
    public TextBoxState State { get; } = new();

    /// <summary>
    /// The line being typed.
    /// </summary>
    public string Text => State.Text;

    /// <summary>
    /// Called from a key's action to move focus to the log at once.
    /// </summary>
    public Action<InputBindingActionContext>? FocusLog { get; set; }

    /// <summary>
    /// Loads the history.
    /// </summary>
    public void Load() => _history.Load();

    /// <summary>
    /// Builds the text box.
    /// </summary>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="more">Adds the screen's keys.</param>
    /// <returns>The text box.</returns>
    public TextBoxWidget Build<TParent>(WidgetContext<TParent> context, Action<InputBindingsBuilder> more)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(more);
        var box = context.TextBox()
            .FillWidth()
            .State(State)
            .OnTextChanged(_ => _history.ResetNavigation())
            .InputBindings(bindings =>
            {
                Bind(bindings);
                more(bindings);
            });

        // A line replaced from outside, as by the history or a command that ran, drops the suggestion made for the old
        // one: a frame without a suggester clears it.
        if (_dropSuggestion)
        {
            _dropSuggestion = false;
            return box;
        }

        return box.Predict(_suggest);
    }

    /// <summary>
    /// Inserts typed text at the caret, as when keys typed on the log belong to a command.
    /// </summary>
    /// <param name="text">The text.</param>
    public void Type(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        _line.Replace(_line.Caret, _line.Caret, text);
        _history.ResetNavigation();
    }

    /// <summary>
    /// Replaces the line and puts the caret at its end.
    /// </summary>
    /// <param name="text">The new line.</param>
    public void SetText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        _line.Replace(0, _line.Text.Length, text);
        _dropSuggestion = true;
    }

    private void Bind(InputBindingsBuilder bindings)
    {
        bindings.Remove(Hex1bKey.Escape);
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

        // At the end of the line, End accepts the suggestion as Right does; with none there is nowhere to move.
        if (State.CursorPosition == State.Text.Length)
        {
            bindings.Remove(TextBoxWidget.MoveEnd);
            bindings.Key(Hex1bKey.End).Triggers(TextBoxWidget.MoveRight);
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
