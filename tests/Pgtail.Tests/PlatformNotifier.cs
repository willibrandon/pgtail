namespace Pgtail.Tests;

/// <summary>
/// What <c>notify</c> reports about the machine's way of showing notifications.
/// </summary>
/// <remarks>
/// Linux shows them with <c>notify-send</c>, which servers and CI runners often lack; notifications are then unavailable
/// rather than disabled.
/// </remarks>
internal static class PlatformNotifier
{
    /// <summary>
    /// The status line before notifications are turned on.
    /// </summary>
    public static string Status => OperatingSystem.IsLinux() && !HasNotifySend
        ? "Notifications: unavailable"
        : "Notifications: disabled";

    /// <summary>
    /// The platform line.
    /// </summary>
    public static string Platform => OperatingSystem.IsMacOS() ? "Platform: macOS (osascript)"
        : OperatingSystem.IsWindows() ? "Platform: Windows (WinRT Toast)"
        : HasNotifySend ? "Platform: Linux (notify-send)"
        : "Platform: Linux (notify-send not found)";

    private static bool HasNotifySend => (Environment.GetEnvironmentVariable("PATH") ?? "").Split(Path.PathSeparator)
        .Any(directory => directory.Length > 0 && File.Exists(Path.Combine(directory, "notify-send")));
}
