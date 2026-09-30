using Pgtail.Parsing;

namespace Pgtail.Statistics;

/// <summary>
/// The errors and warnings of a session.
/// </summary>
public sealed class ErrorStats
{
    private readonly Queue<ErrorEvent> _events = new();

    /// <summary>
    /// How many events are kept; the oldest are dropped first.
    /// </summary>
    public const int Capacity = 10_000;

    /// <summary>
    /// When statistics started, or were last cleared.
    /// </summary>
    public DateTime SessionStart { get; private set; } = ErrorEvent.LocalNow();

    /// <summary>
    /// The number of PANIC, FATAL, and ERROR entries seen.
    /// </summary>
    public int ErrorCount { get; private set; }

    /// <summary>
    /// The number of WARNING entries seen.
    /// </summary>
    public int WarningCount { get; private set; }

    /// <summary>
    /// When the last error was logged.
    /// </summary>
    public DateTime? LastErrorTime { get; private set; }

    /// <summary>
    /// Whether nothing has been recorded.
    /// </summary>
    public bool IsEmpty => _events.Count == 0;

    /// <summary>
    /// Whether a level counts as an error.
    /// </summary>
    /// <param name="level">The level.</param>
    /// <returns>True for PANIC, FATAL, and ERROR.</returns>
    public static bool IsError(LogLevel level) => level is LogLevel.Panic or LogLevel.Fatal or LogLevel.Error;

    /// <summary>
    /// Records an entry when it is an error or a warning.
    /// </summary>
    /// <param name="entry">The entry.</param>
    public void Add(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (!IsError(entry.Level) && entry.Level != LogLevel.Warning)
        {
            return;
        }

        var item = ErrorEvent.FromEntry(entry);
        _events.Enqueue(item);
        while (_events.Count > Capacity)
        {
            _events.Dequeue();
        }

        if (IsError(entry.Level))
        {
            ErrorCount++;
            LastErrorTime = item.Timestamp;
        }
        else
        {
            WarningCount++;
        }
    }

    /// <summary>
    /// Forgets everything and restarts the session clock.
    /// </summary>
    public void Clear()
    {
        _events.Clear();
        ErrorCount = 0;
        WarningCount = 0;
        LastErrorTime = null;
        SessionStart = ErrorEvent.LocalNow();
    }

    /// <summary>
    /// Every kept event, oldest first.
    /// </summary>
    /// <returns>The events.</returns>
    public IReadOnlyList<ErrorEvent> GetEvents() => [.. _events];

    /// <summary>
    /// Counts events by level.
    /// </summary>
    /// <returns>The counts.</returns>
    public IReadOnlyDictionary<LogLevel, int> GetByLevel()
    {
        var counts = new Dictionary<LogLevel, int>();
        foreach (ErrorEvent item in _events)
        {
            counts[item.Level] = counts.GetValueOrDefault(item.Level) + 1;
        }

        return counts;
    }

    /// <summary>
    /// Counts events by SQLSTATE code, the most frequent first.
    /// </summary>
    /// <remarks>
    /// Events without a code count as <c>UNKNOWN</c>. Codes with the same count keep the order they were first seen in.
    /// </remarks>
    /// <returns>The codes and counts.</returns>
    public IReadOnlyList<KeyValuePair<string, int>> GetByCode()
    {
        var counts = new Dictionary<string, int>(StringComparer.Ordinal);
        var order = new List<string>();
        foreach (string code in _events.Select(item => item.SqlState ?? "UNKNOWN"))
        {
            if (!counts.TryGetValue(code, out int count))
            {
                order.Add(code);
            }

            counts[code] = count + 1;
        }

        return [.. order.Select(code => new KeyValuePair<string, int>(code, counts[code])).OrderByDescending(pair => pair.Value)];
    }

    /// <summary>
    /// The events logged at or after a time.
    /// </summary>
    /// <param name="since">The time.</param>
    /// <returns>The events, oldest first.</returns>
    public IReadOnlyList<ErrorEvent> GetEventsSince(DateTime since)
    {
        DateTime bound = LogTimestamps.ToUtc(since);
        return [.. _events.Where(item => LogTimestamps.ToUtc(item.Timestamp) >= bound)];
    }

    /// <summary>
    /// The events with a SQLSTATE code.
    /// </summary>
    /// <param name="code">The code.</param>
    /// <returns>The events, oldest first.</returns>
    public IReadOnlyList<ErrorEvent> GetEventsByCode(string code) => [.. _events.Where(item => item.SqlState == code)];

    /// <summary>
    /// Counts events per minute for the trend sparkline.
    /// </summary>
    /// <param name="minutes">How many minutes to cover.</param>
    /// <returns>One count per minute, oldest first.</returns>
    public IReadOnlyList<int> GetTrendBuckets(int minutes = 60) => ErrorTrend.Bucket(_events, minutes);
}
