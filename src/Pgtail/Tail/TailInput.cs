using Hex1b;
using Hex1b.Input;
using Hex1b.Nodes;
using Hex1b.Surfaces;
using Hex1b.Theming;
using Hex1b.Widgets;
using Pgtail.Display;
using Pgtail.Editing;

namespace Pgtail.Tail;

/// <summary>
/// The <c>tail&gt;</c> command input: editing, history, and grey suggestions.
/// </summary>
/// <remarks>
/// The input draws itself, with a block cursor that blinks while it has focus and stays solid when the log has it. The
/// rest of a command the input suggests follows the text in grey, its first character under the cursor, and is worked
/// out as each frame is built so it always belongs to the line on screen; Right, or End at the end of the line, accepts
/// it. Up and Down walk the history, Enter runs the command, whose output goes into the log, and keeps the input for the
/// next one, Page Up and Page Down scroll the log, and Escape clears the line and moves to the log. Every character typed
/// is text, <c>q</c> included; the <c>q</c> command leaves tail mode once Enter runs it.
/// </remarks>
internal sealed class TailInput
{
    /// <summary>
    /// The prompt in front of the line.
    /// </summary>
    public const string Prompt = PromptLabels.Tail;

    /// <summary>
    /// How long the cursor stays on, and then off, while it blinks.
    /// </summary>
    public static readonly TimeSpan BlinkInterval = TimeSpan.FromMilliseconds(530);

    private static readonly Hex1bColor s_suggestionColor = Hex1bColor.FromRgb(128, 128, 128);
    private readonly TailScreen _screen;
    private readonly TailHistory _history;
    private readonly TextLine _line = new();
    private readonly LineEditingKeys _lineKeys;
    private readonly TailSuggester _suggester;
    private (string Text, string? Suffix) _suggested = ("", null);
    private long _lastInput = Environment.TickCount64;
    private int _scroll;

    /// <summary>
    /// Creates the input for a screen.
    /// </summary>
    /// <param name="screen">The tail screen.</param>
    /// <param name="history">The command history.</param>
    public TailInput(TailScreen screen, TailHistory history)
    {
        _screen = screen;
        _history = history;
        _lineKeys = new LineEditingKeys(_line, Edited);
        _suggester = new TailSuggester(Commands.TailCatalog.Catalog, screen, history);
    }

    /// <summary>
    /// The line being typed.
    /// </summary>
    public string Text => _line.Text;

    /// <summary>
    /// Called from a key's action to move focus to the log at once.
    /// </summary>
    public Action<InputBindingActionContext>? FocusLog { get; set; }

    /// <summary>
    /// The rest of the command the input suggests, when the caret is at the end of the line.
    /// </summary>
    public string? Suggestion => _line.Caret == _line.Text.Length ? Suffix(_line.Text) : null;

    /// <summary>
    /// Which half of its blink the cursor is in; a frame is due whenever this changes.
    /// </summary>
    public long BlinkPhase => (Environment.TickCount64 - _lastInput) / (long)BlinkInterval.TotalMilliseconds;

    /// <summary>
    /// Whether a node is the input.
    /// </summary>
    /// <remarks>
    /// The input and the log are both drawn on a surface in an interactable; the input's surface sits in a row of its own.
    /// </remarks>
    /// <param name="node">The node.</param>
    /// <returns>True for the input.</returns>
    public static bool Is(Hex1bNode node) => node is InteractableNode { Child: HStackNode };

    /// <summary>
    /// Loads the history.
    /// </summary>
    public void Load() => _history.Load();

