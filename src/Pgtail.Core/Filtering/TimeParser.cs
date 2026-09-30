using System.Globalization;
using System.Text.RegularExpressions;
using Pgtail.Parsing;

namespace Pgtail.Filtering;

/// <summary>
/// Reads the time expressions accepted by <c>since</c>, <c>until</c>, <c>between</c>, and <c>--since</c>.
/// </summary>
public static partial class TimeParser
{
    /// <summary>
    /// Parses a relative time, a time of day, or an ISO 8601 date and time.
    /// </summary>
    /// <remarks>
    /// <c>5m</c>, <c>30s</c>, <c>2h</c>, and <c>1d</c> count back from now. <c>14:30</c> and <c>14:30:45</c> are today in
    /// local time. <c>2024-01-15T14:30</c> and <c>2024-01-15T14:30:00Z</c> are absolute; without an offset they are local.
    /// </remarks>
    /// <param name="value">The expression.</param>
    /// <param name="now">The current time, or null for the system clock.</param>
    /// <returns>The time in UTC.</returns>
    /// <exception cref="FormatException">The expression is not a time.</exception>
    public static DateTime Parse(string value, DateTime? now = null)
    {
        ArgumentNullException.ThrowIfNull(value);
        value = value.Trim();
        if (value.Length == 0)
        {
            throw new FormatException("Time value cannot be empty");
        }

        var utcNow = now is { } fixedNow ? LogTimestamps.ToUtc(fixedNow) : DateTime.UtcNow;
        var match = Relative().Match(value);
        if (match.Success)
        {
            var unit = char.ToLowerInvariant(match.Groups[2].Value[0]);
            var ticks = unit switch
            {
                's' => TimeSpan.TicksPerSecond,
                'm' => TimeSpan.TicksPerMinute,
                'h' => TimeSpan.TicksPerHour,
                _ => TimeSpan.TicksPerDay,
            };

            try
            {
                var amount = long.Parse(match.Groups[1].ValueSpan, NumberStyles.None, CultureInfo.InvariantCulture);
                return DateTime.SpecifyKind(utcNow.AddTicks(checked(-amount * ticks)), DateTimeKind.Utc);
            }
            catch (Exception exception) when (exception is OverflowException or ArgumentOutOfRangeException)
            {
                throw new FormatException($"Invalid time '{value}'. The duration is too long.");
            }
        }

        match = TimeOnly().Match(value);
        if (match.Success)
        {
            var hour = int.Parse(match.Groups[1].ValueSpan, CultureInfo.InvariantCulture);
            var minute = int.Parse(match.Groups[2].ValueSpan, CultureInfo.InvariantCulture);
            var second = match.Groups[3].Success ? int.Parse(match.Groups[3].ValueSpan, CultureInfo.InvariantCulture) : 0;
            if (hour > 23 || minute > 59 || second > 59)
            {
                throw new FormatException(
                    $"Invalid time '{value}'. Hours must be 0-23, minutes and seconds must be 0-59.");
            }

            var today = LogTimestamps.ToLocal(utcNow).Date;
            return LogTimestamps.ToUtc(today + new TimeSpan(hour, minute, second));
        }

        if (IsoDateTime.TryParse(value, out var absolute))
        {
            return LogTimestamps.ToUtc(absolute);
        }

        throw new FormatException(
            $"Invalid time format '{value}'. Supported formats:\n"
            + "  - Relative: 5m, 30s, 2h, 1d (from now)\n"
            + "  - Time only: 14:30, 14:30:45 (today)\n"
            + "  - ISO 8601: 2024-01-15T14:30, 2024-01-15T14:30:00Z");
    }

    /// <summary>
    /// Whether a time is later than now.
    /// </summary>
    /// <param name="value">The time, in UTC or local time.</param>
    /// <returns>True for a future time.</returns>
    public static bool IsFuture(DateTime value) => LogTimestamps.ToUtc(value) > DateTime.UtcNow;

    /// <summary>
    /// Describes a time range for display in local time.
    /// </summary>
    /// <remarks>
    /// Times on today's date show only the time of day; a lone bound adds "today". Examples: <c>since 14:30:00 today</c>,
    /// <c>between 14:00:00 and 15:00:00</c>, <c>until 2024-01-15 10:00:00</c>.
    /// </remarks>
    /// <param name="since">The start, or null.</param>
    /// <param name="until">The end, or null.</param>
    /// <returns>The description, or an empty string when neither bound is set.</returns>
    public static string FormatRange(DateTime? since, DateTime? until)
    {
        var today = DateTime.Now.Date;
        string Format(DateTime value, bool includeToday)
        {
            var local = LogTimestamps.ToLocal(value);
            if (local.Date == today)
            {
                var time = local.ToString("HH:mm:ss", CultureInfo.InvariantCulture);
                return includeToday ? time + " today" : time;
            }

            return local.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        }

        return (since, until) switch
        {
            ({ } start, { } end) => $"between {Format(start, false)} and {Format(end, false)}",
            ({ } start, null) => $"since {Format(start, true)}",
            (null, { } end) => $"until {Format(end, true)}",
            _ => "",
        };
    }

    [GeneratedRegex("^([0-9]+)([smhd])$", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex Relative();

    [GeneratedRegex("^([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?$")]
    private static partial Regex TimeOnly();
}
