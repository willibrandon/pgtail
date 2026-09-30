using Pgtail.Matching;
using Pgtail.Styling;

namespace Pgtail.Highlighting;

/// <summary>
/// Applies a set of highlighters to a message, the higher priority ones claiming their ranges first.
/// </summary>
/// <remarks>
/// Matches are taken in order of position and then priority; a match that overlaps a range already taken is dropped.
/// Highlighters named <c>sql_*</c> apply only inside the SQL <see cref="SqlDetector"/> finds. Text past
/// <see cref="MaxLength"/> is left unstyled.
/// </remarks>
public sealed class HighlighterChain
{
    private readonly IHighlighter[] _general;
    private readonly IHighlighter[] _sql;

    /// <summary>
    /// Creates a chain.
    /// </summary>
    /// <param name="highlighters">The highlighters.</param>
    /// <param name="maxLength">How many characters of each message to highlight.</param>
    /// <exception cref="ArgumentException">Two highlighters share a name.</exception>
    public HighlighterChain(IEnumerable<IHighlighter> highlighters, int maxLength = 10_240)
    {
        ArgumentNullException.ThrowIfNull(highlighters);
        var sorted = highlighters.OrderBy(highlighter => highlighter.Priority).ToList();
        IGrouping<string, IHighlighter>? duplicate = sorted.GroupBy(highlighter => highlighter.Name, StringComparer.Ordinal)
            .FirstOrDefault(group => group.Count() > 1);
        if (duplicate is not null)
        {
            throw new ArgumentException($"Highlighter '{duplicate.Key}' already registered", nameof(highlighters));
        }

        Highlighters = sorted;
        _general = [.. sorted.Where(highlighter => !highlighter.Name.StartsWith("sql_", StringComparison.Ordinal))];
        _sql = [.. sorted.Where(highlighter => highlighter.Name.StartsWith("sql_", StringComparison.Ordinal))];
        MaxLength = maxLength;
    }

    /// <summary>
    /// A chain with no highlighters, which leaves text as it is.
    /// </summary>
    public static HighlighterChain None { get; } = new([]);

    /// <summary>
    /// The highlighters by priority.
    /// </summary>
    public IReadOnlyList<IHighlighter> Highlighters { get; }

    /// <summary>
    /// How many characters of each message are highlighted.
    /// </summary>
    public int MaxLength { get; }

    /// <summary>
    /// Styles a message.
    /// </summary>
    /// <param name="text">The message.</param>
    /// <param name="theme">The theme that names the styles.</param>
    /// <returns>The styled message; unmatched text is plain.</returns>
    public StyledText Apply(string text, Theme theme)
    {
        ArgumentNullException.ThrowIfNull(text);
        ArgumentNullException.ThrowIfNull(theme);
        if (text.Length == 0 || Highlighters.Count == 0)
        {
            return new StyledText(text);
        }

        string process = text.Length > MaxLength ? text[..MaxLength] : text;
        using var encoded = new Utf8Text(process);
        List<(HighlightMatch Match, int Priority)> matches = Collect(encoded);
        var result = new StyledText();
        if (matches.Count > 0)
        {
            var tracker = new OccupancyTracker(process.Length);
            int position = 0;
            foreach ((HighlightMatch match, int _) in matches.OrderBy(pair => pair.Match.Start).ThenBy(pair => pair.Priority))
            {
                if (!tracker.IsAvailable(match.Start, match.End))
                {
                    continue;
                }

                tracker.MarkOccupied(match.Start, match.End);
                result.Append(process[position..match.Start]);
                result.Append(process[match.Start..match.End], theme.ResolveStyle(match.Style));
                position = match.End;
            }

            result.Append(process[position..]);
        }
        else
        {
            result.Append(process);
        }

        return result.Append(text[process.Length..]);
    }

    private List<(HighlightMatch Match, int Priority)> Collect(Utf8Text text)
    {
        var matches = new List<(HighlightMatch, int)>();
        foreach (IHighlighter highlighter in _general)
        {
            matches.AddRange(highlighter.FindMatches(text).Select(match => (match, highlighter.Priority)));
        }

        if (_sql.Length > 0 && SqlDetector.Detect(text) is { } detection)
        {
            int start = detection.Prefix.Length;
            int end = start + detection.Sql.Length;
            foreach (IHighlighter highlighter in _sql)
            {
                matches.AddRange(highlighter.FindMatches(text)
                    .Where(match => match.Start >= start && match.End <= end)
                    .Select(match => (match, highlighter.Priority)));
            }
        }

        return matches;
    }
}
