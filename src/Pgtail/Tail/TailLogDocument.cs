using System.Text;
using Hex1b.Documents;
using Hex1b.Widgets;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The tail log's rows, kept in a read-only editor document so Hex1b draws, scrolls, and selects them.
/// </summary>
/// <remarks>
/// At most <see cref="MaxLines"/> rows are kept; the oldest go first.
/// </remarks>
internal sealed class TailLogDocument
{
    /// <summary>
    /// The most rows kept.
    /// </summary>
    public const int MaxLines = 10_000;

    private readonly List<TailLine> _lines = [];

    /// <summary>
    /// The read-only editor state holding the rows' text.
    /// </summary>
    public EditorState Editor { get; } = new(new Hex1bDocument("")) { IsReadOnly = true, TabSize = 8 };

    /// <summary>
    /// The rows, oldest first.
    /// </summary>
    public IReadOnlyList<TailLine> Lines => _lines;

    /// <summary>
    /// The number of rows.
    /// </summary>
    public int Count => _lines.Count;

    /// <summary>
    /// Appends rows made from styled lines.
    /// </summary>
    /// <param name="lines">The styled lines; embedded newlines start more rows.</param>
    /// <returns>The number of rows added.</returns>
    public int Append(IEnumerable<StyledText> lines)
    {
        ArgumentNullException.ThrowIfNull(lines);
        var added = lines.SelectMany(TailLine.From).ToList();
        if (added.Count == 0)
        {
            return 0;
        }

        var document = Editor.Document;
        var text = string.Join('\n', added.Select(line => line.Text));
        if (_lines.Count > 0)
        {
            text = "\n" + text;
        }

        _ = document.Apply(new InsertOperation(new DocumentOffset(document.Length), text), "tail");
        _lines.AddRange(added);
        Prune();
        return added.Count;
    }

    /// <summary>
    /// Removes every row.
    /// </summary>
    public void Clear()
    {
        var document = Editor.Document;
        _ = document.Apply(new DeleteOperation(new DocumentRange(DocumentOffset.Zero, new DocumentOffset(document.Length))), "tail");
        _lines.Clear();
        Editor.Cursor.ClearSelection();
        Editor.SetCursorPosition(DocumentOffset.Zero);
    }

    /// <summary>
    /// The text between two positions, rows joined by newlines.
    /// </summary>
    /// <param name="startLine">The first row, counting from zero.</param>
    /// <param name="startColumn">The first character in it.</param>
    /// <param name="endLine">The last row.</param>
    /// <param name="endColumn">The character just past the end in it.</param>
    /// <returns>The text.</returns>
    public string GetText(int startLine, int startColumn, int endLine, int endColumn)
    {
        if (_lines.Count == 0)
        {
            return "";
        }

        startLine = Math.Clamp(startLine, 0, _lines.Count - 1);
        endLine = Math.Clamp(endLine, 0, _lines.Count - 1);
        if (startLine == endLine)
        {
            var text = _lines[startLine].Text;
            var from = Math.Clamp(startColumn, 0, text.Length);
            return text[from..Math.Clamp(endColumn, from, text.Length)];
        }

        var builder = new StringBuilder();
        var first = _lines[startLine].Text;
        builder.Append(first[Math.Clamp(startColumn, 0, first.Length)..]);
        for (var line = startLine + 1; line < endLine; line++)
        {
            builder.Append('\n').Append(_lines[line].Text);
        }

        var last = _lines[endLine].Text;
        return builder.Append('\n').Append(last[..Math.Clamp(endColumn, 0, last.Length)]).ToString();
    }

    /// <summary>
    /// The document offset of a row and column.
    /// </summary>
    /// <param name="line">The row, counting from zero.</param>
    /// <param name="column">The character in it.</param>
    /// <returns>The offset.</returns>
    public DocumentOffset OffsetOf(int line, int column)
    {
        var document = Editor.Document;
        if (_lines.Count == 0)
        {
            return DocumentOffset.Zero;
        }

        line = Math.Clamp(line, 0, _lines.Count - 1);
        var start = document.PositionToOffset(new DocumentPosition(line + 1, 1));
        return new DocumentOffset(start.Value + Math.Clamp(column, 0, _lines[line].Text.Length));
    }

    private void Prune()
    {
        var excess = _lines.Count - MaxLines;
        if (excess <= 0)
        {
            return;
        }

        var document = Editor.Document;
        var end = document.PositionToOffset(new DocumentPosition(excess + 1, 1));
        _ = document.Apply(new DeleteOperation(new DocumentRange(DocumentOffset.Zero, end)), "tail");
        _lines.RemoveRange(0, excess);
    }
}
