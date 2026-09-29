namespace Pgtail.Tail;

/// <summary>
/// Rows of the tail log that belong together, such as one entry's, made the first time one of them is needed.
/// </summary>
/// <remarks>
/// A segment knows how many rows it has without making them, so a log of many entries costs little until it is drawn,
/// and made rows can be forgotten again and made once more when scrolled back to.
/// </remarks>
/// <param name="rowCount">How many rows the segment has.</param>
/// <param name="make">Makes the rows.</param>
internal sealed class TailSegment(int rowCount, Func<IReadOnlyList<TailLine>> make)
{
    private IReadOnlyList<TailLine>? _rows;

    /// <summary>
    /// How many rows the segment has.
    /// </summary>
    public int RowCount { get; } = rowCount;

    /// <summary>
    /// The log's number for the segment's first row, which stays the same as rows come and go around it.
    /// </summary>
    public long Start { get; set; }

    /// <summary>
    /// Whether the rows are made.
    /// </summary>
    public bool IsMade => _rows is not null;

    /// <summary>
    /// A segment of rows that are already made, such as a message's.
    /// </summary>
    /// <param name="rows">The rows.</param>
    /// <returns>The segment.</returns>
    public static TailSegment Of(IReadOnlyList<TailLine> rows)
    {
        ArgumentNullException.ThrowIfNull(rows);
        return new TailSegment(rows.Count, () => rows);
    }

    /// <summary>
    /// One of the segment's rows, making them all when none is made.
    /// </summary>
    /// <remarks>
    /// Rows made past the count are left out and missing ones are blank, so the log's row numbers always hold.
    /// </remarks>
    /// <param name="index">The row, counting from 0.</param>
    /// <returns>The row.</returns>
    public TailLine Row(int index)
    {
        if (_rows is null)
        {
            var made = make();
            _rows = made.Count == RowCount
                ? made
                : [.. made.Take(RowCount), .. Enumerable.Repeat(TailLine.Blank, RowCount - Math.Min(RowCount, made.Count))];
        }

        return _rows[index];
    }

    /// <summary>
    /// Lets the made rows go, to be made again when next needed.
    /// </summary>
    public void Forget() => _rows = null;
}
