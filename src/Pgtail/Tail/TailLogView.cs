using Hex1b;
using Hex1b.Input;
using Hex1b.Surfaces;
using Hex1b.Theming;
using Hex1b.Widgets;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The tail log view: scrolling, following new rows, vim-style keys, visual selection, and the mouse.
/// </summary>
/// <remarks>
/// The view stays on the newest rows while it is at the end. Moving the cursor highlights its row and marks its column;
/// <c>v</c> selects characters from where it was pressed and <c>V</c> whole rows; <c>y</c> copies the selection. The
/// mouse wheel scrolls, a click selects a row, and dragging selects text and copies it on release. Rows longer than the
/// view scroll sideways to keep the cursor in sight, and with the arrow keys, a sideways swipe, the wheel with Shift or
/// Ctrl, or the scrollbar along the bottom, as far as the widest row in the log.
/// </remarks>
/// <param name="log">The rows.</param>
/// <param name="color">False to draw attributes only, for <c>NO_COLOR</c>.</param>
internal sealed class TailLogView(TailLog log, bool color)
{
    private const int WheelLines = 3;
    private static readonly Hex1bColor s_selectionBackground = Hex1bColor.FromRgb(38, 79, 120);
    private static readonly Hex1bColor s_scrollTrack = Hex1bColor.FromBright(0, 128, 128, 128);
    private int _top;
    private int _left;
    private int _viewport = 20;
    private int _height = 20;
    private int _width = 80;
    private bool _sideways;
    private int _line;
    private int _column;
    private int _anchorLine;
    private int _anchorColumn;

    /// <summary>
    /// The rows.
    /// </summary>
    public TailLog Log { get; } = log;

    /// <summary>
    /// Whether the view shows the newest rows and keeps doing so as rows arrive.
    /// </summary>
    public bool Following { get; private set; } = true;

    /// <summary>
    /// Whether the cursor's row is highlighted because the user moved to it.
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
    /// Called when the user asks to pause with <c>p</c>.
    /// </summary>
    public Action? PauseRequested { get; set; }

    /// <summary>
    /// Called when the user asks to follow with <c>f</c>.
    /// </summary>
    public Action? FollowRequested { get; set; }

    /// <summary>
    /// Called with text to put on the clipboard, and whether to announce it.
    /// </summary>
    public Action<string, bool>? Copy { get; set; }

