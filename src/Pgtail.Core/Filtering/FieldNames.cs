using System.Collections.Frozen;

namespace Pgtail.Filtering;

/// <summary>
/// The structured fields that can be filtered, with their aliases.
/// </summary>
public static class FieldNames
{
    /// <summary>
    /// Maps every accepted name to its canonical field.
    /// </summary>
    public static IReadOnlyDictionary<string, string> Aliases { get; } = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["app"] = "application",
        ["application"] = "application",
        ["db"] = "database",
        ["database"] = "database",
        ["user"] = "user",
        ["pid"] = "pid",
        ["backend"] = "backend",
        ["host"] = "host",
        ["ip"] = "host",
        ["client"] = "host",
        ["connection_from"] = "host",
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

    /// <summary>
    /// Maps each canonical field to the entry field it reads, in display order.
    /// </summary>
    public static IReadOnlyList<(string Field, string EntryField)> Attributes { get; } =
    [
        ("application", "application_name"),
        ("database", "database_name"),
        ("user", "user_name"),
        ("pid", "pid"),
        ("backend", "backend_type"),
        ("host", "connection_from"),
    ];

    /// <summary>
    /// Resolves a field name or alias, ignoring case, to its canonical name.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>The canonical name.</returns>
    /// <exception cref="ArgumentException">The name is not a filterable field.</exception>
    public static string Resolve(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        if (Aliases.TryGetValue(name.ToLowerInvariant(), out var canonical))
        {
            return canonical;
        }

        var valid = string.Join(", ", Aliases.Keys.Order(StringComparer.Ordinal));
        throw new ArgumentException($"Unknown field: {name}. Valid fields: {valid}");
    }

    /// <summary>
    /// The entry field a canonical field reads.
    /// </summary>
    /// <param name="field">The canonical field.</param>
    /// <returns>The entry field name, or null when the field is unknown.</returns>
    public static string? EntryField(string field) =>
        Attributes.FirstOrDefault(pair => pair.Field == field).EntryField;
}
