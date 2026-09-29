using System.Globalization;
using Pgtail.Parsing;

namespace Pgtail.Statistics;

/// <summary>
/// A connection, disconnection, or failed connection seen in the log.
/// </summary>
/// <param name="Timestamp">When it was logged, or when it was read if the entry had no time.</param>
/// <param name="Type">What happened.</param>
/// <param name="Pid">The backend process ID.</param>
/// <param name="User">The user name.</param>
/// <param name="Database">The database name.</param>
/// <param name="Application">The application name, <c>unknown</c> when not logged.</param>
/// <param name="Host">The client host or <c>[local]</c>.</param>
/// <param name="Port">The client port.</param>
/// <param name="DurationSeconds">The session length, for disconnections.</param>
public sealed record ConnectionEvent(
    DateTime Timestamp,
    ConnectionEventType Type,
    int? Pid = null,
    string? User = null,
    string? Database = null,
    string Application = "unknown",
    string? Host = null,
    int? Port = null,
    double? DurationSeconds = null)
{
    /// <summary>
    /// Reads an entry as a connection event.
    /// </summary>
    /// <remarks>
    /// Structured csvlog and jsonlog fields are preferred to the details in the message text.
    /// </remarks>
    /// <param name="entry">The entry.</param>
    /// <returns>The event, or null when the entry is not about a connection.</returns>
    public static ConnectionEvent? FromEntry(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (ConnectionMessageParser.Parse(entry.Message, entry.Level == LogLevel.Fatal) is not { } message)
        {
            return null;
        }

        var port = entry.RemotePort;
        if (port is null && !string.IsNullOrEmpty(message.Port)
            && int.TryParse(message.Port, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed))
        {
            port = parsed;
        }

        double? duration = null;
        if (message.Type == ConnectionEventType.Disconnect && !string.IsNullOrEmpty(message.Duration))
        {
            duration = ParseDuration(message.Duration);
        }

        return new ConnectionEvent(
            entry.Timestamp ?? ErrorEvent.LocalNow(),
            message.Type,
            entry.Pid,
            OrNull(entry.UserName) ?? message.User,
            OrNull(entry.DatabaseName) ?? message.Database,
            OrNull(entry.ApplicationName) ?? OrNull(message.Application) ?? "unknown",
            OrNull(entry.RemoteHost) ?? message.Host,
            port,
            duration);
    }

    /// <summary>
    /// Parses a session time written as <c>H:MM:SS.mmm</c>.
    /// </summary>
    /// <param name="text">The session time.</param>
    /// <returns>The length in seconds, or null when the text is not a session time.</returns>
    public static double? ParseDuration(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var parts = text.Split(':');
        if (parts.Length != 3
            || !int.TryParse(parts[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out var hours)
            || !int.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out var minutes)
            || !double.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var seconds))
        {
            return null;
        }

        return (hours * 3600) + (minutes * 60) + seconds;
    }

    private static string? OrNull(string? value) => string.IsNullOrEmpty(value) ? null : value;
}
