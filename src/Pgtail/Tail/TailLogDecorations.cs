using Hex1b;
using Hex1b.Documents;
using Hex1b.Theming;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// Colors the tail log's rows from their styled ranges.
/// </summary>
/// <remarks>
/// The editor draws foreground, background, bold, italic, and underline. Dim text without a color of its own is drawn
/// in grey, and reversed text swaps its colors, so the fixed tail styles read the same as in a terminal.
/// </remarks>
/// <param name="log">The log whose rows are colored.</param>
/// <param name="color">False to draw attributes only, for <c>NO_COLOR</c>.</param>
internal sealed class TailLogDecorations(TailLogDocument log, bool color) : ITextDecorationProvider
{
    private static readonly Hex1bColor Grey = Hex1bColor.FromBright(0, 128, 128, 128);
    private static readonly Hex1bColor Black = Hex1bColor.FromStandard(0, 0, 0, 0);

    /// <inheritdoc/>
    public IReadOnlyList<TextDecorationSpan> GetDecorations(int startLine, int endLine, IHex1bDocument document)
    {
        var spans = new List<TextDecorationSpan>();
        var lines = log.Lines;
        for (var line = Math.Max(1, startLine); line <= Math.Min(endLine, lines.Count); line++)
        {
            foreach (var (start, end, style) in lines[line - 1].Styles)
            {
                if (ToDecoration(style) is { } decoration)
                {
                    var from = new DocumentPosition(line, start + 1);
                    spans.Add(new TextDecorationSpan(from, new DocumentPosition(line, end + 1), decoration));
                }
            }
        }

        return spans;
    }

    private TextDecoration? ToDecoration(TextStyle style)
    {
        var attributes = style.Attributes;
        var foreground = color ? style.Foreground?.ToHex1b() : null;
        var background = color ? style.Background?.ToHex1b() : null;
        if (attributes.HasFlag(TextAttributes.Dim) && foreground is null && color)
        {
            foreground = Grey;
        }

        if (attributes.HasFlag(TextAttributes.Reverse) && color)
        {
            (foreground, background) = (background ?? Black, foreground ?? Grey);
        }

        var bold = attributes.HasFlag(TextAttributes.Bold) ? true : (bool?)null;
        var italic = attributes.HasFlag(TextAttributes.Italic) ? true : (bool?)null;
        UnderlineStyle? underline = attributes.HasFlag(TextAttributes.Underline) ? UnderlineStyle.Single : null;
        if (foreground is null && background is null && bold is null && italic is null && underline is null)
        {
            return null;
        }

        return new TextDecoration
        {
            Foreground = foreground,
            Background = background,
            Bold = bold,
            Italic = italic,
            UnderlineStyle = underline,
        };
    }
}
