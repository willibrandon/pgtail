namespace Pgtail.Notifications;

/// <summary>
/// Shows notifications on Linux and the BSDs with libnotify's <c>notify-send</c>.
/// </summary>
/// <param name="notifySend">The path of <c>notify-send</c>.</param>
public sealed class LinuxNotifier(string notifySend) : INotifier
{
    /// <inheritdoc/>
    public bool IsAvailable => true;

    /// <inheritdoc/>
    public string PlatformInfo => "Linux (notify-send)";

    /// <inheritdoc/>
    public bool Send(Notification notification)
    {
        ArgumentNullException.ThrowIfNull(notification);
        var body = string.IsNullOrEmpty(notification.Subtitle) ? notification.Body : $"{notification.Subtitle}\n{notification.Body}";
        return CommandNotifier.Run(notifySend, ["-u", "normal", "-a", "pgtail", notification.Title, body]);
    }
}
