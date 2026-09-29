using Hex1b;
using Hex1b.Input;
using Hex1b.Widgets;

namespace Pgtail.Tail;

/// <summary>
/// Moves through the tail log and selects in it with vim-style keys, the mouse, and visual modes.
/// </summary>
/// <remarks>
/// Moving highlights the current row, as selecting a row does. <c>v</c> selects characters from where it was pressed,
/// <c>V</c> selects whole rows, <c>y</c> copies the selection, and Escape clears it. Leaving the last row stops
/// following new entries; returning to it or pressing <c>f</c> resumes.
/// </remarks>
/// <param name="log">The log.</param>
internal sealed class TailLogView(TailLogDocument log)
{
    private const int WheelLines = 3;
    private int _line;
    private int _column;
    private int _anchorLine;
    private int _anchorColumn;

    /// <summary>
    /// The log.
    /// </summary>
    public TailLogDocument Log { get; } = log;

    /// <summary>
    /// Whether a row is highlighted because the user moved to it.
    /// </summary>
    public bool Navigating { get; private set; }

    /// <summary>
    /// Whether visual mode is on.
    /// </summary>
    public bool Visual { get; private set; }

    /// <summary>
    /// Whether visual mode selects whole rows.
    /// </summary>
    public bool VisualLines { get; private set; }

    /// <summary>
    /// Whether the user moved away from the last row, so new entries should not scroll it.
    /// </summary>
    public bool AwayFromEnd => Navigating && _line < Log.Count - 1;

    /// <summary>
    /// The row the cursor is on, counting from zero.
    /// </summary>
    public int CursorLine => _line;

    /// <summary>
    /// The character the cursor is on.
    /// </summary>
    public int CursorColumn => _column;

    /// <summary>
    /// Called when the user asks to pause with <c>p</c>.
    /// </summary>
    public Action? PauseRequested { get; set; }

    /// <summary>
    /// Called when the user asks to follow with <c>f</c>, <c>G</c>, or by returning to the last row.
    /// </summary>
    public Action? FollowRequested { get; set; }

    /// <summary>
    /// Called with text to put on the clipboard, and whether to announce it.
    /// </summary>
    public Action<string, bool>? Copy { get; set; }

    /// <summary>
    /// Adds the log's keys and mouse handling to the editor's bindings.
    /// </summary>
    /// <param name="bindings">The editor's bindings.</param>
    public void Bind(InputBindingsBuilder bindings)
    {
        ArgumentNullException.ThrowIfNull(bindings);
        foreach (var action in new[]
        {
            EditorWidget.MoveUp, EditorWidget.MoveDown, EditorWidget.MoveLeft, EditorWidget.MoveRight,
            EditorWidget.MoveToLineStart, EditorWidget.MoveToLineEnd, EditorWidget.MoveToDocumentStart,
            EditorWidget.MoveToDocumentEnd, EditorWidget.PageUp, EditorWidget.PageDown, EditorWidget.SelectAll,
            EditorWidget.ScrollUp, EditorWidget.ScrollDown, EditorWidget.Click, EditorWidget.DoubleClick,
            EditorWidget.TripleClick, EditorWidget.CtrlClick, EditorWidget.AddCursorAtNextMatch,
        })
        {
            bindings.Remove(action);
        }

        bindings.Remove(Hex1bKey.Escape);
        bindings.Key(Hex1bKey.J).Action(_ => Move(1), "Down one line");
        bindings.Key(Hex1bKey.DownArrow).Action(_ => Move(1), "Down one line");
        bindings.Key(Hex1bKey.K).Action(_ => Move(-1), "Up one line");
        bindings.Key(Hex1bKey.UpArrow).Action(_ => Move(-1), "Up one line");
        bindings.Key(Hex1bKey.H).Action(_ => Left(), "Left");
        bindings.Key(Hex1bKey.LeftArrow).Action(_ => Left(), "Left");
        bindings.Key(Hex1bKey.L).Action(_ => Right(), "Right");
        bindings.Key(Hex1bKey.RightArrow).Action(_ => Right(), "Right");
        bindings.Key(Hex1bKey.D0).Action(_ => LineStart(), "Line start");
        bindings.Character(text => text == "$").Action(_ => LineEnd(), "Line end");
        bindings.Key(Hex1bKey.G).Action(_ => Top(), "Top");
        bindings.Key(Hex1bKey.Home).Action(_ => Top(), "Top");
        bindings.Shift().Key(Hex1bKey.G).Action(_ => Bottom(), "Bottom");
        bindings.Key(Hex1bKey.End).Action(_ => Bottom(), "Bottom");
        bindings.Ctrl().Key(Hex1bKey.D).Action(context => Move(Page(context) / 2), "Half page down");
        bindings.Ctrl().Key(Hex1bKey.U).Action(context => Move(-(Page(context) / 2)), "Half page up");
        bindings.Ctrl().Key(Hex1bKey.F).Action(context => Move(Page(context)), "Page down");
        bindings.Key(Hex1bKey.PageDown).Action(context => Move(Page(context)), "Page down");
        bindings.Ctrl().Key(Hex1bKey.B).Action(context => Move(-Page(context)), "Page up");
        bindings.Key(Hex1bKey.PageUp).Action(context => Move(-Page(context)), "Page up");
        bindings.Key(Hex1bKey.P).Action(_ => PauseRequested?.Invoke(), "Pause");
        bindings.Key(Hex1bKey.F).Action(_ => Follow(), "Follow");
        bindings.Key(Hex1bKey.V).Action(_ => StartVisual(lines: false), "Visual mode");
        bindings.Shift().Key(Hex1bKey.V).Action(_ => StartVisual(lines: true), "Visual line mode");
        bindings.Key(Hex1bKey.Y).Action(_ => Yank(), "Yank selection");
        bindings.Key(Hex1bKey.Escape).Action(_ => ClearSelection(), "Clear selection");
        bindings.Ctrl().Key(Hex1bKey.A).Action(_ => SelectAll(), "Select all");
        bindings.Mouse(MouseButton.ScrollUp).Action(_ => Move(-WheelLines), "Scroll up");
        bindings.Mouse(MouseButton.ScrollDown).Action(_ => Move(WheelLines), "Scroll down");
        bindings.Mouse(MouseButton.Left).Action(context => Click(context), "Select the clicked line");
        bindings.Drag(MouseButton.Left).Action((x, y) => Drag(x, y), "Drag to select and copy");
    }

