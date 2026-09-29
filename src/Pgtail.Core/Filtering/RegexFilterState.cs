namespace Pgtail.Filtering;

/// <summary>
/// The regex filters and highlights of a session.
/// </summary>
public sealed class RegexFilterState
{
    /// <summary>
    /// Include filters, of which a line must match one.
    /// </summary>
    public List<RegexFilter> Includes { get; private set; } = [];

    /// <summary>
    /// Exclude filters, any match of which hides a line.
    /// </summary>
    public List<RegexFilter> Excludes { get; private set; } = [];

    /// <summary>
    /// AND filters, all of which a line must match.
    /// </summary>
    public List<RegexFilter> Ands { get; private set; } = [];

    /// <summary>
    /// Highlight patterns.
    /// </summary>
    public List<RegexHighlight> Highlights { get; private set; } = [];

    /// <summary>
    /// Whether any filter is set.
    /// </summary>
    public bool HasFilters => Includes.Count > 0 || Excludes.Count > 0 || Ands.Count > 0;

    /// <summary>
    /// Whether any highlight is set.
    /// </summary>
    public bool HasHighlights => Highlights.Count > 0;

    /// <summary>
    /// A copy that can change without affecting this state.
    /// </summary>
    /// <returns>The copy.</returns>
    public RegexFilterState Clone() => new()
    {
        Includes = [.. Includes],
        Excludes = [.. Excludes],
        Ands = [.. Ands],
        Highlights = [.. Highlights],
    };

    /// <summary>
    /// Removes every filter, keeping the highlights.
    /// </summary>
    public void ClearFilters()
    {
        Includes.Clear();
        Excludes.Clear();
        Ands.Clear();
    }

    /// <summary>
    /// Removes every highlight.
    /// </summary>
    public void ClearHighlights() => Highlights.Clear();

    /// <summary>
    /// Adds a filter to the list its type belongs to.
    /// </summary>
    /// <param name="filter">The filter.</param>
    public void Add(RegexFilter filter)
    {
        ArgumentNullException.ThrowIfNull(filter);
        switch (filter.Type)
        {
            case FilterType.Include:
                Includes.Add(filter);
                break;
            case FilterType.Exclude:
                Excludes.Add(filter);
                break;
            default:
                Ands.Add(filter);
                break;
        }
    }

    /// <summary>
    /// Replaces the include filters with one filter.
    /// </summary>
    /// <param name="filter">The filter.</param>
    public void SetInclude(RegexFilter filter)
    {
        ArgumentNullException.ThrowIfNull(filter);
        Includes = [filter];
    }

    /// <summary>
    /// Whether a line passes the filters.
    /// </summary>
    /// <remarks>
    /// With include filters, one must match. No exclude filter may match. Every AND filter must match.
    /// </remarks>
    /// <param name="text">The line.</param>
    /// <returns>True to show the line.</returns>
    public bool ShouldShow(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (Includes.Count > 0 && !Includes.Any(filter => filter.Matches(text)))
        {
            return false;
        }

        if (Excludes.Any(filter => filter.Matches(text)))
        {
            return false;
        }

        return Ands.Count == 0 || Ands.All(filter => filter.Matches(text));
    }
}
