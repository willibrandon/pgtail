namespace Pgtail.Configuration;

/// <summary>
/// The effective value of every setting: the configuration file's valid values over the defaults.
/// </summary>
public sealed class PgtailConfig
{
    private readonly Dictionary<string, object?> _values = new(StringComparer.Ordinal);

    /// <summary>
    /// Creates the default configuration.
    /// </summary>
    public PgtailConfig()
    {
        foreach (var setting in SettingsSchema.All)
        {
            _values[setting.Key] = setting.Default;
        }
    }

    /// <summary>
    /// The value of a setting.
    /// </summary>
    /// <param name="key">The dotted key.</param>
    /// <returns>The value, or null when it is unset.</returns>
    public object? this[string key]
    {
        get => _values.TryGetValue(key, out var value) ? value : throw new KeyNotFoundException($"Unknown setting: {key}");
        set
        {
            if (!_values.ContainsKey(key))
            {
                throw new KeyNotFoundException($"Unknown setting: {key}");
            }

            _values[key] = value;
        }
    }

    /// <summary>
    /// The default level filter; empty for every level.
    /// </summary>
    public IReadOnlyList<string> DefaultLevels => (IReadOnlyList<string>)this["default.levels"]!;

    /// <summary>
    /// The slow query warning threshold in milliseconds.
    /// </summary>
    public long SlowWarn => (long)this["slow.warn"]!;

    /// <summary>
    /// The slow query threshold in milliseconds.
    /// </summary>
    public long SlowError => (long)this["slow.error"]!;

    /// <summary>
    /// The critical slow query threshold in milliseconds.
    /// </summary>
    public long SlowCritical => (long)this["slow.critical"]!;

    /// <summary>
    /// The theme name.
    /// </summary>
    public string ThemeName => (string)this["theme.name"]!;

    /// <summary>
    /// Whether desktop notifications are on.
    /// </summary>
    public bool NotificationsEnabled => (bool)this["notifications.enabled"]!;

    /// <summary>
    /// The levels that trigger notifications.
    /// </summary>
    public IReadOnlyList<string> NotificationLevels => (IReadOnlyList<string>)this["notifications.levels"]!;

    /// <summary>
    /// The patterns that trigger notifications.
    /// </summary>
    public IReadOnlyList<string> NotificationPatterns => (IReadOnlyList<string>)this["notifications.patterns"]!;

    /// <summary>
    /// The error rate per minute that triggers a notification, or null.
    /// </summary>
    public long? NotificationErrorRate => (long?)this["notifications.error_rate"];

    /// <summary>
    /// The query duration in milliseconds that triggers a notification, or null.
    /// </summary>
    public long? NotificationSlowQueryMs => (long?)this["notifications.slow_query_ms"];

    /// <summary>
    /// The quiet hours such as <c>22:00-08:00</c>, or null.
    /// </summary>
    public string? QuietHours => (string?)this["notifications.quiet_hours"];

    /// <summary>
    /// Whether the startup update check runs.
    /// </summary>
    public bool UpdatesCheck => (bool)this["updates.check"]!;

    /// <summary>
    /// When the last update check ran, in ISO 8601, or empty.
    /// </summary>
    public string LastUpdateCheck => (string)this["updates.last_check"]!;

    /// <summary>
    /// The latest version seen by the last update check, or empty.
    /// </summary>
    public string LastSeenVersion => (string)this["updates.last_version"]!;
}
