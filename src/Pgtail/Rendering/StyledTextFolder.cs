using System.Text;
using Hex1b;
using Pgtail.Styling;

namespace Pgtail.Rendering;

/// <summary>
/// Breaks styled text into terminal rows.
/// </summary>
/// <remarks>
/// Newlines start a row, tabs expand to the next multiple of eight columns, other control characters are dropped,
/// and a row that would overflow the width continues on the next row, measured in grapheme display columns.
/// </remarks>
internal static class StyledTextFolder
{
    private const int TabWidth = 8;

    /// <summary>
    /// Folds styled text into rows no wider than a width.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="width">The width in columns, or zero or less to break only at newlines.</param>
    /// <returns>The rows, each a list of spans; empty text is one empty row.</returns>
    public static List<List<StyledSpan>> Fold(StyledText text, int width)
    {
        ArgumentNullException.ThrowIfNull(text);
        var rows = new List<List<StyledSpan>>();
        var row = new List<StyledSpan>();
        var run = new StringBuilder();
        TextStyle runStyle = TextStyle.Plain;
        int column = 0;

        void FlushRun()
        {
            if (run.Length > 0)
            {
                row.Add(new StyledSpan(run.ToString(), runStyle));
                run.Clear();
            }
        }

        void NewRow()
        {
            FlushRun();
            rows.Add(row);
            row = [];
            column = 0;
        }

        foreach (StyledSpan span in text.Spans)
        {
            if (run.Length > 0 && span.Style != runStyle)
            {
                FlushRun();
            }

            runStyle = span.Style;
            string value = span.Text;
            int index = 0;
            while (index < value.Length)
            {
                int next = GraphemeHelper.GetNextClusterBoundary(value, index);
                if (next <= index)
                {
                    next = index + 1;
                }

                string cluster = value[index..next];
                index = next;
                if (cluster == "\n" || cluster == "\r\n")
                {
                    NewRow();
                    continue;
                }

                if (cluster == "\t")
                {
                    int spaces = TabWidth - (column % TabWidth);
                    for (int i = 0; i < spaces; i++)
                    {
                        if (width > 0 && column >= width)
                        {
                            NewRow();
                            break;
                        }

                        run.Append(' ');
                        column++;
                    }

                    continue;
                }

                if (char.IsControl(cluster[0]))
                {
                    continue;
                }

                int clusterWidth = GraphemeHelper.GetClusterDisplayWidth(cluster);
                if (width > 0 && column + clusterWidth > width && column > 0)
                {
                    NewRow();
                }

                run.Append(cluster);
                column += clusterWidth;
            }
        }

        FlushRun();
        rows.Add(row);
        return rows;
    }

    /// <summary>
    /// The display width of a row.
    /// </summary>
    /// <param name="row">The row.</param>
    /// <returns>The width in columns.</returns>
    public static int Width(IReadOnlyList<StyledSpan> row)
    {
        ArgumentNullException.ThrowIfNull(row);
        int width = 0;
        foreach (StyledSpan span in row)
        {
            width += DisplayWidth.GetStringWidth(span.Text);
        }

        return width;
    }
}
