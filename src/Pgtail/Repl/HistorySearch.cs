namespace Pgtail.Repl;

/// <summary>
/// A reverse incremental search through the REPL's history, as Ctrl+R starts in a shell.
/// </summary>
/// <remarks>
/// While searching, the line being edited holds the search text, and the newest earlier command containing it is the
/// match; Ctrl+R again moves to the next older one.
/// </remarks>
/// <param name="saved">The line that was being edited when the search started.</param>
internal sealed class HistorySearch(string saved)
{
    private int _skip;

    /// <summary>
    /// The line that was being edited when the search started, restored when the search is cancelled.
    /// </summary>
    public string Saved { get; } = saved;

    /// <summary>
    /// The command found, or null when none contains the search text.
    /// </summary>
    public string? Match { get; private set; }

    /// <summary>
    /// Finds the newest command containing the search text, after the text changed.
    /// </summary>
    /// <param name="history">The history, oldest first.</param>
    /// <param name="query">The search text.</param>
    public void Update(IReadOnlyList<string> history, string query)
    {
        ArgumentNullException.ThrowIfNull(history);
        _skip = 0;
        Match = Find(history, query, 0);
    }

    /// <summary>
    /// Moves to the next older command containing the search text, keeping the current one when there is none.
    /// </summary>
    /// <param name="history">The history, oldest first.</param>
    /// <param name="query">The search text.</param>
    public void Older(IReadOnlyList<string> history, string query)
    {
        ArgumentNullException.ThrowIfNull(history);
        if (Find(history, query, _skip + 1) is { } older)
        {
            _skip++;
            Match = older;
        }
    }

    private static string? Find(IReadOnlyList<string> history, string query, int skip)
    {
        if (query.Length == 0)
        {
            return null;
        }

        var seen = new HashSet<string>(StringComparer.Ordinal);
        for (var index = history.Count - 1; index >= 0; index--)
        {
            var entry = history[index];
            if (entry.Contains(query, StringComparison.Ordinal) && seen.Add(entry) && skip-- == 0)
            {
                return entry;
            }
        }

        return null;
    }
}
