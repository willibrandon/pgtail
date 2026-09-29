namespace Pgtail.Highlighting;

/// <summary>
/// Styles keywords and phrases, matched together in one pass.
/// </summary>
public sealed class KeywordHighlighter : IHighlighter
{
    private readonly bool _caseSensitive;
    private readonly bool _wordBoundary;
    private readonly string[] _styles;
    private readonly Lazy<AhoCorasick> _matcher;

    /// <summary>
    /// Creates a highlighter.
    /// </summary>
    /// <param name="name">The unique name.</param>
    /// <param name="priority">The processing order.</param>
    /// <param name="description">A short description.</param>
    /// <param name="keywords">Each keyword with its style.</param>
    /// <param name="caseSensitive">True to match case exactly.</param>
    /// <param name="wordBoundary">True to match only whole words.</param>
    public KeywordHighlighter(
        string name,
        int priority,
        string description,
        IReadOnlyList<(string Keyword, string Style)> keywords,
        bool caseSensitive = false,
        bool wordBoundary = true)
    {
        ArgumentNullException.ThrowIfNull(keywords);
        Name = name;
        Priority = priority;
        Description = description;
        _caseSensitive = caseSensitive;
        _wordBoundary = wordBoundary;
        _styles = [.. keywords.Select(pair => pair.Style)];
        var patterns = keywords.Select(pair => caseSensitive ? pair.Keyword : pair.Keyword.ToLowerInvariant()).ToList();
        _matcher = new Lazy<AhoCorasick>(() => new AhoCorasick(patterns));
        KeywordCount = keywords.Count;
        StyleOf = patterns.Select((pattern, index) => (pattern, index))
            .GroupBy(pair => pair.pattern, StringComparer.Ordinal)
            .ToDictionary(group => group.Key, group => _styles[group.Last().index], StringComparer.Ordinal);
    }

    /// <inheritdoc />
    public string Name { get; }

    /// <inheritdoc />
    public int Priority { get; }

    /// <inheritdoc />
    public string Description { get; }

    /// <summary>
    /// The number of keywords.
    /// </summary>
    public int KeywordCount { get; }

    private Dictionary<string, string> StyleOf { get; }

    /// <inheritdoc />
    public IEnumerable<HighlightMatch> FindMatches(string text)
    {
        if (text.Length == 0)
        {
            yield break;
        }

        var search = _caseSensitive ? text : text.ToLowerInvariant();
        var matcher = _matcher.Value;
        foreach (var (keyword, end) in matcher.Find(search))
        {
            var word = matcher.Keyword(keyword);
            var start = end - word.Length;
            if (_wordBoundary && ((start > 0 && char.IsLetterOrDigit(search[start - 1]))
                || (end < search.Length && char.IsLetterOrDigit(search[end]))))
            {
                continue;
            }

            yield return new HighlightMatch(start, end, StyleOf[word]);
        }
    }
}
