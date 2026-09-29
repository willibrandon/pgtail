using Scout.Text.Regex;

namespace Pgtail.Matching;

/// <summary>
/// A regular expression over log text, matched by Scout's byte-oriented, linear-time engine.
/// </summary>
/// <remarks>
/// Patterns use ripgrep's regular expression syntax. Matching takes time proportional to the text, however the pattern
/// is written, so a pattern typed by a user can never stall the tail.
/// </remarks>
public sealed class LogPattern
{
    private LogPattern(string pattern, bool caseSensitive, ByteRegex regex)
    {
        Pattern = pattern;
        CaseSensitive = caseSensitive;
        Regex = regex;
    }

    /// <summary>
    /// The pattern as written.
    /// </summary>
    public string Pattern { get; }

    /// <summary>
    /// Whether the pattern matches case.
    /// </summary>
    public bool CaseSensitive { get; }

    /// <summary>
    /// The compiled expression.
    /// </summary>
    public ByteRegex Regex { get; }

    /// <summary>
    /// Compiles a pattern.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="caseSensitive">False to ignore case, including non-ASCII letters.</param>
    /// <returns>The compiled pattern.</returns>
    /// <exception cref="FormatException">The pattern is not a valid regular expression.</exception>
    public static LogPattern Compile(string pattern, bool caseSensitive = true)
    {
        ArgumentNullException.ThrowIfNull(pattern);
        ByteRegex regex;
        try
        {
            // The pattern is compiled as written first, so a syntax error reports offsets into what the user typed.
            regex = ByteRegex.Compile(pattern);
        }
        catch (ByteRegexParseException exception)
        {
            throw new FormatException(exception.Message, exception);
        }

        return new LogPattern(pattern, caseSensitive, caseSensitive ? regex : ByteRegex.Compile("(?i)" + pattern));
    }

    /// <summary>
    /// Compiles a pattern, reporting a syntax error as a message instead of an exception.
    /// </summary>
    /// <param name="pattern">The pattern.</param>
    /// <param name="caseSensitive">False to ignore case.</param>
    /// <param name="compiled">The compiled pattern, when valid.</param>
    /// <param name="error">Why the pattern is invalid.</param>
    /// <returns>True when the pattern is valid.</returns>
    public static bool TryCompile(string pattern, bool caseSensitive, out LogPattern compiled, out string error)
    {
        try
        {
            compiled = Compile(pattern, caseSensitive);
            error = "";
            return true;
        }
        catch (FormatException exception)
        {
            compiled = null!;
            error = exception.Message;
            return false;
        }
    }

    /// <summary>
    /// Whether the pattern occurs in UTF-8 text.
    /// </summary>
    /// <param name="utf8">The text.</param>
    /// <returns>True on a match.</returns>
    public bool IsMatch(ReadOnlySpan<byte> utf8) => Regex.IsMatch(utf8);

    /// <summary>
    /// Whether the pattern occurs in a string.
    /// </summary>
    /// <param name="text">The string.</param>
    /// <returns>True on a match.</returns>
    public bool IsMatch(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        using var utf8 = new Utf8Text(text);
        return Regex.IsMatch(utf8.Bytes);
    }

    /// <summary>
    /// Whether the pattern matches the empty string at its start, which makes it unusable for highlighting.
    /// </summary>
    /// <returns>True when an empty text matches.</returns>
    public bool MatchesEmpty() => Regex.Find([]) is { Start: 0 };

    /// <summary>
    /// The character ranges of every match.
    /// </summary>
    /// <param name="text">The encoded text.</param>
    /// <returns>The ranges, in order.</returns>
    public IReadOnlyList<(int Start, int End)> FindSpans(Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return Spans(Regex, text);
    }

    /// <summary>
    /// The character ranges of every match of an expression.
    /// </summary>
    /// <param name="regex">The expression.</param>
    /// <param name="text">The encoded text.</param>
    /// <returns>The ranges, in order.</returns>
    public static List<(int Start, int End)> Spans(ByteRegex regex, Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(regex);
        ArgumentNullException.ThrowIfNull(text);
        var state = new List<(int, int)>();
        regex.ForEachMatch(text.Bytes, ref state, static (_, match, ref list) =>
        {
            list.Add((match.Start, match.End));
            return true;
        });

        for (var i = 0; i < state.Count; i++)
        {
            state[i] = (text.ToCharOffset(state[i].Item1), text.ToCharOffset(state[i].Item2));
        }

        return state;
    }

    /// <summary>
    /// Every match with its capture groups, as character ranges.
    /// </summary>
    /// <param name="regex">The expression.</param>
    /// <param name="text">The encoded text.</param>
    /// <returns>For each match, the range of every group by index, null where a group did not take part.</returns>
    public static List<(int Start, int End)?[]> Captures(ByteRegex regex, Utf8Text text)
    {
        ArgumentNullException.ThrowIfNull(regex);
        ArgumentNullException.ThrowIfNull(text);
        var results = new List<(int Start, int End)?[]>();
        var bytes = text.Bytes;
        var position = 0;
        while (position <= bytes.Length && regex.FindCaptures(bytes, position) is { } captures)
        {
            var groups = new (int Start, int End)?[captures.GroupCount];
            for (var i = 0; i < groups.Length; i++)
            {
                if (captures.GetGroup(i) is { } group)
                {
                    groups[i] = (text.ToCharOffset(group.Start), text.ToCharOffset(group.End));
                }
            }

            results.Add(groups);
            var match = captures.Match;
            position = match.Length == 0 ? NextBoundary(bytes, match.End) : match.End;
        }

        return results;
    }

    private static int NextBoundary(ReadOnlySpan<byte> bytes, int position)
    {
        position++;
        while (position < bytes.Length && (bytes[position] & 0xC0) == 0x80)
        {
            position++;
        }

        return position;
    }
}
