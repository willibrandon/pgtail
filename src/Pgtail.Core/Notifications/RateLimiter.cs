namespace Pgtail.Notifications;

/// <summary>
/// Keeps a minimum gap between notifications.
/// </summary>
/// <param name="window">The minimum gap.</param>
public sealed class RateLimiter(TimeSpan window)
{
    private DateTime? _lastSent;

    /// <summary>
    /// Whether a notification may be sent now.
    /// </summary>
    /// <param name="now">The current time.</param>
    /// <returns>True when the gap has passed since the last one.</returns>
    public bool ShouldAllow(DateTime now) => _lastSent is not { } last || now - last >= window;

    /// <summary>
    /// Records that a notification was sent.
    /// </summary>
    /// <param name="now">The current time.</param>
    public void RecordSent(DateTime now) => _lastSent = now;
}
