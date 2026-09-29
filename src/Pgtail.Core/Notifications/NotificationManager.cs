using System.Globalization;
using Pgtail.Parsing;
using Pgtail.Statistics;

namespace Pgtail.Notifications;

/// <summary>
/// Decides which log entries send notifications and sends them.
/// </summary>
/// <remarks>
/// Rules are checked in order: level, pattern, error rate, then slow query. At most one notification is sent every five
/// seconds, error rate alerts at most once a minute, and nothing is sent during quiet hours.
/// </remarks>
/// <param name="notifier">The platform notifier.</param>
/// <param name="errorStats">The error statistics error rate rules read.</param>
/// <param name="clock">Returns the current local time.</param>
public sealed class NotificationManager(INotifier notifier, ErrorStats errorStats, Func<DateTime> clock)
{
    private readonly RateLimiter _limiter = new(TimeSpan.FromSeconds(5));
    private DateTime? _lastErrorRateAlert;

    /// <summary>
    /// The rules and settings.
    /// </summary>
    public NotificationConfig Config { get; } = new();

    /// <summary>
    /// The platform notifier.
    /// </summary>
    public INotifier Notifier { get; } = notifier;

    /// <summary>
    /// Checks an entry against the rules and sends a notification when one matches.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The notification to send, or null; the caller sends it with <see cref="Deliver"/>.</returns>
    public Notification? Check(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        var now = clock();
        if (!Config.Enabled || Config.QuietHours?.IsActive(now) == true)
        {
            return null;
        }

        if (Config.LevelRules().Contains(entry.Level))
        {
            return Allow(now, EntryNotification(entry, "Level Alert", $"lvl:{entry.Level.ToName()}"));
        }

        if (Config.PatternRules().Any(rule => rule.Pattern!.IsMatch(entry.Message)))
        {
            var start = entry.Message.Length > 10 ? entry.Message[..10] : entry.Message;
            return Allow(now, EntryNotification(entry, "Pattern Match", "pat:" + start));
        }

        if (ErrorRateExceeded(now) is { } rate)
        {
            var alert = Allow(now, new Notification(
                "pgtail: High Error Rate",
                $"Error rate: {rate}/min (threshold: {Config.ErrorRateThreshold()}/min)",
                Severity: NotificationSeverity.Error,
                Tag: "rate:err"));
            if (alert is not null)
            {
                _lastErrorRateAlert = now;
            }

            return alert;
        }

        if (Config.SlowQueryThreshold() is { } threshold && DurationExtractor.Extract(entry.Message) is { } duration
            && duration > threshold)
        {
            var message = entry.Message.Length > 100 ? entry.Message[..97] + "..." : entry.Message;
            return Allow(now, new Notification(
                "pgtail: Slow Query",
                $"Duration: {FormatMs(duration)}ms (threshold: {threshold}ms)\n{message}",
                Severity: NotificationSeverities.FromLevel(entry.Level),
                Tag: "slow:query"));
        }

        return null;
    }

    /// <summary>
    /// Sends a notification through the platform notifier.
    /// </summary>
    /// <param name="notification">The notification.</param>
    /// <returns>True when it was delivered.</returns>
    public bool Deliver(Notification notification) => Notifier.Send(notification);

    /// <summary>
    /// Sends a test notification, regardless of rate limits and quiet hours.
    /// </summary>
    /// <param name="severity">The severity to test.</param>
    /// <returns>True when it was delivered.</returns>
    public bool SendTest(NotificationSeverity severity) => Notifier.Send(new Notification(
        $"pgtail: Test ({severity.ToName().ToUpperInvariant()})",
        "Notification system is working correctly",
        "pgtail",
        severity,
        "test:pgtail"));

    private Notification? Allow(DateTime now, Notification notification)
    {
        if (!_limiter.ShouldAllow(now))
        {
            return null;
        }

        _limiter.RecordSent(now);
        return notification;
    }

    private int? ErrorRateExceeded(DateTime now)
    {
        if (Config.ErrorRateThreshold() is not { } threshold)
        {
            return null;
        }

        var buckets = errorStats.GetTrendBuckets(1);
        if (buckets.Count == 0 || buckets[^1] <= threshold)
        {
            return null;
        }

        return _lastErrorRateAlert is { } last && now - last < TimeSpan.FromSeconds(60) ? null : buckets[^1];
    }

    private static Notification EntryNotification(LogEntry entry, string category, string tag)
    {
        var parts = new List<string>();
        if (entry.Message.Length > 0)
        {
            parts.Add(entry.Message.Length > 150 ? entry.Message[..147] + "..." : entry.Message);
        }

        if (!string.IsNullOrEmpty(entry.DatabaseName))
        {
            parts.Add($"Database: {entry.DatabaseName}");
        }

        return new Notification(
            $"pgtail: {category}",
            parts.Count > 0 ? string.Join('\n', parts) : "Log event occurred",
            entry.Level.ToName(),
            NotificationSeverities.FromLevel(entry.Level),
            tag.Length > 16 ? tag[..16] : tag);
    }

    private static string FormatMs(double value) => value.ToString("0.###", CultureInfo.InvariantCulture);
}
