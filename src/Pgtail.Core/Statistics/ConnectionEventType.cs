namespace Pgtail.Statistics;

/// <summary>
/// What happened to a connection.
/// </summary>
public enum ConnectionEventType
{
    /// <summary>
    /// A connection was authorized.
    /// </summary>
    Connect,

    /// <summary>
    /// A session ended.
    /// </summary>
    Disconnect,

    /// <summary>
    /// A connection attempt failed.
    /// </summary>
    ConnectionFailed,
}
