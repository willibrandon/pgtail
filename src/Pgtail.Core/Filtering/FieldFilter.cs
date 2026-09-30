using System.Globalization;
using Pgtail.Parsing;

namespace Pgtail.Filtering;

/// <summary>
/// One field condition, such as <c>database=prod</c>.
/// </summary>
/// <param name="Field">The canonical field name.</param>
/// <param name="Value">The value to match, ignoring case.</param>
public sealed record FieldFilter(string Field, string Value)
{
    /// <summary>
    /// Whether an entry's field equals the value.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>True on a match; an entry without the field never matches.</returns>
    public bool Matches(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (FieldNames.EntryField(Field) is not { } name || entry.GetField(name) is not { } value)
        {
            return false;
        }

        return value is string text
            ? string.Equals(text.ToLowerInvariant(), Value.ToLowerInvariant(), StringComparison.Ordinal)
            : Convert.ToString(value, CultureInfo.InvariantCulture) == Value;
    }
}
