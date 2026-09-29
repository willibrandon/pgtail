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
/// view scroll sideways to keep the cursor in sight.
/// </remarks>
/// <param name="log">The rows.</param>
/// <param name="color">False to draw attributes only, for <c>NO_COLOR</c>.</param>
internal sealed class TailLogView(TailLog log, bool color)
{
    private const int WheelLines = 3;
    private static readonly Hex1bColor SelectionBackground = Hex1bColor.FromRgb(38, 79, 120);
    private static readonly Hex1bColor ScrollTrack = Hex1bColor.FromBright(0, 128, 128, 128);
    private int _top;
    private int _left;
    private int _viewport = 20;
    private int _width = 80;
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
    /// Whether anything is selected: a visual selection or the highlighted cursor row.
    /// </summary>
    public bool HasSelection => (Visual || Navigating) && Log.Count > 0;

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
    /// together, each still take effect.
    /// </remarks>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="screenKeys">The screen's typed keys, handled with the view's.</param>
    /// <param name="more">Adds the screen's other keys.</param>
    /// <returns>The widget.</returns>
    public InteractableWidget Build<TParent>(
        WidgetContext<TParent> context,
        IReadOnlyDictionary<char, Action> screenKeys,
        Action<InputBindingsBuilder> more)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(screenKeys);
        ArgumentNullException.ThrowIfNull(more);
        return context.Interactable(i => i.Surface(s => [s.Layer(Draw)]).Fill())
            .InputBindings(bindings =>
            {
                Bind(bindings, screenKeys);
                more(bindings);
            });
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

    private void Bind(InputBindingsBuilder bindings, IReadOnlyDictionary<char, Action> screenKeys)
    {
        var keys = new Dictionary<char, Action>
        {
            ['j'] = () => Move(1),
            ['k'] = () => Move(-1),
            ['h'] = Left,
            ['l'] = Right,
            ['0'] = LineStart,
            ['$'] = LineEnd,
            ['g'] = Top,
            ['G'] = Bottom,
            ['p'] = () => PauseRequested?.Invoke(),
            ['f'] = Follow,
            ['v'] = () => StartVisual(lines: false),
            ['V'] = () => StartVisual(lines: true),
            ['y'] = Yank,
        };

        foreach (var (key, action) in screenKeys)
        {
            keys[key] = action;
        }

        bindings.Character(text => text.All(keys.ContainsKey)).Action(text =>
        {
            foreach (var key in text)
            {
                keys[key]();
            }
        }, "Log keys");

        bindings.Key(Hex1bKey.DownArrow).Action(_ => Move(1), "Down one line");
        bindings.Key(Hex1bKey.UpArrow).Action(_ => Move(-1), "Up one line");
        bindings.Key(Hex1bKey.LeftArrow).Action(_ => Left(), "Left");
        bindings.Key(Hex1bKey.RightArrow).Action(_ => Right(), "Right");
        bindings.Key(Hex1bKey.Home).Action(_ => Top(), "Top");
        bindings.Key(Hex1bKey.End).Action(_ => Bottom(), "Bottom");
        bindings.Ctrl().Key(Hex1bKey.D).Action(_ => Move(_viewport / 2), "Half page down");
        bindings.Ctrl().Key(Hex1bKey.U).Action(_ => Move(-(_viewport / 2)), "Half page up");
        bindings.Ctrl().Key(Hex1bKey.F).Action(_ => Move(_viewport), "Page down");
        bindings.Key(Hex1bKey.PageDown).Action(_ => Move(_viewport), "Page down");
        bindings.Ctrl().Key(Hex1bKey.B).Action(_ => Move(-_viewport), "Page up");
        bindings.Key(Hex1bKey.PageUp).Action(_ => Move(-_viewport), "Page up");
        bindings.Key(Hex1bKey.Escape).Action(_ => ClearSelection(), "Clear selection");
        bindings.Ctrl().Key(Hex1bKey.A).Action(_ => SelectAll(), "Select all");
        bindings.Mouse(MouseButton.ScrollUp).Action(_ => Scroll(-WheelLines), "Scroll up");
        bindings.Mouse(MouseButton.ScrollDown).Action(_ => Scroll(WheelLines), "Scroll down");
        bindings.Mouse(MouseButton.ScrollUp).Shift().Action(_ => _left = Math.Max(0, _left - WheelLines), "Scroll left");
        bindings.Mouse(MouseButton.ScrollDown).Shift().Action(_ => _left += WheelLines, "Scroll right");
        bindings.Drag(MouseButton.Left).Action(Drag, "Click to select a line, or drag to select and copy");
    }

    private void Draw(Surface surface)
    {
        _viewport = Math.Max(1, surface.Height);
        _width = Math.Max(1, surface.Width - 1);
        var count = Log.Count;
        var maxTop = Math.Max(0, count - _viewport);
        _top = Following ? maxTop : Math.Clamp(_top, 0, maxTop);
        var selection = Selection();
        for (var row = 0; row < _viewport && _top + row < count; row++)
        {
            var index = _top + row;
            DrawLine(surface, row, Log.Lines[index]);
            if (selection is { } range && index >= range.StartLine && index <= range.EndLine)
            {
                var text = Log.Lines[index].Text;
                var start = index == range.StartLine ? range.StartColumn : 0;
                var end = index == range.EndLine ? Math.Min(range.EndColumn, text.Length) : text.Length;
                Highlight(surface, row, text, start, end, fullWidth: VisualLines || !Visual, lineBreak: index != range.EndLine);
            }
        }

        if ((Navigating || Visual) && !VisualLines && _line >= _top && _line < Math.Min(count, _top + _viewport))
        {
            DrawCaret(surface, _line - _top, Log.Lines[_line].Text);
        }

        DrawScrollbar(surface, count);
    }

