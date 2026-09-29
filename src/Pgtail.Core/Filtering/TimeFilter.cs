using System.Globalization;
using Pgtail.Parsing;

namespace Pgtail.Filtering;

/// <summary>
/// Keeps entries logged within a time range.
/// </summary>
public sealed class TimeFilter
{
    /// <summary>
    /// Creates a filter.
    /// </summary>
    /// <param name="since">The earliest time to keep, or null for no lower bound.</param>
    /// <param name="until">The latest time to keep, or null for no upper bound.</param>
    /// <param name="originalInput">What the user typed, kept for display.</param>
    /// <exception cref="ArgumentException">The start is after the end.</exception>
    public TimeFilter(DateTime? since = null, DateTime? until = null, string originalInput = "")
    {
        if (since is { } start && until is { } end && LogTimestamps.ToUtc(start) > LogTimestamps.ToUtc(end))
        {
            throw new ArgumentException(
                $"Start time ({Clock(start)}) must be before end time ({Clock(end)})");
        }

        Since = since;
        Until = until;
        OriginalInput = originalInput;
    }

    /// <summary>
    /// A filter that keeps everything.
    /// </summary>
    public static TimeFilter Empty { get; } = new();

    /// <summary>
    /// The earliest time kept, or null.
    /// </summary>
    public DateTime? Since { get; }

    /// <summary>
    /// The latest time kept, or null.
    /// </summary>
    public DateTime? Until { get; }

    /// <summary>
    /// What the user typed.
    /// </summary>
    public string OriginalInput { get; }

    /// <summary>
    /// Whether either bound is set.
    /// </summary>
    public bool IsActive => Since is not null || Until is not null;

    /// <summary>
    /// Whether an entry falls inside the range.
    /// </summary>
    /// <remarks>
    /// While a bound is set, entries without a timestamp are dropped.
    /// </remarks>
    /// <param name="entry">The entry.</param>
    /// <returns>True to keep the entry.</returns>
    public bool Matches(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (!IsActive)
        {
            return true;
        }

        if (entry.Timestamp is not { } timestamp)
        {
            return false;
        }

        var value = LogTimestamps.ToUtc(timestamp);
        if (Since is { } since && value < LogTimestamps.ToUtc(since))
        {
            return false;
        }

        return Until is not { } until || value <= LogTimestamps.ToUtc(until);
    }

    /// <summary>
    /// Describes the range, such as <c>since 14:30:00 today</c>.
    /// </summary>
    /// <returns>The description, or an empty string for an inactive filter.</returns>
    public string FormatDescription() => TimeParser.FormatRange(Since, Until);

    private static string Clock(DateTime value) =>
        LogTimestamps.ToLocal(value).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
}
