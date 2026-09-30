namespace Pgtail.Statistics;

/// <summary>
/// Narrows connection events by database, user, and application.
/// </summary>
/// <param name="Database">The database name to match exactly, or null.</param>
/// <param name="User">The user name to match exactly, or null.</param>
/// <param name="Application">The application name to match exactly, or null.</param>
public sealed record ConnectionFilter(string? Database = null, string? User = null, string? Application = null)
{
    /// <summary>
    /// Whether no criterion is set.
    /// </summary>
    public bool IsEmpty => Database is null && User is null && Application is null;

    /// <summary>
    /// Whether an event matches every criterion that is set.
    /// </summary>
    /// <param name="item">The event.</param>
    /// <returns>True on a match.</returns>
    public bool Matches(ConnectionEvent item)
    {
        ArgumentNullException.ThrowIfNull(item);
        return Allows(Database, item.Database) && Allows(User, item.User) && Allows(Application, item.Application);
    }

    // A part of the filter that is not set allows every value.
    private static bool Allows(string? wanted, string? value) => wanted is null || value == wanted;
}
