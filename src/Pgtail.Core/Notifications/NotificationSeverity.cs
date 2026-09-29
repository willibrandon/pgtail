namespace Pgtail.Notifications;

/// <summary>
/// How urgent a notification is, which sets how long a Windows toast stays and how it sounds.
/// </summary>
public enum NotificationSeverity
{
    /// <summary>
    /// A short notification with the default sound.
    /// </summary>
    Info,

    /// <summary>
    /// A short notification labeled as a warning.
    /// </summary>
    Warning,

    /// <summary>
    /// A long, high priority notification.
    /// </summary>
    Error,

    /// <summary>
    /// An alarm that loops its sound and does not expire.
    /// </summary>
    Critical,
}
