using System.Globalization;
using System.Text;
using Pgtail.Parsing;
using Pgtail.Statistics;

namespace Pgtail.Notifications;

/// <summary>
/// Decides which log entries send notifications and sends them.
/// </summary>
/// <remarks>
/// Rules are checked in order: level, pattern, error rate, then slow query, and only for entries logged after tailing
/// started. At most one notification is shown every five seconds; alerts that match in between are held and shown
/// together when the five seconds are up, as one notification that counts them. An alert whose message is one already
/// shown in the last minute, apart from its numbers, counts as a repeat instead of showing again, and the next time it
/// shows it says how often it repeated. Error rate alerts come at most once a minute, and nothing is shown during quiet
/// hours.
/// </remarks>
/// <param name="notifier">The platform notifier.</param>
/// <param name="errorStats">The error statistics error rate rules read.</param>
/// <param name="clock">Returns the current local time.</param>
public sealed class NotificationManager(INotifier notifier, ErrorStats errorStats, Func<DateTime> clock)
{
    private static readonly TimeSpan s_cooldown = TimeSpan.FromSeconds(5);
    private static readonly TimeSpan s_repeatWindow = TimeSpan.FromMinutes(1);
    private const int RememberedAlerts = 256;
    private readonly Lock _gate = new();
    private readonly Dictionary<string, Shown> _shown = new(StringComparer.Ordinal);
    private readonly List<Notification> _held = [];
    private DateTime? _lastShown;
    private DateTime? _lastErrorRateAlert;
    private Timer? _release;

    /// <summary>
    /// The rules and settings.
    /// </summary>
    public NotificationConfig Config { get; } = new();

    /// <summary>
    /// The platform notifier.
    /// </summary>
    public INotifier Notifier { get; } = notifier;

    /// <summary>
    /// Checks a newly logged entry against the rules and shows, holds, or counts the alert it raises.
    /// </summary>
    /// <param name="entry">The entry.</param>
    public void Consider(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        DateTime now = clock();
        if (!IsOn(now) || Match(entry, now) is not { } matched)
        {
            return;
        }

        (Notification? alert, string? key) = matched;
        lock (_gate)
        {
            if (_shown.TryGetValue(key, out Shown? shown) && now - shown.At < s_repeatWindow)
            {
                shown.Repeats++;
                return;
            }

            if (shown is { Repeats: > 0 })
            {
                alert = alert with { Body = $"{alert.Body}\n(repeated {shown.Repeats} times since it was last shown)" };
            }

            Remember(key, now);
            if (_held.Count == 0 && (_lastShown is not { } last || now - last >= s_cooldown))
            {
                Show(alert, now);
                return;
            }

            _held.Add(alert);
            TimeSpan wait = (_lastShown ?? now) + s_cooldown - now;
            _release ??= new Timer(_ => Release(), null, wait < TimeSpan.Zero ? TimeSpan.Zero : wait, Timeout.InfiniteTimeSpan);
        }
    }

    /// <summary>
    /// Sends a test notification, regardless of the rules and quiet hours.
    /// </summary>
    /// <param name="severity">The severity.</param>
    /// <returns>True when it was sent.</returns>
    public bool SendTest(NotificationSeverity severity) => Notifier.Send(new Notification(
        $"pgtail: Test ({severity.ToName().ToUpperInvariant()})",
        "Notification system is working correctly",
        "pgtail",
        severity,
        "test:pgtail"));

    private bool IsOn(DateTime now) => Config.Enabled && Config.QuietHours?.IsActive(now) != true;

