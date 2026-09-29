using System.Text;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// One row of the tail log: its plain text and the styled ranges within it.
/// </summary>
/// <param name="Text">The text, with tabs expanded.</param>
/// <param name="Styles">The styled character ranges, in order.</param>
internal sealed record TailLine(string Text, IReadOnlyList<(int Start, int End, TextStyle Style)> Styles)
{
    private const int TabWidth = 8;

    /// <summary>
    /// Splits styled text into rows at newlines, expanding tabs and dropping other control characters.
    /// </summary>
    /// <param name="text">The styled text.</param>
    /// <returns>The rows.</returns>
    public static List<TailLine> From(StyledText text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var lines = new List<TailLine>();
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

            lines.Add(new TailLine(builder.ToString(), styles));
        }

        return lines;
    }
}
