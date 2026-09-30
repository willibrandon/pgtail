using System.Collections.Frozen;

namespace Pgtail.Display;

/// <summary>
/// The fields <c>display fields</c> accepts and the labels full mode shows.
/// </summary>
public static class DisplayFields
{
    /// <summary>
    /// The field names accepted by <c>display fields</c>, sorted.
    /// </summary>
    public static IReadOnlyList<string> Valid { get; } =
    [
        "application", "backend_type", "command_tag", "context", "database", "detail", "hint", "level", "location",
        "message", "pid", "query", "session_id", "sql_state", "timestamp", "user",
    ];

    /// <summary>
    /// The fields full mode lists under the first line, with their labels, in order.
    /// </summary>
    public static IReadOnlyList<(string Field, string Label)> Secondary { get; } =
    [
        ("application_name", "Application"),
        ("database_name", "Database"),
        ("user_name", "User"),
        ("query", "Query"),
        ("detail", "Detail"),
        ("hint", "Hint"),
        ("context", "Context"),
        ("location", "Location"),
        ("backend_type", "Backend"),
        ("session_id", "Session"),
    ];

    private static readonly FrozenSet<string> s_validSet = Valid.ToFrozenSet(StringComparer.Ordinal);

    /// <summary>
    /// Whether a name is accepted by <c>display fields</c>.
    /// </summary>
    /// <param name="name">The field name.</param>
    /// <returns>True when it is valid.</returns>
    public static bool IsValid(string name) => s_validSet.Contains(name);
}
