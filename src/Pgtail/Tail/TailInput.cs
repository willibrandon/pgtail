using Hex1b;
using Hex1b.Input;
using Hex1b.Theming;
using Hex1b.Widgets;
using Pgtail.Editing;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The <c>tail&gt;</c> command input: editing, history, and grey suggestions.
/// </summary>
/// <remarks>
/// The terminal's own cursor marks the caret, and the rest of a command the input suggests follows it in grey, worked
/// out as each frame is built so it always belongs to the line on screen; Right, or End at the end of the line, accepts
/// it. Up and Down walk the history, Enter runs the command and keeps the input for
/// the next one, Page Up and Page Down scroll the command output or else the log, and Escape closes the command output
/// or else clears the line and moves to the log. Every character typed is text, <c>q</c> included; the <c>q</c> command
/// leaves tail mode once Enter runs it.
/// </remarks>
internal sealed class TailInput
{
    private static readonly TextStyle SuggestionText = StyleParser.Parse("fg:#808080");
    private readonly TailScreen _screen;
    private readonly TailHistory _history;
    private readonly TextBoxLine _line;
    private readonly LineEditingKeys _lineKeys;
    private readonly TailSuggester _suggester;
    private (string Text, string? Suffix) _suggested = ("", null);

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
        _suggester = new TailSuggester(Commands.TailCatalog.Catalog, screen, history);
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
    /// The rest of the command the input suggests, when the caret is at the end of the line.
    /// </summary>
    public string? Suggestion => State.CursorPosition == State.Text.Length && !State.HasSelection ? Suffix(State.Text) : null;

    /// <summary>
    /// Builds the text box, as wide as its text, and the suggestion after it.
    /// </summary>
    /// <remarks>
    /// The text box has no fill of its own, so the line reads like a shell prompt.
    /// </remarks>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="more">Adds the screen's keys.</param>
    /// <param name="color">Whether colors are on.</param>
    /// <returns>The widgets.</returns>
    public Hex1bWidget[] Build<TParent>(WidgetContext<TParent> context, Action<InputBindingsBuilder> more, bool color)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(more);
        var box = context.TextBox()
            .ContentWidth()
            .State(State)
            .OnTextChanged(_ => _history.ResetNavigation())
            .InputBindings(bindings =>
            {
                Bind(bindings);
                more(bindings);
            });

        var suggestion = Suggestion;
        return
        [
            context.ThemePanel(theme => theme
                .Set(TextBoxTheme.FillBackgroundColor, Hex1bColor.Default)
                .Set(TextBoxTheme.FocusedFillBackgroundColor, Hex1bColor.Default), box),
            context.Surface(s =>
            [
                s.Layer(layer =>
                {
                    if (suggestion is not null)
                    {
                        _ = StyledBlock.DrawRow(layer, 0, 0, [new StyledSpan(suggestion, SuggestionText)], color);
                    }
                }),
            ]).FillWidth(),
        ];
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

        if (Suggestion is { } suggestion)
        {
            bindings.Remove(TextBoxWidget.MoveRight);
            bindings.Remove(TextBoxWidget.MoveEnd);
            bindings.Key(Hex1bKey.RightArrow).Action(_ => Accept(suggestion), "Accept the suggestion");
            bindings.Key(Hex1bKey.End).Action(_ => Accept(suggestion), "Accept the suggestion");
        }
    }

    private void Accept(string suggestion)
    {
        _line.Replace(_line.Text.Length, _line.Text.Length, suggestion);
        _history.ResetNavigation();
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

    private async Task SubmitAsync()
    {
        var text = Text;
        SetText("");
        _history.ResetNavigation();
        await _screen.RunCommandAsync(text);
    }
}
