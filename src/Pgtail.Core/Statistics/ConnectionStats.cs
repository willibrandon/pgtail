using Pgtail.Parsing;

namespace Pgtail.Statistics;

/// <summary>
/// The connections and disconnections of a session, with the connections still open.
/// </summary>
public sealed class ConnectionStats
{
    private readonly Queue<ConnectionEvent> _events = new();
    private readonly Dictionary<int, ConnectionEvent> _active = [];
    private readonly List<int> _activeOrder = [];

    /// <summary>
    /// How many events are kept; the oldest are dropped first.
    /// </summary>
    public const int Capacity = 10_000;

    /// <summary>
    /// When tracking started, or was last cleared.
    /// </summary>
    public DateTime SessionStart { get; private set; } = ErrorEvent.LocalNow();

    /// <summary>
    /// The connections seen.
    /// </summary>
    public int ConnectCount { get; private set; }

    /// <summary>
    /// The disconnections seen.
    /// </summary>
    public int DisconnectCount { get; private set; }

    /// <summary>
    /// The failed connection attempts seen.
    /// </summary>
    public int FailedCount { get; private set; }

    /// <summary>
    /// Whether nothing has been recorded.
    /// </summary>
    public bool IsEmpty => _events.Count == 0;

    /// <summary>
    /// The number of connections without a matching disconnection.
    /// </summary>
    public int ActiveCount => _active.Count;

    /// <summary>
    /// Records an entry when it is about a connection.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>True when the entry was a connection event.</returns>
    public bool Add(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (ConnectionEvent.FromEntry(entry) is not { } item)
        {
            return false;
        }

        _events.Enqueue(item);
        while (_events.Count > Capacity)
        {
            _events.Dequeue();
        }

        switch (item.Type)
        {
            case ConnectionEventType.Connect:
                ConnectCount++;
                if (item.Pid is { } pid)
                {
                    if (!_active.ContainsKey(pid))
                    {
                        _activeOrder.Add(pid);
                    }

                    _active[pid] = item;
                }

                break;
            case ConnectionEventType.Disconnect:
                DisconnectCount++;
                if (item.Pid is { } ended && _active.Remove(ended))
                {
                    _activeOrder.Remove(ended);
                }

                break;
            default:
                FailedCount++;
                break;
        }

        return true;
    }

    /// <summary>
    /// Forgets everything and restarts the session clock.
    /// </summary>
    public void Clear()
    {
        _events.Clear();
        _active.Clear();
        _activeOrder.Clear();
        ConnectCount = 0;
        DisconnectCount = 0;
        FailedCount = 0;
        SessionStart = ErrorEvent.LocalNow();
    }

    /// <summary>
    /// Every kept event, oldest first.
    /// </summary>
    /// <returns>The events.</returns>
    public IReadOnlyList<ConnectionEvent> GetEvents() => [.. _events];

    /// <summary>
    /// The open connections, optionally narrowed.
    /// </summary>
    /// <param name="filter">The filter, or null.</param>
    /// <returns>The connections in the order they opened.</returns>
    public IReadOnlyList<ConnectionEvent> GetActiveConnections(ConnectionFilter? filter = null)
    {
        var active = _activeOrder.Select(pid => _active[pid]);
        return filter is null || filter.IsEmpty ? [.. active] : [.. active.Where(filter.Matches)];
    }

    /// <summary>
    /// Counts open connections by database.
    /// </summary>
    /// <returns>The counts in first-seen order.</returns>
    public IReadOnlyList<KeyValuePair<string, int>> GetByDatabase() => Count(item => item.Database);

    /// <summary>
    /// Counts open connections by user.
    /// </summary>
    /// <returns>The counts in first-seen order.</returns>
    public IReadOnlyList<KeyValuePair<string, int>> GetByUser() => Count(item => item.User);

    /// <summary>
    /// Counts open connections by application.
    /// </summary>
    /// <returns>The counts in first-seen order.</returns>
    public IReadOnlyList<KeyValuePair<string, int>> GetByApplication() => Count(item => item.Application);

    /// <summary>
    /// The events logged at or after a time.
    /// </summary>
    /// <param name="since">The time.</param>
    /// <returns>The events, oldest first.</returns>
    public IReadOnlyList<ConnectionEvent> GetEventsSince(DateTime since)
    {
        var bound = LogTimestamps.ToUtc(since);
        return [.. _events.Where(item => LogTimestamps.ToUtc(item.Timestamp) >= bound)];
    }

    /// <summary>
    /// Counts connections and disconnections per time bucket for the history sparklines.
    /// </summary>
    /// <param name="minutes">The window in minutes.</param>
    /// <param name="bucketSize">The bucket size in minutes.</param>
    /// <param name="now">The current time, or null for the system clock.</param>
    /// <returns>The connects and disconnects of each bucket, oldest first.</returns>
    public IReadOnlyList<(int Connects, int Disconnects)> GetTrendBuckets(int minutes = 60, int bucketSize = 15, DateTime? now = null)
    {
        var current = now is { } fixedNow ? LogTimestamps.ToUtc(fixedNow) : DateTime.UtcNow;
        var count = Math.Max(1, minutes / bucketSize);
        var buckets = new (int Connects, int Disconnects)[count];
        foreach (var item in _events)
        {
            var ago = (current - LogTimestamps.ToUtc(item.Timestamp)).TotalSeconds / 60;
            if (ago < 0 || ago >= minutes)
            {
                continue;
            }

            var index = Math.Clamp(count - 1 - (int)Math.Floor(ago / bucketSize), 0, count - 1);
            if (item.Type == ConnectionEventType.Connect)
            {
                buckets[index].Connects++;
            }
            else if (item.Type == ConnectionEventType.Disconnect)
            {
                buckets[index].Disconnects++;
            }
        }

        return buckets;
    }

    private List<KeyValuePair<string, int>> Count(Func<ConnectionEvent, string?> key)
    {
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        var order = new List<string>();
        foreach (var pid in _activeOrder)
        {
            var name = key(_active[pid]);
            if (string.IsNullOrEmpty(name))
            {
                name = "unknown";
            }

            if (!counts.TryGetValue(name, out var value))
            {
                order.Add(name);
            }

            counts[name] = value + 1;
        }

        return [.. order.Select(name => new KeyValuePair<string, int>(name, counts[name]))];
    }
}
