using Pgtail.Parsing;

namespace Pgtail.Notifications;

/// <summary>
/// Names and log level mappings for <see cref="NotificationSeverity"/>.
/// </summary>
public static class NotificationSeverities
{
    /// <summary>
    /// The names <c>notify test</c> accepts, in order of urgency.
    /// </summary>
    public static IReadOnlyList<string> Names { get; } = ["info", "warning", "error", "critical"];

    /// <summary>
    /// The lower case name of a severity.
    /// </summary>
    /// <param name="severity">The severity.</param>
    /// <returns>The name.</returns>
    public static string ToName(this NotificationSeverity severity) => severity switch
    {
        NotificationSeverity.Warning => "warning",
        NotificationSeverity.Error => "error",
        NotificationSeverity.Critical => "critical",
        _ => "info",
    };

    /// <summary>
    /// Reads a severity name, ignoring case.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <param name="severity">The severity.</param>
    /// <returns>True when the name is a severity.</returns>
    public static bool TryParse(string name, out NotificationSeverity severity)
    {
        ArgumentNullException.ThrowIfNull(name);
        (var found, severity) = name.ToLowerInvariant() switch
        {
            "info" => (true, NotificationSeverity.Info),
            "warning" => (true, NotificationSeverity.Warning),
            "error" => (true, NotificationSeverity.Error),
            "critical" => (true, NotificationSeverity.Critical),
            _ => (false, NotificationSeverity.Info),
        };

        return found;
    }

    /// <summary>
    /// The severity of a notification about an entry at a level.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <returns>Critical for PANIC and FATAL, error for ERROR, warning for WARNING, and info otherwise.</returns>
    public static NotificationSeverity FromLevel(LogLevel level) => level switch
    {
        LogLevel.Panic or LogLevel.Fatal => NotificationSeverity.Critical,
        LogLevel.Error => NotificationSeverity.Error,
        LogLevel.Warning => NotificationSeverity.Warning,
        _ => NotificationSeverity.Info,
    };
}
