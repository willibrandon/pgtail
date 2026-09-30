namespace Pgtail.Highlighting;

/// <summary>
/// Finds every occurrence of many keywords in one pass over a text.
/// </summary>
/// <remarks>
/// Occurrences are reported in the order they end; where several end at the same character, the longest comes first.
/// </remarks>
public sealed class AhoCorasick
{
    private readonly List<Dictionary<char, int>> _next = [new()];
    private readonly List<int> _fail = [0];
    private readonly List<int> _keyword = [-1];
    private readonly List<int> _output = [-1];
    private readonly List<string> _keywords = [];

    /// <summary>
    /// Builds a matcher.
    /// </summary>
    /// <param name="keywords">The keywords, as they must appear in the searched text.</param>
    public AhoCorasick(IEnumerable<string> keywords)
    {
        ArgumentNullException.ThrowIfNull(keywords);
        foreach (string keyword in keywords.Where(keyword => keyword.Length > 0))
        {
            Add(keyword);
        }

        Link();
    }

    /// <summary>
    /// Finds every occurrence.
    /// </summary>
    /// <param name="text">The text to search.</param>
    /// <returns>The index of each keyword found and the position just past it.</returns>
    public IEnumerable<(int Keyword, int End)> Find(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        int state = 0;
        for (int i = 0; i < text.Length; i++)
        {
            char c = text[i];
            while (state != 0 && !_next[state].ContainsKey(c))
            {
                state = _fail[state];
            }

            state = _next[state].TryGetValue(c, out int target) ? target : 0;
            for (int node = _keyword[state] >= 0 ? state : _output[state]; node > 0; node = _output[node])
            {
                yield return (_keyword[node], i + 1);
            }
        }
    }

    /// <summary>
    /// The keyword at an index.
    /// </summary>
    /// <param name="index">The index reported by <see cref="Find"/>.</param>
    /// <returns>The keyword.</returns>
    public string Keyword(int index) => _keywords[index];

    private void Add(string keyword)
    {
        int state = 0;
        foreach (char c in keyword)
        {
            if (!_next[state].TryGetValue(c, out int target))
            {
                target = _next.Count;
                _next.Add([]);
                _fail.Add(0);
                _keyword.Add(-1);
                _output.Add(-1);
                _next[state][c] = target;
            }

            state = target;
        }

        if (_keyword[state] < 0)
        {
            _keyword[state] = _keywords.Count;
            _keywords.Add(keyword);
        }
    }

    private void Link()
    {
        var queue = new Queue<int>();
        foreach (int child in _next[0].Values)
        {
            _fail[child] = 0;
            queue.Enqueue(child);
        }

        while (queue.Count > 0)
        {
            int state = queue.Dequeue();
            foreach ((char c, int child) in _next[state])
            {
                int fail = _fail[state];
                while (fail != 0 && !_next[fail].ContainsKey(c))
                {
                    fail = _fail[fail];
                }

                _fail[child] = _next[fail].TryGetValue(c, out int target) && target != child ? target : 0;
                int suffix = _fail[child];
                _output[child] = _keyword[suffix] >= 0 ? suffix : _output[suffix];
                queue.Enqueue(child);
            }
        }
    }
}
