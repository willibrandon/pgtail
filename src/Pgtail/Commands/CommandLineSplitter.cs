using System.Text;

namespace Pgtail.Commands;

/// <summary>
/// Splits a command line into words the way a shell does, while keeping regular expressions intact.
/// </summary>
/// <remarks>
/// Whitespace separates words. Single quotes keep their contents literally; double quotes do too, except that
/// <c>\"</c> and <c>\\</c> stand for a quote and a backslash. A backslash outside quotes is kept, so patterns such
/// as <c>/user_\d+/</c> arrive as typed. A quote with no closing partner is an ordinary character, so
/// <c>filter /can't/</c> works.
/// </remarks>
internal static class CommandLineSplitter
{
    /// <summary>
    /// Splits a line into words.
    /// </summary>
    /// <param name="line">The line.</param>
    /// <returns>The words, in order.</returns>
    public static List<CommandToken> Split(string line)
    {
        ArgumentNullException.ThrowIfNull(line);
        var tokens = new List<CommandToken>();
        var builder = new StringBuilder();
        int index = 0;
        while (index < line.Length)
        {
            while (index < line.Length && char.IsWhiteSpace(line[index]))
            {
                index++;
            }

            if (index >= line.Length)
            {
                break;
            }

            int start = index;
            builder.Clear();
            while (index < line.Length && !char.IsWhiteSpace(line[index]))
            {
                char current = line[index];
                if (current is '\'' or '"' && FindClose(line, index) is var close && close > index)
                {
                    AppendQuoted(builder, line, index + 1, close, current == '"');
                    index = close + 1;
                    continue;
                }

                builder.Append(current);
                index++;
            }

            tokens.Add(new CommandToken(builder.ToString(), start, index));
        }

        return tokens;
    }

    private static int FindClose(string line, int open)
    {
        char quote = line[open];
        for (int i = open + 1; i < line.Length; i++)
        {
            if (quote == '"' && line[i] == '\\' && i + 1 < line.Length)
            {
                i++;
                continue;
            }

            if (line[i] == quote)
            {
                return i;
            }
        }

        return -1;
    }

    private static void AppendQuoted(StringBuilder builder, string line, int start, int end, bool escapes)
    {
        for (int i = start; i < end; i++)
        {
            if (escapes && line[i] == '\\' && i + 1 < end && line[i + 1] is '"' or '\\')
            {
                i++;
            }

            builder.Append(line[i]);
        }
    }
}