    /// <summary>
    /// Builds the view.
    /// </summary>
    /// <remarks>
    /// Typed keys are handled a character at a time, so keys typed faster than the screen reads them, which arrive
    /// together, each still take effect. Typed text holding any other character is a command being typed, and goes to
    /// <paramref name="typed"/>.
    /// </remarks>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="screenKeys">The screen's typed keys, handled with the view's.</param>
    /// <param name="typed">Receives text typed that is not the view's or the screen's keys.</param>
    /// <param name="more">Adds the screen's other keys.</param>
    /// <returns>The widget.</returns>
    public InteractableWidget Build<TParent>(
        WidgetContext<TParent> context,
        IReadOnlyDictionary<char, Action<InputBindingActionContext>> screenKeys,
        Action<string, InputBindingActionContext> typed,
        Action<InputBindingsBuilder> more)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(screenKeys);
        ArgumentNullException.ThrowIfNull(typed);
        ArgumentNullException.ThrowIfNull(more);
        return context.Interactable(i => i.Surface(s => [s.Layer(Draw)]).Fill())
            .InputBindings(bindings =>
            {
                Bind(bindings, screenKeys, typed);
                more(bindings);
            });
    }

    /// <summary>
    /// The number of screen rows the view took when last drawn, its sideways scrollbar included.
    /// </summary>
    public int Height => _height;

    /// <summary>
    /// Scrolls a page at a time, as Page Up and Page Down do.
    /// </summary>
    /// <param name="pages">The pages to scroll, negative for up.</param>
    public void Page(int pages) => ScrollWithCaret(pages * _viewport);

    /// <summary>
    /// Adjusts for rows put in front of the log, so the rows on screen and the selection stay where they are.
    /// </summary>
    /// <param name="rows">The number of rows put in.</param>
    public void Prepended(int rows)
    {
        _top += rows;
        _line += rows;
        _anchorLine += rows;
    }

    /// <summary>
    /// Adjusts for rows dropped from the start of the log.
    /// </summary>
    /// <param name="dropped">The number of rows dropped.</param>
    public void Dropped(int dropped)
    {
        if (dropped <= 0)
        {
            return;
        }

        _top = Math.Max(0, _top - dropped);
        _line = Math.Max(0, _line - dropped);
        _anchorLine = Math.Max(0, _anchorLine - dropped);
    }

    /// <summary>
    /// Returns to the newest rows with nothing selected, as after the log is cleared or redrawn.
    /// </summary>
    public void Reset()
    {
        ClearSelection();
        _left = 0;
        Following = true;
    }

    /// <summary>
    /// Scrolls to the newest rows and follows them, keeping the selection.
    /// </summary>
    public void ShowEnd() => Following = true;

    /// <summary>
    /// Clears the selection and leaves visual mode.
    /// </summary>
    public void ClearSelection()
    {
        Visual = false;
        VisualLines = false;
        Navigating = false;
    }

    /// <summary>
    /// Returns to the newest rows and follows.
    /// </summary>
    public void Follow()
    {
        Reset();
        FollowRequested?.Invoke();
    }

    /// <summary>
    /// Copies the selection, when there is one.
    /// </summary>
    /// <returns>True when something was copied.</returns>
    public bool CopySelection()
    {
        if (SelectedText() is not { Length: > 0 } text)
        {
            return false;
        }

        Copy?.Invoke(text, true);
        return true;
    }

    private void Bind(
        InputBindingsBuilder bindings,
        IReadOnlyDictionary<char, Action<InputBindingActionContext>> screenKeys,
        Action<string, InputBindingActionContext> typed)
    {
        var keys = new Dictionary<char, Action<InputBindingActionContext>>
        {
            ['j'] = _ => Move(1),
            ['k'] = _ => Move(-1),
            ['h'] = _ => Left(),
            ['l'] = _ => Right(),
            ['0'] = _ => LineStart(),
            ['$'] = _ => LineEnd(),
            ['g'] = _ => Top(),
            ['G'] = _ => Bottom(),
            ['p'] = _ => PauseRequested?.Invoke(),
            ['f'] = _ => Follow(),
            ['v'] = _ => StartVisual(lines: false),
            ['V'] = _ => StartVisual(lines: true),
            ['y'] = _ => Yank(),
        };

        foreach ((char key, Action<InputBindingActionContext> action) in screenKeys)
        {
            keys[key] = action;
        }

        bindings.Character(text => text.All(keys.ContainsKey)).Action((text, context) =>
        {
            foreach (char key in text)
            {
                keys[key](context);
            }

            return Task.CompletedTask;
        }, "Log keys");

        bindings.Character(text => !text.All(keys.ContainsKey) && !text.Any(char.IsControl)).Action((text, context) =>
        {
            typed(text, context);
            return Task.CompletedTask;
        }, "Type a command");

        bindings.Key(Hex1bKey.DownArrow).Action(_ => Move(1), "Down one line");
        bindings.Key(Hex1bKey.UpArrow).Action(_ => Move(-1), "Up one line");
        bindings.Key(Hex1bKey.LeftArrow).Action(_ => Arrow(-1), "Scroll left, or move the cursor left");
        bindings.Key(Hex1bKey.RightArrow).Action(_ => Arrow(1), "Scroll right, or move the cursor right");
        bindings.Key(Hex1bKey.Home).Action(_ => Top(), "Top");
        bindings.Key(Hex1bKey.End).Action(_ => Bottom(), "Bottom");
        bindings.Ctrl().Key(Hex1bKey.D).Action(_ => ScrollWithCaret(_viewport / 2), "Half page down");
        bindings.Ctrl().Key(Hex1bKey.U).Action(_ => ScrollWithCaret(-(_viewport / 2)), "Half page up");
        bindings.Ctrl().Key(Hex1bKey.F).Action(_ => Page(1), "Page down");
        bindings.Key(Hex1bKey.PageDown).Action(_ => Page(1), "Page down");
        bindings.Ctrl().Key(Hex1bKey.B).Action(_ => Page(-1), "Page up");
        bindings.Key(Hex1bKey.PageUp).Action(_ => Page(-1), "Page up");
        bindings.Key(Hex1bKey.Escape).Action(_ => ClearSelection(), "Clear selection");
        bindings.Ctrl().Key(Hex1bKey.A).Action(_ => SelectAll(), "Select all");
        bindings.Mouse(MouseButton.ScrollUp).Action(_ => Scroll(-WheelLines), "Scroll up");
        bindings.Mouse(MouseButton.ScrollDown).Action(_ => Scroll(WheelLines), "Scroll down");
        bindings.Mouse(MouseButton.ScrollUp).Shift().Action(_ => ScrollSideways(-WheelLines), "Scroll left");
        bindings.Mouse(MouseButton.ScrollDown).Shift().Action(_ => ScrollSideways(WheelLines), "Scroll right");
        bindings.Mouse(MouseButton.ScrollUp).Ctrl().Action(_ => ScrollSideways(-WheelLines), "Scroll left");
        bindings.Mouse(MouseButton.ScrollDown).Ctrl().Action(_ => ScrollSideways(WheelLines), "Scroll right");
        bindings.Drag(MouseButton.Left).Action(Drag, "Click to select a line, or drag to select and copy");
    }

    private void Draw(Surface surface)
    {
        _height = Math.Max(1, surface.Height);
        _width = Math.Max(1, surface.Width - 1);
        _sideways = MaxLeft() > 0 && _height > 1;
        _viewport = _height - (_sideways ? 1 : 0);
        int count = Log.Count;
        int maxTop = Math.Max(0, count - _viewport);
        _top = Following ? maxTop : Math.Clamp(_top, 0, maxTop);
        _left = Math.Clamp(_left, 0, MaxLeft());
        (int StartLine, int StartColumn, int EndLine, int EndColumn)? selection = Selection();
        for (int row = 0; row < _viewport && _top + row < count; row++)
        {
            int index = _top + row;
            DrawLine(surface, row, Log.Row(index));
            if (selection is { } range && index >= range.StartLine && index <= range.EndLine)
            {
                string text = Log.Row(index).Text;
                int start = index == range.StartLine ? range.StartColumn : 0;
                int end = index == range.EndLine ? Math.Min(range.EndColumn, text.Length) : text.Length;
                Highlight(surface, row, text, start, end, fullWidth: VisualLines || !Visual, lineBreak: index != range.EndLine);
            }
        }

        if ((Navigating || Visual) && !VisualLines && _line >= _top && _line < Math.Min(count, _top + _viewport))
        {
            DrawCaret(surface, _line - _top, Log.Row(_line).Text);
        }

        DrawScrollbar(surface, count);
        DrawSidewaysScrollbar(surface);
    }

    private void DrawLine(Surface surface, int row, TailLine line)
    {
        string text = line.Text;
        IReadOnlyList<(int Start, int End, TextStyle Style)> styles = line.Styles;
        int styleIndex = 0;
        int column = 0;
        int index = 0;
        while (index < text.Length)
        {
            int next = GraphemeHelper.GetNextClusterBoundary(text, index);
            if (next <= index)
            {
                next = index + 1;
            }

            string cluster = text[index..next];
            int width = Math.Max(1, GraphemeHelper.GetClusterDisplayWidth(cluster));
            while (styleIndex < styles.Count && styles[styleIndex].End <= index)
            {
                styleIndex++;
            }

            TextStyle style = styleIndex < styles.Count && styles[styleIndex].Start <= index ? styles[styleIndex].Style : TextStyle.Plain;
            int x = column - _left;
            if (x >= _width)
            {
                break;
            }

            if (x >= 0)
            {
                Hex1bColor? foreground = color ? style.Foreground?.ToHex1b() : null;
                Hex1bColor? background = color ? style.Background?.ToHex1b() : null;
                _ = surface.WriteText(x, row, cluster, foreground, background, style.Attributes.ToCellAttributes());
            }

            column += width;
            index = next;
        }
    }

    private void Highlight(Surface surface, int row, string text, int start, int end, bool fullWidth, bool lineBreak)
    {
        int from = GraphemeHelper.IndexToDisplayColumn(text, Math.Clamp(start, 0, text.Length)) - _left;
        int to = fullWidth ? _width : GraphemeHelper.IndexToDisplayColumn(text, Math.Clamp(end, 0, text.Length)) - _left;
        if (!fullWidth && (lineBreak || end > text.Length))
        {
            to++;
        }

        for (int x = Math.Max(0, from); x < Math.Min(_width, to); x++)
        {
            SurfaceCell cell = surface[x, row];
            if (cell.IsContinuation)
            {
                continue;
            }

            if (cell == SurfaceCells.Empty)
            {
                cell = cell with { Character = " " };
            }

            surface[x, row] = color
                ? cell.WithBackground(s_selectionBackground)
                : cell.WithAddedAttributes(CellAttributes.Reverse);
        }
    }

    private void DrawCaret(Surface surface, int row, string text)
    {
        int x = GraphemeHelper.IndexToDisplayColumn(text, Math.Min(_column, text.Length)) - _left;
        if (x < 0 || x >= _width)
        {
            return;
        }

        SurfaceCell cell = surface[x, row];
        if (cell == SurfaceCells.Empty)
        {
            cell = cell with { Character = " " };
        }

        surface[x, row] = cell.WithAttributes(cell.Attributes ^ CellAttributes.Reverse);
    }

    private void DrawScrollbar(Surface surface, int count)
    {
        if (count <= _viewport)
        {
            return;
        }

        int x = surface.Width - 1;
        int thumb = Math.Max(1, _viewport * _viewport / count);
        int travel = _viewport - thumb;
        int position = travel * _top / Math.Max(1, count - _viewport);
        for (int row = 0; row < _viewport; row++)
        {
            bool inThumb = row >= position && row < position + thumb;
            _ = surface.WriteText(x, row, inThumb ? "▉" : "│", color ? s_scrollTrack : null, null);
        }
    }

    // The sideways scrollbar, drawn below the rows like the scrollbar beside them, when a row is wider than the view.
    private void DrawSidewaysScrollbar(Surface surface)
    {
        if (!_sideways)
        {
            return;
        }

        int maxLeft = MaxLeft();
        int thumb = Math.Max(1, _width * _width / (_width + maxLeft));
        int travel = _width - thumb;
        int position = travel * _left / Math.Max(1, maxLeft);
        for (int x = 0; x < _width; x++)
        {
            bool inThumb = x >= position && x < position + thumb;
            _ = surface.WriteText(x, _viewport, inThumb ? "▇" : "─", color ? s_scrollTrack : null, null);
        }
    }

    private (int StartLine, int StartColumn, int EndLine, int EndColumn)? Selection()
    {
        if (Log.Count == 0)
        {
            return null;
        }

        if (Visual && VisualLines)
        {
            (int first, int last) = (Math.Min(_anchorLine, _line), Math.Max(_anchorLine, _line));
            return (first, 0, last, Length(last));
        }

        if (Visual)
        {
            bool anchorFirst = _anchorLine < _line || (_anchorLine == _line && _anchorColumn <= _column);
            return anchorFirst
                ? (_anchorLine, _anchorColumn, _line, _column + 1)
                : (_line, _column, _anchorLine, _anchorColumn + 1);
        }

        return Navigating ? (_line, 0, _line, Length(_line)) : null;
    }

    private string? SelectedText() => Selection() is { } range
        ? Log.GetText(range.StartLine, range.StartColumn, range.EndLine, range.EndColumn)
        : null;

    private int Length(int line) => line >= 0 && line < Log.Count ? Log.Row(line).Text.Length : 0;

    private void BeginNavigation()
    {
        if (!Navigating && !Visual)
        {
            _line = Math.Clamp(_top + _viewport - 1, 0, Math.Max(0, Log.Count - 1));
            if (Following)
            {
                _line = Math.Max(0, Log.Count - 1);
            }

            _column = 0;
        }

        Navigating = true;
    }

    private void Move(int delta)
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        _line = Math.Clamp(_line + delta, 0, Log.Count - 1);
        _column = Math.Min(_column, Length(_line));
        Reveal();
    }

    // Scrolls the view by rows and carries the cursor line along, as a pager's page keys do; at either end, where the view
    // cannot move, the cursor line goes the rest of the way.
    private void ScrollWithCaret(int delta)
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        int maxTop = Math.Max(0, Log.Count - _viewport);
        int top = Following ? maxTop : _top;
        int target = Math.Clamp(top + delta, 0, maxTop);
        Following = false;
        _top = target;
        _line = Math.Clamp(_line + (target != top ? target - top : delta), 0, Log.Count - 1);
        _column = Math.Min(_column, Length(_line));
        Reveal();
    }

    private void Top()
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        _line = 0;
        _column = 0;
        Reveal();
    }

    private void Bottom()
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        _line = Log.Count - 1;
        _column = Math.Min(_column, Length(_line));
        Reveal();
    }

    // The arrow keys move the cursor while a row is highlighted or text is being selected, and otherwise scroll sideways.
    private void Arrow(int direction)
    {
        if (Navigating || Visual)
        {
            if (direction < 0)
            {
                Left();
            }
            else
            {
                Right();
            }
        }
        else
        {
            ScrollSideways(direction);
        }
    }

    private void ScrollSideways(int columns) => _left = Math.Clamp(_left + columns, 0, MaxLeft());

    // How far the view can scroll sideways: to the end of the widest row in the log, and one column past it while there is
    // a cursor, which can sit just after a row's last character.
    private int MaxLeft() => Math.Max(0, Log.Widest + (Navigating || Visual ? 1 : 0) - _width);

    private void ScrollSidewaysTo(int column) =>
        _left = (int)((long)Math.Clamp(column, 0, _width - 1) * MaxLeft() / Math.Max(1, _width - 1));

    private void Left()
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        if (_column > 0)
        {
            _column--;
        }
        else if (_line > 0)
        {
            _line--;
            _column = Length(_line);
        }

        Reveal();
    }

    private void Right()
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        if (_column < Length(_line))
        {
            _column++;
        }
        else if (_line < Log.Count - 1)
        {
            _line++;
            _column = 0;
        }

        Reveal();
    }

    private void LineStart()
    {
        _column = 0;
        Reveal();
    }

    private void LineEnd()
    {
        if (Log.Count > 0 && (Navigating || Visual))
        {
            _column = Length(_line);
            Reveal();
        }
    }

    private void StartVisual(bool lines)
    {
        if (Log.Count == 0)
        {
            return;
        }

        BeginNavigation();
        Visual = true;
        VisualLines = lines;
        _anchorLine = _line;
        _anchorColumn = _column;
        Reveal();
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
    }

    private void Scroll(int delta)
    {
        int maxTop = Math.Max(0, Log.Count - _viewport);
        _top = Math.Clamp((Following ? maxTop : _top) + delta, 0, maxTop);
        Following = _top >= maxTop;
    }

    private DragHandler Drag(int x, int y)
    {
        if (Log.Count == 0)
        {
            return new DragHandler();
        }

        // Pressing a scrollbar jumps to that point of the log, and dragging moves through it.
        if (_sideways && y >= _viewport)
        {
            if (x >= _width)
            {
                return new DragHandler();
            }

            ScrollSidewaysTo(x);
            return new DragHandler(onMove: (_, deltaX, _) => ScrollSidewaysTo(x + deltaX));
        }

        if (x >= _width && Log.Count > _viewport)
        {
            ScrollTo(y);
            return new DragHandler(onMove: (_, _, deltaY) => ScrollTo(y + deltaY));
        }

        (int Line, int Column) anchor = Hit(x, y);
        bool dragged = false;
        return new DragHandler(
            onMove: (_, deltaX, deltaY) =>
            {
                if (!dragged && Math.Abs(deltaX) <= 1 && deltaY == 0)
                {
                    return;
                }

                dragged = true;
                (_anchorLine, _anchorColumn) = anchor;
                (_line, _column) = Hit(x + deltaX, y + deltaY);
                Navigating = true;
                Visual = true;
                VisualLines = false;
            },
            onEnd: _ =>
            {
                if (!dragged)
                {
                    Visual = false;
                    VisualLines = false;
                    Navigating = true;
                    (_line, _column) = (anchor.Line, 0);
                    Reveal();
                }
                else if (SelectedText() is { Length: > 0 } text)
                {
                    Copy?.Invoke(text, false);
                }
            });
    }

    private void ScrollTo(int row)
    {
        int maxTop = Math.Max(0, Log.Count - _viewport);
        _top = (int)((long)Math.Clamp(row, 0, _viewport - 1) * maxTop / Math.Max(1, _viewport - 1));
        Following = _top >= maxTop;
    }

    private (int Line, int Column) Hit(int x, int y)
    {
        int maxTop = Math.Max(0, Log.Count - _viewport);
        _top = Following ? maxTop : _top;
        Following = false;
        int line = Math.Clamp(_top + y, 0, Log.Count - 1);
        string text = Log.Row(line).Text;
        return (line, Math.Clamp(GraphemeHelper.DisplayColumnToIndex(text, Math.Max(0, _left + x)), 0, text.Length));
    }

    private void Reveal()
    {
        int maxTop = Math.Max(0, Log.Count - _viewport);
        if (Following)
        {
            _top = maxTop;
        }

        if (_line < _top)
        {
            _top = _line;
        }
        else if (_line >= _top + _viewport)
        {
            _top = _line - _viewport + 1;
        }

        _top = Math.Clamp(_top, 0, maxTop);
        int column = GraphemeHelper.IndexToDisplayColumn(Log.Row(_line).Text, Math.Min(_column, Length(_line)));
        if (column < _left)
        {
            _left = column;
        }
        else if (column >= _left + _width)
        {
            _left = column - _width + 1;
        }

        Following = _top >= maxTop && _line == Log.Count - 1;
    }
}
