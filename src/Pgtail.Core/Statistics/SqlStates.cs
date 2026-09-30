using System.Collections.Frozen;

namespace Pgtail.Statistics;

/// <summary>
/// Readable names for common SQLSTATE codes.
/// </summary>
public static class SqlStates
{
    /// <summary>
    /// The condition names of common SQLSTATE codes.
    /// </summary>
    public static IReadOnlyDictionary<string, string> Names { get; } = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["23502"] = "not_null_violation",
        ["23503"] = "foreign_key_violation",
        ["23505"] = "unique_violation",
        ["23514"] = "check_violation",
        ["23P01"] = "exclusion_violation",
        ["42501"] = "insufficient_privilege",
        ["42601"] = "syntax_error",
        ["42602"] = "invalid_name",
        ["42703"] = "undefined_column",
        ["42704"] = "undefined_object",
        ["42710"] = "duplicate_object",
        ["42P01"] = "undefined_table",
        ["42P02"] = "undefined_parameter",
        ["53100"] = "disk_full",
        ["53200"] = "out_of_memory",
        ["53300"] = "too_many_connections",
        ["57014"] = "query_canceled",
        ["57P01"] = "admin_shutdown",
        ["57P02"] = "crash_shutdown",
        ["57P03"] = "cannot_connect_now",
        ["58030"] = "io_error",
        ["40001"] = "serialization_failure",
        ["40P01"] = "deadlock_detected",
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

    /// <summary>
    /// The condition name of a code, such as <c>unique_violation</c> for <c>23505</c>.
    /// </summary>
    /// <param name="code">The code.</param>
    /// <returns>The name, or the code itself when it is not a common one.</returns>
    public static string GetName(string code)
    {
        ArgumentNullException.ThrowIfNull(code);
        return Names.TryGetValue(code, out string? name) ? name : code;
    }
}