    /// <summary>
    /// Copies the selection, when there is one.
    /// </summary>
    /// <returns>True when something was copied.</returns>
    public bool CopySelection()
    {
        var text = SelectedText();
        if (text.Length == 0)
        {
            return false;
        }

        Copy?.Invoke(text, true);
        return true;
    }

    /// <summary>
    /// Whether any text is selected.
    /// </summary>
    public bool HasSelection => Log.Editor.Cursor.HasSelection;

    /// <summary>
    /// Returns to following: clears the selection and moves to the end of the log.
    /// </summary>
    public void Follow()
    {
        EndNavigation();
        FollowRequested?.Invoke();
    }

    /// <summary>
    /// Clears the selection and leaves visual mode, keeping the cursor row.
    /// </summary>
    public void ClearSelection()
    {
        Visual = false;
        VisualLines = false;
        Navigating = false;
        Log.Editor.Cursor.ClearSelection();
    }

    /// <summary>
    /// Keeps the editor's caret at the end of the log while following.
    /// </summary>
    public void StickToEnd()
    {
        if (!Navigating && !Visual)
        {
            Log.Editor.Cursor.ClearSelection();
            Log.Editor.SetCursorPosition(new Hex1b.Documents.DocumentOffset(Log.Editor.Document.Length));
            _line = Math.Max(0, Log.Count - 1);
            _column = 0;
        }
    }

    /// <summary>
    /// Forgets the position after the log is cleared or rebuilt.
    /// </summary>
    public void Reset()
    {
        _line = 0;
        _column = 0;
        EndNavigation();
    }

    private void EndNavigation()
    {
        Visual = false;
        VisualLines = false;
        Navigating = false;
        StickToEnd();
    }

    private static int Page(InputBindingActionContext context) =>
        context.FocusedNode is EditorNode { ViewportLines: > 0 } editor ? editor.ViewportLines : 20;

    private void Move(int delta)
    {
        if (Log.Count == 0)
        {
            return;
        }

        _line = Math.Clamp(_line + delta, 0, Log.Count - 1);
        _column = Math.Min(_column, Log.Lines[_line].Text.Length);
        Navigating = true;
        Select();
    }

    private void Top()
    {
        if (Log.Count > 0)
        {
            _line = 0;
            Navigating = true;
            Select();
        }
    }

    private void Bottom()
    {
        if (Log.Count == 0)
        {
            return;
        }

        _line = Log.Count - 1;
        if (Visual)
        {
            Select();
            return;
        }

        Follow();
    }

    private void Left()
    {
        if (Log.Count == 0)
        {
            return;
        }

        if (_column > 0)
        {
            _column--;
        }
        else if (_line > 0)
        {
            _line--;
            _column = Log.Lines[_line].Text.Length;
        }

        Navigating = true;
        Select();
    }

