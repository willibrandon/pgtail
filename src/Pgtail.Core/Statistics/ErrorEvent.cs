using Pgtail.Parsing;

namespace Pgtail.Statistics;

/// <summary>
/// An error or warning seen in the log.
/// </summary>
/// <param name="Timestamp">When it was logged, or when it was read if the entry had no time.</param>
/// <param name="Level">The severity.</param>
/// <param name="SqlState">The SQLSTATE code, when the log carries one.</param>
/// <param name="Message">The first 200 characters of the message.</param>
/// <param name="Pid">The backend process ID.</param>
/// <param name="Database">The database name.</param>
/// <param name="User">The user name.</param>
public sealed record ErrorEvent(
    DateTime Timestamp,
    LogLevel Level,
    string? SqlState,
    string Message,
    int? Pid,
    string? Database,
    string? User)
{
    /// <summary>
    /// Records an entry.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The event.</returns>
    public static ErrorEvent FromEntry(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        string message = entry.Message.Length > 200 ? entry.Message[..200] : entry.Message;
        return new ErrorEvent(entry.Timestamp ?? LocalNow(), entry.Level, entry.SqlState, message, entry.Pid, entry.DatabaseName,
            entry.UserName);
    }

    /// <summary>
    /// The current local time without a zone, the way entries without a zone are stored.
    /// </summary>
    /// <returns>The time.</returns>
    public static DateTime LocalNow() => DateTime.SpecifyKind(DateTime.Now, DateTimeKind.Unspecified);
}