    // The alert an entry raises, with the key that tells its repeats apart: its rule and its message without numbers.
    private (Notification Alert, string Key)? Match(LogEntry entry, DateTime now)
    {
        if (Config.LevelRules().Contains(entry.Level))
        {
            return (EntryNotification(entry, "Level Alert", $"lvl:{entry.Level.ToName()}"), "level:" + Shape(entry.Message));
        }

        if (Config.PatternRules().Any(rule => rule.Pattern!.IsMatch(entry.Message)))
        {
            string start = entry.Message.Length > 10 ? entry.Message[..10] : entry.Message;
            return (EntryNotification(entry, "Pattern Match", "pat:" + start), "pattern:" + Shape(entry.Message));
        }

        if (ErrorRateExceeded(now) is { } rate)
        {
            _lastErrorRateAlert = now;
            return (new Notification(
                "pgtail: High Error Rate",
                $"Error rate: {rate}/min (threshold: {Config.ErrorRateThreshold()}/min)",
                Severity: NotificationSeverity.Error,
                Tag: "rate:err"), "rate");
        }

        if (Config.SlowQueryThreshold() is { } threshold && DurationExtractor.Extract(entry.Message) is { } duration
            && duration > threshold)
        {
            string message = entry.Message.Length > 100 ? entry.Message[..97] + "..." : entry.Message;
            return (new Notification(
                "pgtail: Slow Query",
                $"Duration: {FormatMs(duration)}ms (threshold: {threshold}ms)\n{message}",
                Severity: NotificationSeverities.FromLevel(entry.Level),
                Tag: "slow:query"), "slow:" + Shape(entry.Message));
        }

        return null;
    }

    private void Show(Notification alert, DateTime now)
    {
        _lastShown = now;
        _ = Task.Run(() => Notifier.Send(alert));
    }

    // Shows what was held while the last notification was on screen: the alert itself, or one that counts them.
    private void Release()
    {
        lock (_gate)
        {
            _release?.Dispose();
            _release = null;
            DateTime now = clock();
            if (_held.Count > 0 && IsOn(now))
            {
                Show(_held.Count == 1 ? _held[0] : Summary(_held), now);
            }

            _held.Clear();
        }
    }

    private static Notification Summary(List<Notification> held)
    {
        IEnumerable<string> counts = held.GroupBy(alert => alert.Subtitle ?? alert.Title["pgtail: ".Length..], StringComparer.Ordinal)
            .Select(group => $"{group.Count()} {group.Key}");
        // The detail is the most severe alert, the newest of those.
        Notification worst = held.Where(alert => alert.Severity == held.Max(other => other.Severity)).Last();
        return new Notification(
            $"pgtail: {held.Count} more alerts",
            $"{string.Join(" · ", counts)}\n{worst.Body.Split('\n')[0]}",
            Severity: worst.Severity,
            Tag: "summary");
    }

    private void Remember(string key, DateTime now)
    {
        if (_shown.Count >= RememberedAlerts)
        {
            foreach (string? old in _shown.Where(pair => now - pair.Value.At >= s_repeatWindow).Select(pair => pair.Key).ToList())
            {
                _ = _shown.Remove(old);
            }
        }

        _shown[key] = new Shown(now);
    }

    // A message with each run of digits replaced, so "queue depth is 814" and "queue depth is 233" are one alert.
    private static string Shape(string message)
    {
        var shape = new StringBuilder(Math.Min(message.Length, 120));
        foreach (char character in message)
        {
            if (shape.Length >= 120)
            {
                break;
            }

            if (!char.IsAsciiDigit(character))
            {
                _ = shape.Append(character);
            }
            else if (shape.Length == 0 || shape[^1] != '#')
            {
                _ = shape.Append('#');
            }
        }

        return shape.ToString();
    }

    private int? ErrorRateExceeded(DateTime now)
    {
        if (Config.ErrorRateThreshold() is not { } threshold)
        {
            return null;
        }

        IReadOnlyList<int> buckets = errorStats.GetTrendBuckets(1);
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

    // When an alert was last shown, and how often it repeated since.
    private sealed class Shown(DateTime at)
    {
        /// <summary>
        /// When the alert was last shown.
        /// </summary>
        public DateTime At { get; } = at;

        /// <summary>
        /// How often it repeated since.
        /// </summary>
        public int Repeats { get; set; }
    }
}
