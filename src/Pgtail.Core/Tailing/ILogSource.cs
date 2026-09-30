using System.Threading.Channels;

namespace Pgtail.Tailing;

/// <summary>
/// Reads log entries in the background and reports them through a channel.
/// </summary>
public interface ILogSource : IAsyncDisposable
{
    /// <summary>
    /// The events read so far and not yet taken.
    /// </summary>
    ChannelReader<LogSourceEvent> Events { get; }

    /// <summary>
    /// Whether a file being read is currently missing or unreadable.
    /// </summary>
    bool IsUnavailable { get; }

    /// <summary>
    /// Whether a file being read exists but may not be read by this user.
    /// </summary>
    bool IsPermissionDenied { get; }

    /// <summary>
    /// Starts reading.
    /// </summary>
    void Start();

    /// <summary>
    /// Stops reading back older entries; a source that reads none back ignores it.
    /// </summary>
    void StopReadingOlder();
}
