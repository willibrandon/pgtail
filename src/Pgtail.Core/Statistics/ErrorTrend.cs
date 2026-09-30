using Pgtail.Parsing;

namespace Pgtail.Statistics;

/// <summary>
/// Buckets events by minute and draws them as sparklines.
/// </summary>
public static class ErrorTrend
{
    /// <summary>
    /// The block characters of a sparkline, from lowest to highest.
    /// </summary>
    public const string SparkCharacters = "▁▂▃▄▅▆▇█";

    /// <summary>
    /// Draws values as a sparkline scaled to the largest value.
    /// </summary>
    /// <param name="values">The values.</param>
    /// <returns>One block character per value.</returns>
    public static string Sparkline(IReadOnlyList<int> values)
    {
        ArgumentNullException.ThrowIfNull(values);
        if (values.Count == 0)
        {
            return "";
        }

        int max = values.Max();
        if (max == 0)
        {
            max = 1;
        }

        return string.Concat(values.Select(value => SparkCharacters[Math.Min((int)((double)value / max * 7), 7)]));
    }

    /// <summary>
    /// Counts events per minute over the last minutes.
    /// </summary>
    /// <param name="events">The events.</param>
    /// <param name="minutes">How many minutes to cover.</param>
    /// <param name="now">The current time, or null for the system clock.</param>
    /// <returns>One count per minute, oldest first.</returns>
    public static IReadOnlyList<int> Bucket(IEnumerable<ErrorEvent> events, int minutes = 60, DateTime? now = null)
    {
        ArgumentNullException.ThrowIfNull(events);
        DateTime current = now is { } fixedNow ? LogTimestamps.ToUtc(fixedNow) : DateTime.UtcNow;
        int[] buckets = new int[Math.Max(0, minutes)];
        DateTime cutoff = current.AddMinutes(-minutes);
        foreach (ErrorEvent item in events)
        {
            DateTime timestamp = LogTimestamps.ToUtc(item.Timestamp);
            if (timestamp < cutoff)
            {
                continue;
            }

            int age = (int)((current - timestamp).TotalSeconds / 60);
            if (age >= 0 && age < minutes)
            {
                buckets[minutes - 1 - age]++;
            }
        }

        return buckets;
    }
}
