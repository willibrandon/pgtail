using System.Text;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// One row of the tail log: plain text, with tabs expanded, and the styles over it.
/// </summary>
/// <remarks>
/// An entry's rows are made from a quick formatting, whose text is final, and get the entry's full highlighting the
/// first time one of them is drawn, so a log of thousands of entries appears at once and only the rows on screen are
/// highlighted.
/// </remarks>
internal sealed class TailLine
{
    private const int TabWidth = 8;
    private readonly IReadOnlyList<(int Start, int End, TextStyle Style)> _styles;
    private readonly Highlighting? _highlighting;
    private readonly int _row;

    private TailLine(string text, IReadOnlyList<(int Start, int End, TextStyle Style)> styles, Highlighting? highlighting, int row)
    {
        Text = text;
        _styles = styles;
        _highlighting = highlighting;
        _row = row;
    }

    /// <summary>
    /// The row's text.
    /// </summary>
    public string Text { get; }

    /// <summary>
    /// The styles over the row's text, highlighting it when that was put off.
    /// </summary>
    public IReadOnlyList<(int Start, int End, TextStyle Style)> Styles => _highlighting?.Styles(_row) ?? _styles;

    /// <summary>
    /// Splits styled text into rows.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The rows.</returns>
    public static List<TailLine> From(StyledText text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return [.. Split(text).Select(row => new TailLine(row.Text, row.Styles, null, 0))];
    }

    /// <summary>
    /// Splits an entry into rows from its quick formatting, putting off its full highlighting until a row is drawn.
    /// </summary>
    /// <param name="quick">The entry formatted without semantic highlighting, which has the same text.</param>
    /// <param name="full">Formats the entry with its highlighting.</param>
    /// <returns>The rows.</returns>
    public static List<TailLine> From(StyledText quick, Func<StyledText> full)
    {
        ArgumentNullException.ThrowIfNull(quick);
        ArgumentNullException.ThrowIfNull(full);
        var highlighting = new Highlighting(full);
        return [.. Split(quick).Select((row, index) => new TailLine(row.Text, row.Styles, highlighting, index))];
    }

    private static List<(string Text, IReadOnlyList<(int Start, int End, TextStyle Style)> Styles)> Split(StyledText text)
    {
        var rows = new List<(string, IReadOnlyList<(int, int, TextStyle)>)>();
        foreach (var row in text.SplitLines())
        {
            var builder = new StringBuilder();
            var styles = new List<(int, int, TextStyle)>();
            foreach (var span in row.Spans)
            {
                var start = builder.Length;
                foreach (var character in span.Text)
                {
                    if (character == '\t')
                    {
                        builder.Append(' ', TabWidth - (builder.Length % TabWidth));
                    }
                    else if (!char.IsControl(character))
                    {
                        builder.Append(character);
                    }
                }

                if (!span.Style.IsPlain && builder.Length > start)
                {
                    styles.Add((start, builder.Length, span.Style));
                }
            }

            rows.Add((builder.ToString(), styles));
        }

        return rows;
    }

    // An entry's full highlighting, worked out once for all its rows.
    private sealed class Highlighting(Func<StyledText> full)
    {
        private List<(string Text, IReadOnlyList<(int Start, int End, TextStyle Style)> Styles)>? _rows;

        /// <summary>
        /// The styles of one of the entry's rows.
        /// </summary>
        /// <param name="row">The row, counting from 0.</param>
        /// <returns>The styles, or null when the full formatting has fewer rows.</returns>
        public IReadOnlyList<(int Start, int End, TextStyle Style)>? Styles(int row)
        {
            _rows ??= Split(full());
            return row < _rows.Count ? _rows[row].Styles : null;
        }
    }
}
