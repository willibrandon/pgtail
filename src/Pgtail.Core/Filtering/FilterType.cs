namespace Pgtail.Filtering;

/// <summary>
/// How a regex filter combines with the others.
/// </summary>
public enum FilterType
{
    /// <summary>
    /// A line must match at least one include filter.
    /// </summary>
    Include,

    /// <summary>
    /// A line matching an exclude filter is hidden.
    /// </summary>
    Exclude,

    /// <summary>
    /// A line must match every AND filter.
    /// </summary>
    And,
}
