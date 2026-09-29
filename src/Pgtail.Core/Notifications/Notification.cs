namespace Pgtail.Notifications;

/// <summary>
/// A desktop notification.
/// </summary>
/// <param name="Title">The title.</param>
/// <param name="Body">The body text.</param>
/// <param name="Subtitle">A subtitle shown above the body, or null.</param>
/// <param name="Severity">How urgent it is.</param>
/// <param name="Tag">A tag that lets a newer Windows toast replace an older one, at most 16 characters, or null.</param>
public sealed record Notification(
    string Title,
    string Body,
    string? Subtitle = null,
    NotificationSeverity Severity = NotificationSeverity.Info,
    string? Tag = null);