    /// <summary>
    /// Builds the input.
    /// </summary>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="more">Adds the screen's keys.</param>
    /// <param name="color">Whether colors are on.</param>
    /// <returns>The input.</returns>
    public InteractableWidget Build<TParent>(WidgetContext<TParent> context, Action<InputBindingsBuilder> more, bool color)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(more);
        return context.Interactable(i => i.HStack(h =>
            [
                h.Surface(s => [s.Layer(surface => Draw(surface, i.IsFocused, color))]).Fill(),
            ]))
            .InputBindings(bindings =>
            {
                Bind(bindings);
                more(bindings);
            });
    }

    /// <summary>
    /// Inserts typed text at the caret, as when keys typed on the log belong to a command or text is pasted.
    /// </summary>
    /// <param name="text">The text; line breaks become spaces.</param>
    public void Type(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        _line.Replace(_line.Caret, _line.Caret, text.ReplaceLineEndings(" "));
        Edited();
    }

    /// <summary>
    /// Replaces the line and puts the caret at its end.
    /// </summary>
    /// <param name="text">The new line.</param>
    public void SetText(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        _line.Replace(0, _line.Text.Length, text);
        _lastInput = Environment.TickCount64;
    }

    // The prompt, the part of the line that fits, the suggestion, and the cursor, which blinks while the input has focus.
    private void Draw(Surface surface, bool focused, bool color)
    {
        string text = _line.Text;
        int start = Prompt.Length;
        int room = Math.Max(1, surface.Width - start - 1);
        int caretColumn = GraphemeHelper.IndexToDisplayColumn(text, _line.Caret);
        _scroll = Math.Clamp(_scroll, Math.Max(0, caretColumn - room), caretColumn);
        _ = surface.WriteText(0, 0, Prompt);
        int written = surface.WriteText(start, 0, text[GraphemeHelper.DisplayColumnToIndex(text, _scroll)..]);
        if (Suggestion is { } suggestion)
        {
            _ = surface.WriteText(start + written, 0, suggestion, color ? s_suggestionColor : null, null);
        }

        int x = start + caretColumn - _scroll;
        if ((!focused || BlinkPhase % 2 == 0) && x < surface.Width)
        {
            // Under the cursor, a suggested character is drawn like typed text, so the block looks the same everywhere.
            SurfaceCell cell = surface[x, 0];
            if (cell == SurfaceCells.Empty || _line.Caret == text.Length)
            {
                cell = SurfaceCells.Empty with { Character = cell == SurfaceCells.Empty ? " " : cell.Character };
            }

            surface[x, 0] = cell.WithAttributes(cell.Attributes ^ CellAttributes.Reverse);
        }
    }

    private void Bind(InputBindingsBuilder bindings)
    {
        _lineKeys.Bind(bindings);
        bindings.Character(text => !text.Any(char.IsControl)).Action((text, _) =>
        {
            Type(text);
            return Task.CompletedTask;
        }, "Type text");

        bindings.Key(Hex1bKey.Backspace).Action(_ => Delete(GraphemeHelper.GetPreviousClusterBoundary(Text, _line.Caret), _line.Caret),
            "Delete the character before the cursor");
        bindings.Key(Hex1bKey.Delete).Action(_ => Delete(_line.Caret, GraphemeHelper.GetNextClusterBoundary(Text, _line.Caret)),
            "Delete the character under the cursor");
        bindings.Key(Hex1bKey.LeftArrow).Action(_ => Move(GraphemeHelper.GetPreviousClusterBoundary(Text, _line.Caret)), "Left");
        bindings.Key(Hex1bKey.Home).Action(_ => Move(0), "Start of the line");
        bindings.Key(Hex1bKey.RightArrow).Action(_ => AcceptOr(() => Move(GraphemeHelper.GetNextClusterBoundary(Text, _line.Caret))),
            "Right, or accept the suggestion");
        bindings.Key(Hex1bKey.End).Action(_ => AcceptOr(() => Move(Text.Length)), "End of the line, or accept the suggestion");
        bindings.Key(Hex1bKey.Enter).Action(_ => SubmitAsync(), "Run the command");
        bindings.Key(Hex1bKey.Escape).Action(context =>
        {
            SetText("");
            FocusLog?.Invoke(context);
        }, "Clear and return to the log");

        bindings.Key(Hex1bKey.PageUp).Action(_ => _screen.Scroll(-1), "Scroll the log up");
        bindings.Key(Hex1bKey.PageDown).Action(_ => _screen.Scroll(1), "Scroll the log down");
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

        bindings.Mouse(MouseButton.Left).Action(context =>
        {
            _ = context.FocusWhere(Is);
            Move(GraphemeHelper.DisplayColumnToIndex(Text, Math.Max(0, context.MouseX - Prompt.Length + _scroll)));
        }, "Put the cursor where clicked");
    }

    private void Delete(int start, int end)
    {
        if (end > start)
        {
            _line.Replace(start, end, "");
            Edited();
        }
    }

    private void Move(int caret)
    {
        _line.Caret = caret;
        _lastInput = Environment.TickCount64;
    }

    private void AcceptOr(Action otherwise)
    {
        if (Suggestion is { } suggestion)
        {
            _line.Replace(Text.Length, Text.Length, suggestion);
            Edited();
            return;
        }

        otherwise();
    }

    // Keeps the cursor on while typing and starts history navigation over.
    private void Edited()
    {
        _lastInput = Environment.TickCount64;
        _history.ResetNavigation();
    }

    private async Task SubmitAsync()
    {
        string text = Text;
        SetText("");
        _history.ResetNavigation();
        await _screen.RunCommandAsync(text);
    }

    // The suggester runs once for each line typed.
    private string? Suffix(string text)
    {
        if (_suggested.Text != text)
        {
            _suggested = (text, _suggester.Suffix(text));
        }

        return _suggested.Suffix;
    }
}