    private void Right()
    {
        if (Log.Count == 0)
        {
            return;
        }

        if (_column < Log.Lines[_line].Text.Length)
        {
            _column++;
        }
        else if (_line < Log.Count - 1)
        {
            _line++;
            _column = 0;
        }

        Navigating = true;
        Select();
    }

    private void LineStart()
    {
        _column = 0;
        if (Visual && !VisualLines)
        {
            Select();
        }
    }

    private void LineEnd()
    {
        if (Log.Count > 0)
        {
            _column = Log.Lines[_line].Text.Length;
            if (Visual && !VisualLines)
            {
                Select();
            }
        }
    }

    private void StartVisual(bool lines)
    {
        if (Log.Count == 0)
        {
            return;
        }

        if (!Navigating)
        {
            _line = Log.Count - 1;
            _column = 0;
        }

        Visual = true;
        VisualLines = lines;
        Navigating = true;
        _anchorLine = _line;
        _anchorColumn = _column;
        Select();
    }

    private void Yank()
    {
        if (SelectedText() is { Length: > 0 } text)
        {
            Copy?.Invoke(text, true);
            ClearSelection();
        }
    }

    private void SelectAll()
    {
        if (Log.Count == 0)
        {
            return;
        }

        Navigating = true;
        Visual = true;
        VisualLines = true;
        _anchorLine = 0;
        _line = Log.Count - 1;
        Select();
    }

    private void Click(InputBindingActionContext context)
    {
        if (Log.Count == 0 || context.FocusedNode is not EditorNode editor)
        {
            return;
        }

        Visual = false;
        VisualLines = false;
        _line = Math.Clamp(editor.ScrollOffset - 1 + context.MouseY - editor.Bounds.Y, 0, Log.Count - 1);
        _column = 0;
        Navigating = true;
        Select();
    }

    private DragHandler Drag(int x, int y)
    {
        if (Log.Count == 0)
        {
            return new DragHandler();
        }

        EditorNode? editor = null;
        (int Line, int Column) Hit(InputBindingActionContext context, int column, int row)
        {
            editor ??= context.FocusedNode as EditorNode;
            var top = editor?.ScrollOffset ?? 1;
            var left = editor?.HorizontalScrollOffset ?? 0;
            var line = Math.Clamp(top - 1 + row, 0, Log.Count - 1);
            var text = Log.Lines[line].Text;
            return (line, Math.Clamp(GraphemeHelper.DisplayColumnToIndex(text, Math.Max(0, left + column)), 0, text.Length));
        }

        var started = false;
        return new DragHandler(
            onMove: (context, deltaX, deltaY) =>
            {
                if (!started)
                {
                    started = true;
                    (_anchorLine, _anchorColumn) = Hit(context, x, y);
                    Visual = true;
                    VisualLines = false;
                    Navigating = true;
                }

                (_line, _column) = Hit(context, x + deltaX, y + deltaY);
                _column = Math.Max(0, _column - 1);
                Select();
            },
            onEnd: _ =>
            {
                if (started && SelectedText() is { Length: > 0 } text)
                {
                    Copy?.Invoke(text, false);
                }
            });
    }

    private void Select()
    {
        var editor = Log.Editor;
        if (Log.Count == 0)
        {
            return;
        }

        int startLine, startColumn, endLine, endColumn;
        if (Visual && VisualLines)
        {
            (startLine, endLine) = (Math.Min(_anchorLine, _line), Math.Max(_anchorLine, _line));
            (startColumn, endColumn) = (0, Log.Lines[endLine].Text.Length);
        }
        else if (Visual)
        {
            var anchorFirst = _anchorLine < _line || (_anchorLine == _line && _anchorColumn <= _column);
            (startLine, startColumn, endLine, endColumn) = anchorFirst
                ? (_anchorLine, _anchorColumn, _line, _column + 1)
                : (_line, _column, _anchorLine, _anchorColumn + 1);
        }
        else
        {
            (startLine, startColumn, endLine, endColumn) = (_line, 0, _line, Log.Lines[_line].Text.Length);
        }

        var start = Log.OffsetOf(startLine, startColumn);
        var end = Log.OffsetOf(endLine, endColumn);
        var caret = Log.OffsetOf(_line, Visual ? _column : 0);
        var anchor = caret == start ? end : start;
        editor.SetCursorPosition(anchor);
        editor.SetCursorPosition(caret, extend: true);
        if (_line == Log.Count - 1 && !Visual)
        {
            FollowRequested?.Invoke();
        }
    }

    private string SelectedText()
    {
        var cursor = Log.Editor.Cursor;
        if (!cursor.HasSelection)
        {
            return "";
        }

        var document = Log.Editor.Document;
        return document.GetText(cursor.SelectionRange);
    }
}
