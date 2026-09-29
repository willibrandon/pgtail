using System.Text;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The tail log's rows, oldest first, keeping at most <see cref="MaxLines"/>.
/// </summary>
internal sealed class TailLog
{
    /// <summary>
    /// The most rows kept.
    /// </summary>
    public const int MaxLines = 10_000;

    private readonly List<TailLine> _lines = [];

    /// <summary>
    /// The rows, oldest first.
    /// </summary>
    public IReadOnlyList<TailLine> Lines => _lines;

    /// <summary>
    /// The number of rows.
    /// </summary>
    public int Count => _lines.Count;

    /// <summary>
    /// Appends rows made from styled lines, dropping the oldest past the limit.
    /// </summary>
    /// <param name="lines">The styled lines; embedded newlines start more rows.</param>
    /// <returns>The number of old rows dropped.</returns>
    public int Append(IEnumerable<StyledText> lines)
    {
        ArgumentNullException.ThrowIfNull(lines);
        foreach (var line in lines)
        {
            _lines.AddRange(TailLine.From(line));
        }

        var excess = _lines.Count - MaxLines;
        if (excess <= 0)
        {
            return 0;
        }

        _lines.RemoveRange(0, excess);
        return excess;
    }

    /// <summary>
    /// Removes every row.
    /// </summary>
    public void Clear() => _lines.Clear();

    /// <summary>
    /// The text between two positions, rows joined by newlines.
    /// </summary>
    /// <param name="startLine">The first row.</param>
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
}
