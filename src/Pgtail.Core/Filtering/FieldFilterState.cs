using Pgtail.Parsing;

namespace Pgtail.Filtering;

/// <summary>
/// The field filters of a session, all of which an entry must match.
/// </summary>
public sealed class FieldFilterState
{
    private readonly Dictionary<string, FieldFilter> _filters = new(StringComparer.Ordinal);
    private readonly List<string> _order = [];

    /// <summary>
    /// Whether any filter is set.
    /// </summary>
    public bool IsActive => _filters.Count > 0;

    /// <summary>
    /// The filters in the order their fields were first set.
    /// </summary>
    public IReadOnlyList<FieldFilter> Filters => [.. _order.Select(name => _filters[name])];

    /// <summary>
    /// Sets the value a field must have, replacing an earlier value for the same field.
    /// </summary>
    /// <param name="field">The field name or alias.</param>
    /// <param name="value">The value.</param>
    /// <exception cref="ArgumentException">The field is not filterable.</exception>
    public void Add(string field, string value)
    {
        var canonical = FieldNames.Resolve(field);
        if (!_filters.ContainsKey(canonical))
        {
            _order.Add(canonical);
        }

        _filters[canonical] = new FieldFilter(canonical, value);
    }

    /// <summary>
    /// Removes the filter on a field.
    /// </summary>
    /// <param name="field">The field name or alias.</param>
    /// <returns>True when a filter was removed.</returns>
    public bool Remove(string field)
    {
        string canonical;
        try
        {
            canonical = FieldNames.Resolve(field);
        }
        catch (ArgumentException)
        {
            return false;
        }

        if (!_filters.Remove(canonical))
        {
            return false;
        }

        _order.Remove(canonical);
        return true;
    }

    /// <summary>
    /// Removes every filter.
    /// </summary>
    public void Clear()
    {
        _filters.Clear();
        _order.Clear();
    }

    /// <summary>
    /// Whether an entry matches every filter.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>True to keep the entry.</returns>
    public bool Matches(LogEntry entry) => _filters.Count == 0 || _filters.Values.All(filter => filter.Matches(entry));

    /// <summary>
    /// Describes the filters, such as <c>Field filters: application=myapp, database=prod</c>.
    /// </summary>
    /// <returns>The description, or <c>No field filters</c>.</returns>
    public string FormatStatus() => _filters.Count == 0
        ? "No field filters"
        : "Field filters: " + string.Join(", ", Filters.Select(filter => $"{filter.Field}={filter.Value}"));
}
