using System.Collections.Frozen;

namespace Pgtail.Statistics;

/// <summary>
/// Readable names for common SQLSTATE codes and their classes.
/// </summary>
public static class SqlStates
{
    /// <summary>
    /// The class names of SQLSTATE codes, by their first two characters.
    /// </summary>
    public static IReadOnlyDictionary<string, string> Categories { get; } = new Dictionary<string, string>(StringComparer.Ordinal)
    {
        ["00"] = "Successful Completion",
        ["01"] = "Warning",
        ["02"] = "No Data",
        ["03"] = "SQL Statement Not Yet Complete",
        ["08"] = "Connection Exception",
        ["09"] = "Triggered Action Exception",
        ["0A"] = "Feature Not Supported",
        ["0B"] = "Invalid Transaction Initiation",
        ["0F"] = "Locator Exception",
        ["0L"] = "Invalid Grantor",
        ["0P"] = "Invalid Role Specification",
        ["0Z"] = "Diagnostics Exception",
        ["20"] = "Case Not Found",
        ["21"] = "Cardinality Violation",
        ["22"] = "Data Exception",
        ["23"] = "Integrity Constraint Violation",
        ["24"] = "Invalid Cursor State",
        ["25"] = "Invalid Transaction State",
        ["26"] = "Invalid SQL Statement Name",
        ["27"] = "Triggered Data Change Violation",
        ["28"] = "Invalid Authorization Specification",
        ["2B"] = "Dependent Privilege Descriptors Still Exist",
        ["2D"] = "Invalid Transaction Termination",
        ["2F"] = "SQL Routine Exception",
        ["34"] = "Invalid Cursor Name",
        ["38"] = "External Routine Exception",
        ["39"] = "External Routine Invocation Exception",
        ["3B"] = "Savepoint Exception",
        ["3D"] = "Invalid Catalog Name",
        ["3F"] = "Invalid Schema Name",
        ["40"] = "Transaction Rollback",
        ["42"] = "Syntax Error or Access Rule Violation",
        ["44"] = "WITH CHECK OPTION Violation",
        ["53"] = "Insufficient Resources",
        ["54"] = "Program Limit Exceeded",
        ["55"] = "Object Not In Prerequisite State",
        ["57"] = "Operator Intervention",
        ["58"] = "System Error",
        ["72"] = "Snapshot Failure",
        ["F0"] = "Configuration File Error",
        ["HV"] = "Foreign Data Wrapper Error",
        ["P0"] = "PL/pgSQL Error",
        ["XX"] = "Internal Error",
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

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
        return Names.TryGetValue(code, out var name) ? name : code;
    }
}
