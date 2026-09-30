using System.Text;

namespace Pgtail.Tail;

/// <summary>
/// The tail log's rows, oldest first, keeping at most <see cref="MaxLines"/>.
/// </summary>
/// <remarks>
/// Rows are held in segments, one per entry, whose rows are made when first drawn; only the most recently made ones are
/// kept made, so a large log costs about what its entries do.
/// </remarks>
internal sealed class TailLog
{
    /// <summary>
    /// The most rows kept.
    /// </summary>
    public const int MaxLines = 400_000;

    private const int MadeLimit = 5_000;
    private readonly List<TailSegment> _segments = [];
    private readonly Queue<TailSegment> _made = new();
    private long _first;
    private long _next;

    /// <summary>
    /// The number of rows.
    /// </summary>
    public int Count => (int)(_next - _first);

    /// <summary>
    /// The number of rows that are log entries', leaving out messages such as command output.
    /// </summary>
    public int EntryRows { get; private set; }

    /// <summary>
    /// One of the rows.
    /// </summary>
    /// <param name="index">The row, counting from 0.</param>
    /// <returns>The row.</returns>
    public TailLine Row(int index)
    {
        var position = _first + index;
        var low = 0;
        var high = _segments.Count - 1;
        while (low < high)
        {
            var middle = (low + high + 1) / 2;
            if (_segments[middle].Start <= position)
            {
                low = middle;
            }
            else
            {
                high = middle - 1;
            }
        }

        var segment = _segments[low];
        if (!segment.IsMade)
        {
            _made.Enqueue(segment);
            if (_made.Count > MadeLimit)
            {
                _made.Dequeue().Forget();
            }
        }

        return segment.Row((int)(position - segment.Start));
    }

    /// <summary>
    /// Appends segments, dropping the oldest past the limit.
    /// </summary>
    /// <param name="segments">The segments.</param>
    /// <returns>The number of old rows dropped.</returns>
    public int Append(IEnumerable<TailSegment> segments)
    {
        ArgumentNullException.ThrowIfNull(segments);
        foreach (var segment in segments)
        {
            segment.Start = _next;
            _next += segment.RowCount;
            EntryRows += segment.IsEntry ? segment.RowCount : 0;
            _segments.Add(segment);
        }

        var dropped = 0;
        var remove = 0;
        while (Count - dropped > MaxLines && remove < _segments.Count)
        {
            var segment = _segments[remove++];
            dropped += segment.RowCount;
            EntryRows -= segment.IsEntry ? segment.RowCount : 0;
        }

        _segments.RemoveRange(0, remove);
        _first += dropped;
        return dropped;
    }

    /// <summary>
    /// Puts segments in front of the others, as older entries are read back, as many as fit under the limit.
    /// </summary>
    /// <param name="segments">The segments, oldest first.</param>
    /// <returns>The number of rows put in, those of the newest segments given.</returns>
    public int Prepend(IReadOnlyList<TailSegment> segments)
    {
        ArgumentNullException.ThrowIfNull(segments);
        var added = 0;
        var take = 0;
        for (var i = segments.Count - 1; i >= 0 && Count + added + segments[i].RowCount <= MaxLines; i--)
        {
            added += segments[i].RowCount;
            take++;
        }

        var start = _first - added;
        var kept = segments.Skip(segments.Count - take).ToList();
        foreach (var segment in kept)
        {
            segment.Start = start;
            start += segment.RowCount;
            EntryRows += segment.IsEntry ? segment.RowCount : 0;
        }

        _segments.InsertRange(0, kept);
        _first -= added;
        return added;
    }

    /// <summary>
    /// Removes every row.
    /// </summary>
    public void Clear()
    {
        _segments.Clear();
        _made.Clear();
        EntryRows = 0;
        _first = 0;
        _next = 0;
    }

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
        if (Count == 0)
        {
            return "";
        }

        startLine = Math.Clamp(startLine, 0, Count - 1);
        endLine = Math.Clamp(endLine, 0, Count - 1);
        if (startLine == endLine)
        {
            var text = Row(startLine).Text;
            var from = Math.Clamp(startColumn, 0, text.Length);
            return text[from..Math.Clamp(endColumn, from, text.Length)];
        }

        var builder = new StringBuilder();
        var first = Row(startLine).Text;
        builder.Append(first[Math.Clamp(startColumn, 0, first.Length)..]);
        for (var line = startLine + 1; line < endLine; line++)
        {
            builder.Append('\n').Append(Row(line).Text);
        }

        var last = Row(endLine).Text;
        return builder.Append('\n').Append(last[..Math.Clamp(endColumn, 0, last.Length)]).ToString();
    }
}
