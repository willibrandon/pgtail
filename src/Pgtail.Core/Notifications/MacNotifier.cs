namespace Pgtail.Notifications;

/// <summary>
/// Shows notifications on macOS with AppleScript's <c>display notification</c> through <c>osascript</c>.
/// </summary>
/// <param name="osascript">The path of <c>osascript</c>.</param>
public sealed class MacNotifier(string osascript) : INotifier
{
    /// <inheritdoc/>
    public bool IsAvailable => true;

    /// <inheritdoc/>
    public string PlatformInfo => "macOS (osascript)";

    /// <inheritdoc/>
    public bool Send(Notification notification)
    {
        ArgumentNullException.ThrowIfNull(notification);
        return CommandNotifier.Run(osascript, ["-e", Script(notification)]);
    }

    /// <summary>
    /// The AppleScript that shows a notification.
    /// </summary>
    /// <param name="notification">The notification.</param>
    /// <returns>The script.</returns>
    public static string Script(Notification notification)
    {
        ArgumentNullException.ThrowIfNull(notification);
        string script = $"display notification \"{Escape(notification.Body)}\"";
        if (!string.IsNullOrEmpty(notification.Subtitle))
        {
            script += $" subtitle \"{Escape(notification.Subtitle)}\"";
        }

        return script + $" with title \"{Escape(notification.Title)}\"";
    }

    private static string Escape(string text) => text.Replace("\\", "\\\\", StringComparison.Ordinal)
        .Replace("\"", "\\\"", StringComparison.Ordinal);
}
