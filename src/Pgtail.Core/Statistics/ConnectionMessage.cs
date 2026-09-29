namespace Pgtail.Statistics;

/// <summary>
/// The details a connection log message carries.
/// </summary>
/// <param name="Type">What happened.</param>
/// <param name="User">The user name.</param>
/// <param name="Database">The database name.</param>
/// <param name="Application">The application name.</param>
/// <param name="Host">The client host.</param>
/// <param name="Port">The client port, as written.</param>
/// <param name="Duration">The session time, as written.</param>
public sealed record ConnectionMessage(
    ConnectionEventType Type,
    string? User = null,
    string? Database = null,
    string? Application = null,
    string? Host = null,
    string? Port = null,
    string? Duration = null);
