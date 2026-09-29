using Hex1b.Documents;
using Hex1b.Theming;

namespace Pgtail.Editing;

/// <summary>
/// Colors TOML in the built-in editor: comments, table headers, keys, strings, numbers, and booleans.
/// </summary>
internal sealed class TomlDecorationProvider : ITextDecorationProvider
{
    private static readonly TextDecoration Comment = new() { Foreground = Hex1bColor.FromBright(0, 128, 128, 128) };
    private static readonly TextDecoration Header = new() { Foreground = Hex1bColor.FromStandard(6, 0, 205, 205), Bold = true };
    private static readonly TextDecoration Key = new() { Foreground = Hex1bColor.FromStandard(6, 0, 205, 205) };
    private static readonly TextDecoration String = new() { Foreground = Hex1bColor.FromStandard(2, 0, 205, 0) };
    private static readonly TextDecoration Number = new() { Foreground = Hex1bColor.FromStandard(5, 205, 0, 205) };
    private static readonly TextDecoration Boolean = new() { Foreground = Hex1bColor.FromStandard(3, 205, 205, 0) };

    /// <inheritdoc/>
    public IReadOnlyList<TextDecorationSpan> GetDecorations(int startLine, int endLine, IHex1bDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);
        var spans = new List<TextDecorationSpan>();
        for (var line = Math.Max(1, startLine); line <= Math.Min(endLine, document.LineCount); line++)
        {
            Decorate(line, document.GetLineText(line), spans);
        }

        return spans;
    }

    private static void Decorate(int line, string text, List<TextDecorationSpan> spans)
    {
        var index = 0;
        while (index < text.Length && char.IsWhiteSpace(text[index]))
        {
            index++;
        }

        if (index >= text.Length)
        {
            return;
        }

        if (text[index] == '[')
        {
            var comment = FindComment(text, index);
            Add(spans, line, index, comment, Header);
            Add(spans, line, comment, text.Length, Comment);
            return;
        }

        if (text[index] == '#')
        {
            Add(spans, line, index, text.Length, Comment);
            return;
        }

        var equals = text.IndexOf('=', index);
        if (equals < 0)
        {
            return;
        }

        Add(spans, line, index, equals, Key);
        var position = equals + 1;
        while (position < text.Length)
        {
            var current = text[position];
            if (current is '"' or '\'')
            {
                var end = StringEnd(text, position);
                Add(spans, line, position, end, String);
                position = end;
            }
            else if (current == '#')
            {
                Add(spans, line, position, text.Length, Comment);
                return;
            }
            else if (char.IsDigit(current) || (current is '-' or '+' && position + 1 < text.Length && char.IsDigit(text[position + 1])))
            {
                var end = position + 1;
                while (end < text.Length && (char.IsLetterOrDigit(text[end]) || text[end] is '_' or '.' or ':' or '-' or '+'))
                {
                    end++;
                }

                Add(spans, line, position, end, Number);
                position = end;
            }
            else if (Word(text, position, "true") || Word(text, position, "false"))
            {
                var end = position + (text[position] == 't' ? 4 : 5);
                Add(spans, line, position, end, Boolean);
                position = end;
            }
            else
            {
                position++;
            }
        }
    }

    private static int FindComment(string text, int start)
    {
        var inString = '\0';
        for (var i = start; i < text.Length; i++)
        {
            if (inString != '\0')
            {
                inString = text[i] == inString ? '\0' : inString;
            }
            else if (text[i] is '"' or '\'')
            {
                inString = text[i];
            }
            else if (text[i] == '#')
            {
                return i;
            }
        }

        return text.Length;
    }

    private static int StringEnd(string text, int start)
    {
        var quote = text[start];
        for (var i = start + 1; i < text.Length; i++)
        {
            if (quote == '"' && text[i] == '\\')
            {
                i++;
                continue;
            }

            if (text[i] == quote)
            {
                return i + 1;
            }
        }

        return text.Length;
    }

    private static bool Word(string text, int position, string word) =>
        string.CompareOrdinal(text, position, word, 0, word.Length) == 0
        && (position + word.Length == text.Length || !char.IsLetterOrDigit(text[position + word.Length]));

    private static void Add(List<TextDecorationSpan> spans, int line, int start, int end, TextDecoration decoration)
    {
        if (end > start)
        {
            spans.Add(new TextDecorationSpan(new DocumentPosition(line, start + 1), new DocumentPosition(line, end + 1), decoration));
        }
    }
}
