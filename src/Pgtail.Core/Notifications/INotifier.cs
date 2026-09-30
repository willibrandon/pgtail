namespace Pgtail.Notifications;

/// <summary>
/// Sends desktop notifications through the platform's own mechanism.
/// </summary>
public interface INotifier
{
    /// <summary>
    /// Whether notifications can be sent.
    /// </summary>
    bool IsAvailable { get; }

    /// <summary>
    /// The platform and method, such as <c>Linux (notify-send)</c>, or why notifications are unavailable.
    /// </summary>
    string PlatformInfo { get; }

    /// <summary>
    /// Sends a notification.
    /// </summary>
    /// <param name="notification">The notification.</param>
    /// <returns>True when it was delivered to the platform.</returns>
    bool Send(Notification notification);
}
