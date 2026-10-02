using System.Text;
using Hex1b;
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
    /// An empty row.
    /// </summary>
    public static TailLine Blank { get; } = new("", [], null, 0);

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

    /// <summary>
    /// The display width of the widest row text splits into, worked out without making the rows.
    /// </summary>
    /// <param name="text">The plain text, as formatted for the log.</param>
    /// <returns>The width in columns.</returns>
    public static int Widest(string text) => Widest(0, text);

    /// <summary>
    /// The display width of the widest row text splits into, its first row put after a number of ASCII characters.
    /// </summary>
    /// <param name="start">How many ASCII characters, with no tabs, come before the text on its first row.</param>
    /// <param name="text">The plain text, as formatted for the log.</param>
    /// <returns>The width in columns.</returns>
    public static int Widest(int start, string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        int widest = 0;
        ReadOnlySpan<char> rest = text;
        while (true)
        {
            int end = rest.IndexOf('\n');
            widest = Math.Max(widest, Width(start, end < 0 ? rest : rest[..end]));
            if (end < 0)
            {
                return widest;
            }

            start = 0;
            rest = rest[(end + 1)..];
        }
    }

    // The display width of one row's text after some ASCII characters, with tabs expanded and control characters left
    // out as Split does.
    private static int Width(int start, ReadOnlySpan<char> row)
    {
        if (Ascii.IsValid(row))
        {
            int column = start;
            foreach (char character in row)
            {
                column += character == '\t' ? TabWidth - (column % TabWidth) : char.IsControl(character) ? 0 : 1;
            }

            return column;
        }

        StringBuilder builder = new StringBuilder().Append(' ', start);
        AppendExpanded(builder, row);
        string expanded = builder.ToString();
        return GraphemeHelper.IndexToDisplayColumn(expanded, expanded.Length);
    }

    // Appends text with tabs expanded to the next multiple of TabWidth and control characters left out.
    private static void AppendExpanded(StringBuilder builder, ReadOnlySpan<char> text)
    {
        foreach (char character in text)
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
    }

    private static List<(string Text, IReadOnlyList<(int Start, int End, TextStyle Style)> Styles)> Split(StyledText text)
    {
        var rows = new List<(string, IReadOnlyList<(int, int, TextStyle)>)>();
        var builder = new StringBuilder();
        foreach (StyledText row in text.SplitLines())
        {
            _ = builder.Clear();
            var styles = new List<(int, int, TextStyle)>();
            foreach (StyledSpan span in row.Spans)
            {
                int start = builder.Length;
                AppendExpanded(builder, span.Text);

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
