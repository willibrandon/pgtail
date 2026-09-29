using System.Text;
using Pgtail.Styling;

namespace Pgtail.Rendering;

/// <summary>
/// Writes styled text as ANSI escape sequences for plain terminal output.
/// </summary>
internal static class AnsiText
{
    /// <summary>
    /// Renders styled text, resetting after every styled run.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="color">False to drop colors and keep attributes.</param>
    /// <param name="styled">False to write the plain text only, as when output is redirected.</param>
    /// <returns>The rendered text.</returns>
    public static string Render(StyledText text, bool color, bool styled = true)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (!styled)
        {
            return text.PlainText;
        }

        var builder = new StringBuilder();
        foreach (var span in text.Spans)
        {
            var sgr = Sgr(span.Style, color);
            if (sgr.Length == 0)
            {
                builder.Append(span.Text);
                continue;
            }

            // Styles end before each newline so a pager or the next prompt never inherits them.
            var lines = span.Text.Split('\n');
            for (var i = 0; i < lines.Length; i++)
            {
                if (i > 0)
                {
                    builder.Append('\n');
                }

                if (lines[i].Length > 0)
                {
                    builder.Append("\e[").Append(sgr).Append('m').Append(lines[i]).Append("\e[0m");
                }
            }
        }

        return builder.ToString();
    }

    /// <summary>
    /// The SGR parameters for a style.
    /// </summary>
    /// <param name="style">The style.</param>
    /// <param name="color">False to leave colors out.</param>
    /// <returns>The parameters joined by semicolons, empty for a plain style.</returns>
    public static string Sgr(TextStyle style, bool color)
    {
        var parts = new List<string>();
        var attributes = style.Attributes;
        (TextAttributes Flag, string Code)[] codes =
        [
            (TextAttributes.Bold, "1"),
            (TextAttributes.Dim, "2"),
            (TextAttributes.Italic, "3"),
            (TextAttributes.Underline, "4"),
            (TextAttributes.Blink, "5"),
            (TextAttributes.Reverse, "7"),
            (TextAttributes.Hidden, "8"),
            (TextAttributes.Strikethrough, "9"),
            (TextAttributes.Overline, "53"),
        ];
        foreach (var (flag, code) in codes)
        {
            if (attributes.HasFlag(flag))
            {
                parts.Add(code);
            }
        }

        if (color && style.Foreground is { } foreground)
        {
            parts.Add(foreground.ToSgr(background: false));
        }

        if (color && style.Background is { } background)
        {
            parts.Add(background.ToSgr(background: true));
        }

        return string.Join(';', parts);
    }
}
