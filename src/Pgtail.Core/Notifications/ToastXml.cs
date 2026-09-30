using System.Text;

namespace Pgtail.Notifications;

/// <summary>
/// Builds Windows toast XML with a template for each severity.
/// </summary>
public static class ToastXml
{
    /// <summary>
    /// How long a toast of a severity stays in Action Center, or null for one that never expires.
    /// </summary>
    /// <param name="severity">The severity.</param>
    /// <returns>The lifetime.</returns>
    public static TimeSpan? Expiry(NotificationSeverity severity) => severity switch
    {
        NotificationSeverity.Warning => TimeSpan.FromMinutes(10),
        NotificationSeverity.Error => TimeSpan.FromMinutes(30),
        NotificationSeverity.Critical => null,
        _ => TimeSpan.FromMinutes(2),
    };

    /// <summary>
    /// The toast XML for a notification.
    /// </summary>
    /// <remarks>
    /// Errors and critical alerts stay on screen longer; critical alerts use the alarm scenario and a looping alarm
    /// sound; warnings, errors, and critical alerts are labeled in the attribution line.
    /// </remarks>
    /// <param name="notification">The notification.</param>
    /// <returns>The XML.</returns>
    public static string Build(Notification notification)
    {
        ArgumentNullException.ThrowIfNull(notification);
        NotificationSeverity severity = notification.Severity;
        string duration = severity is NotificationSeverity.Error or NotificationSeverity.Critical ? "long" : "short";
        string? attribution = severity switch
        {
            NotificationSeverity.Warning => "Warning",
            NotificationSeverity.Error => "Error",
            NotificationSeverity.Critical => "Critical",
            _ => null,
        };

        var builder = new StringBuilder();
        builder.Append($"<toast duration=\"{duration}\"");
        if (severity == NotificationSeverity.Critical)
        {
            builder.Append(" scenario=\"alarm\"");
        }

        builder.Append(">\n    <visual>\n        <binding template=\"ToastGeneric\">\n");
        builder.Append($"            <text>{Escape(notification.Title)}</text>\n");
        if (!string.IsNullOrEmpty(notification.Subtitle))
        {
            builder.Append($"            <text>{Escape(notification.Subtitle)}</text>\n");
        }

        builder.Append($"            <text>{Escape(notification.Body)}</text>");
        if (attribution is not null)
        {
            builder.Append($"\n            <text placement=\"attribution\">{attribution}</text>");
        }

        builder.Append("\n        </binding>\n    </visual>\n");
        builder.Append(severity == NotificationSeverity.Critical
            ? "    <audio src=\"ms-winsoundevent:Notification.Looping.Alarm\" loop=\"true\"/>\n"
            : "    <audio src=\"ms-winsoundevent:Notification.Default\"/>\n");
        return builder.Append("</toast>").ToString();
    }

    /// <summary>
    /// Escapes text for an XML element or attribute.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <returns>The escaped text.</returns>
    public static string Escape(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        return text.Replace("&", "&amp;", StringComparison.Ordinal)
            .Replace("<", "&lt;", StringComparison.Ordinal)
            .Replace(">", "&gt;", StringComparison.Ordinal)
            .Replace("\"", "&quot;", StringComparison.Ordinal)
            .Replace("'", "&apos;", StringComparison.Ordinal);
    }
}
