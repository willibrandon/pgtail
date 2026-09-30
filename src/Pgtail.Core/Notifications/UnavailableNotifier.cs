namespace Pgtail.Notifications;

/// <summary>
/// Stands in where the platform has no way to show notifications, such as a server without a desktop.
/// </summary>
/// <param name="reason">Why notifications are unavailable, as in <c>Linux (notify-send not found)</c>.</param>
public sealed class UnavailableNotifier(string reason) : INotifier
{
    /// <inheritdoc/>
    public bool IsAvailable => false;

    /// <inheritdoc/>
    public string PlatformInfo { get; } = reason;

    /// <inheritdoc/>
    public bool Send(Notification notification) => false;
}
