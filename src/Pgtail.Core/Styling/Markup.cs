using System.Text;

namespace Pgtail.Styling;

/// <summary>
/// Builds styled text from markup such as <c>[bold yellow]Warning:[/] message</c>.
/// </summary>
/// <remarks>
/// A tag opens a style that lasts until its closing tag, <c>[/style]</c>, or until <c>[/]</c> closes the latest one.
/// Styles nest. A tag starts with a letter, <c>#</c>, or <c>/</c>, so text such as <c>[12345]</c> stays literal, and
/// <c>\[</c> writes a bracket. Use <see cref="Escape"/> for text that must never be read as markup.
/// </remarks>
public static class Markup
{
    /// <summary>
    /// Parses markup.
    /// </summary>
    /// <param name="markup">The markup.</param>
    /// <returns>The styled text.</returns>
    /// <exception cref="FormatException">A tag names an unknown style or closes a tag that is not open.</exception>
    public static StyledText Parse(string markup)
    {
        ArgumentNullException.ThrowIfNull(markup);
        var result = new StyledText();
        var stack = new List<(string Tag, TextStyle Style)>();
        var text = new StringBuilder();
        TextStyle Current() => stack.Count == 0 ? TextStyle.Plain : stack[^1].Style;
        void Flush()
        {
            result.Append(text.ToString(), Current());
            text.Clear();
        }

        for (int i = 0; i < markup.Length; i++)
        {
            char c = markup[i];
            if (c == '\\' && i + 1 < markup.Length && markup[i + 1] == '[')
            {
                text.Append('[');
                i++;
                continue;
            }

            int close = c == '[' ? markup.IndexOf(']', i + 1) : -1;
            if (close < 0 || close == i + 1 || !IsTagStart(markup[i + 1]) || markup.AsSpan(i + 1, close - i - 1).Contains('['))
            {
                text.Append(c);
                continue;
            }

            Flush();
            string tag = markup[(i + 1)..close];
            if (tag.StartsWith('/'))
            {
                string name = tag[1..].Trim();
                if (stack.Count == 0)
                {
                    throw new FormatException($"Closing tag '[{tag}]' has nothing to close");
                }

                int index = name.Length == 0 ? stack.Count - 1 : stack.FindLastIndex(entry => entry.Tag == name);
                if (index < 0)
                {
                    throw new FormatException($"Closing tag '[{tag}]' does not match any open tag");
                }

                stack.RemoveAt(index);
            }
            else
            {
                stack.Add((tag.Trim(), Current().Then(StyleParser.Parse(tag))));
            }

            i = close;
        }

        Flush();
        return result;
    }

    /// <summary>
    /// Escapes text so markup reads it literally.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The escaped text.</returns>
    public static string Escape(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return text.Replace("[", "\\[", StringComparison.Ordinal);
    }

    private static bool IsTagStart(char c) => c is (>= 'a' and <= 'z') or (>= 'A' and <= 'Z') or '#' or '/' or '@';
}