    private void DrawLine(Surface surface, int row, TailLine line)
    {
        var text = line.Text;
        var styles = line.Styles;
        var styleIndex = 0;
        var column = 0;
        var index = 0;
        while (index < text.Length)
        {
            var next = GraphemeHelper.GetNextClusterBoundary(text, index);
            if (next <= index)
            {
                next = index + 1;
            }

            var cluster = text[index..next];
            var width = Math.Max(1, GraphemeHelper.GetClusterDisplayWidth(cluster));
            while (styleIndex < styles.Count && styles[styleIndex].End <= index)
            {
                styleIndex++;
            }

            var style = styleIndex < styles.Count && styles[styleIndex].Start <= index ? styles[styleIndex].Style : TextStyle.Plain;
            var x = column - _left;
            if (x >= _width)
            {
                break;
            }

            if (x >= 0)
            {
                var foreground = color ? style.Foreground?.ToHex1b() : null;
                var background = color ? style.Background?.ToHex1b() : null;
                _ = surface.WriteText(x, row, cluster, foreground, background, style.Attributes.ToCellAttributes());
            }

            column += width;
            index = next;
        }
    }

    private void Highlight(Surface surface, int row, string text, int start, int end, bool fullWidth, bool lineBreak)
    {
        var from = GraphemeHelper.IndexToDisplayColumn(text, Math.Clamp(start, 0, text.Length)) - _left;
        var to = fullWidth ? _width : GraphemeHelper.IndexToDisplayColumn(text, Math.Clamp(end, 0, text.Length)) - _left;
        if (!fullWidth && (lineBreak || end > text.Length))
        {
            to++;
        }

        for (var x = Math.Max(0, from); x < Math.Min(_width, to); x++)
        {
            var cell = surface[x, row];
            if (cell.IsContinuation)
            {
                continue;
            }

            if (cell == SurfaceCells.Empty)
            {
                cell = cell with { Character = " " };
            }

            surface[x, row] = color
                ? cell.WithBackground(SelectionBackground)
                : cell.WithAddedAttributes(CellAttributes.Reverse);
        }
    }

    private void DrawCaret(Surface surface, int row, string text)
    {
        var x = GraphemeHelper.IndexToDisplayColumn(text, Math.Min(_column, text.Length)) - _left;
        if (x < 0 || x >= _width)
        {
            return;
        }

        var cell = surface[x, row];
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

        var x = surface.Width - 1;
        var thumb = Math.Max(1, _viewport * _viewport / count);
        var travel = _viewport - thumb;
        var position = travel * _top / Math.Max(1, count - _viewport);
        for (var row = 0; row < _viewport; row++)
        {
            var inThumb = row >= position && row < position + thumb;
            _ = surface.WriteText(x, row, inThumb ? "▉" : "│", color ? ScrollTrack : null, null);
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
            var (first, last) = (Math.Min(_anchorLine, _line), Math.Max(_anchorLine, _line));
            return (first, 0, last, Length(last));
        }

        if (Visual)
        {
            var anchorFirst = _anchorLine < _line || (_anchorLine == _line && _anchorColumn <= _column);
            return anchorFirst
                ? (_anchorLine, _anchorColumn, _line, _column + 1)
                : (_line, _column, _anchorLine, _anchorColumn + 1);
        }

        return Navigating ? (_line, 0, _line, Length(_line)) : null;
    }

    private string? SelectedText() => Selection() is { } range
        ? Log.GetText(range.StartLine, range.StartColumn, range.EndLine, range.EndColumn)
        : null;

    private int Length(int line) => line >= 0 && line < Log.Count ? Log.Lines[line].Text.Length : 0;

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
        var maxTop = Math.Max(0, Log.Count - _viewport);
        _top = Math.Clamp((Following ? maxTop : _top) + delta, 0, maxTop);
        Following = _top >= maxTop;
    }

    private DragHandler Drag(int x, int y)
    {
        if (Log.Count == 0)
        {
            return new DragHandler();
        }

        var anchor = Hit(x, y);
        var dragged = false;
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

    private (int Line, int Column) Hit(int x, int y)
    {
        var maxTop = Math.Max(0, Log.Count - _viewport);
        _top = Following ? maxTop : _top;
        Following = false;
        var line = Math.Clamp(_top + y, 0, Log.Count - 1);
        var text = Log.Lines[line].Text;
        return (line, Math.Clamp(GraphemeHelper.DisplayColumnToIndex(text, Math.Max(0, _left + x)), 0, text.Length));
    }

    private void Reveal()
    {
        var maxTop = Math.Max(0, Log.Count - _viewport);
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
        var column = GraphemeHelper.IndexToDisplayColumn(Log.Lines[_line].Text, Math.Min(_column, Length(_line)));
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
