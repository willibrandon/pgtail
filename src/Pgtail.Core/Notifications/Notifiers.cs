using Pgtail.Platform;

namespace Pgtail.Notifications;

/// <summary>
/// Chooses the notifier for the current platform.
/// </summary>
public static class Notifiers
{
    /// <summary>
    /// The platform's notifier, or an unavailable one that says what is missing.
    /// </summary>
    /// <param name="environment">Reads environment variables.</param>
    /// <returns>The notifier.</returns>
    public static INotifier Create(Func<string, string?> environment)
    {
        ArgumentNullException.ThrowIfNull(environment);
        if (OperatingSystem.IsMacOS())
        {
            return ExecutableFinder.Find("osascript", environment) is { } osascript
                ? new MacNotifier(osascript)
                : new UnavailableNotifier("macOS (osascript not found)");
        }

        if (OperatingSystem.IsWindows())
        {
            return WindowsNotifier.TryCreate(environment) is { } windows
                ? windows
                : new UnavailableNotifier("Windows (WinRT unavailable)");
        }

        if (OperatingSystem.IsLinux() || OperatingSystem.IsFreeBSD())
        {
            return ExecutableFinder.Find("notify-send", environment) is { } notifySend
                ? new LinuxNotifier(notifySend)
                : new UnavailableNotifier("Linux (notify-send not found)");
        }

        return new UnavailableNotifier($"Unsupported platform: {Environment.OSVersion.Platform}");
    }
}
