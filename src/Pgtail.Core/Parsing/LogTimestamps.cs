using System.Collections.Frozen;
using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Parsing;

/// <summary>
/// Reads the timestamps PostgreSQL writes and normalizes them for comparison.
/// </summary>
public static partial class LogTimestamps
{
    private static readonly FrozenDictionary<string, int> s_zoneOffsets = new Dictionary<string, int>(StringComparer.Ordinal)
    {
        ["UTC"] = 0,
        ["GMT"] = 0,
        ["Z"] = 0,
        ["EST"] = -5,
        ["EDT"] = -4,
        ["CST"] = -6,
        ["CDT"] = -5,
        ["MST"] = -7,
        ["MDT"] = -6,
        ["PST"] = -8,
        ["PDT"] = -7,
        ["AKST"] = -9,
        ["AKDT"] = -8,
        ["HST"] = -10,
        ["WET"] = 0,
        ["WEST"] = 1,
        ["CET"] = 1,
        ["CEST"] = 2,
        ["EET"] = 2,
        ["EEST"] = 3,
        ["JST"] = 9,
        ["KST"] = 9,
        ["IST"] = 5,
        ["AEST"] = 10,
        ["AEDT"] = 11,
        ["NZST"] = 12,
        ["NZDT"] = 13,
    }
    .ToFrozenDictionary(StringComparer.Ordinal);

    /// <summary>
    /// Parses <c>YYYY-MM-DD HH:MM:SS</c> with optional fractional seconds of up to six digits.
    /// </summary>
    /// <param name="text">The text, with nothing before or after the time.</param>
    /// <param name="value">The time, with an unspecified kind.</param>
    /// <returns>True when the text is a valid time.</returns>
    public static bool TryParseNaive(string text, out DateTime value)
    {
        ArgumentNullException.ThrowIfNull(text);
        value = default;
        Match match = NaivePattern().Match(text);
        if (!match.Success)
        {
            return false;
        }

        int year = int.Parse(match.Groups[1].ValueSpan, CultureInfo.InvariantCulture);
        int month = int.Parse(match.Groups[2].ValueSpan, CultureInfo.InvariantCulture);
        int day = int.Parse(match.Groups[3].ValueSpan, CultureInfo.InvariantCulture);
        int hour = int.Parse(match.Groups[4].ValueSpan, CultureInfo.InvariantCulture);
        int minute = int.Parse(match.Groups[5].ValueSpan, CultureInfo.InvariantCulture);
        int second = int.Parse(match.Groups[6].ValueSpan, CultureInfo.InvariantCulture);
        string fraction = match.Groups[7].Success ? match.Groups[7].Value.PadRight(6, '0') : "0";
        int microseconds = int.Parse(fraction, CultureInfo.InvariantCulture);
        if (year < 1 || month is < 1 or > 12 || hour > 23 || minute > 59 || second > 59)
        {
            return false;
        }

        if (day < 1 || day > DateTime.DaysInMonth(year, month))
        {
            return false;
        }

        value = new DateTime(year, month, day, hour, minute, second, DateTimeKind.Unspecified).AddTicks(microseconds * 10L);
        return true;
    }

    /// <summary>
    /// The UTC offset of a zone abbreviation PostgreSQL writes, such as <c>UTC</c> or <c>PDT</c>.
    /// </summary>
    /// <param name="zone">The abbreviation.</param>
    /// <param name="offset">The offset, when the abbreviation is known.</param>
    /// <returns>True when the abbreviation is known.</returns>
    public static bool TryGetZoneOffset(string zone, out TimeSpan offset)
    {
        ArgumentNullException.ThrowIfNull(zone);
        bool known = s_zoneOffsets.TryGetValue(zone.ToUpperInvariant(), out int hours);
        offset = TimeSpan.FromHours(hours);
        return known;
    }

    /// <summary>
    /// Parses a csvlog or jsonlog timestamp into UTC and the offset it was written with.
    /// </summary>
    /// <remarks>
    /// Accepts a trailing zone abbreviation such as <c>PST</c>, an ISO 8601 offset such as <c>+00</c> or <c>-05:00</c>, or
    /// a <c>T</c> separated time ending in <c>Z</c>. An unknown abbreviation is read as UTC, and a time without any zone
    /// as local time.
    /// </remarks>
    /// <param name="text">The timestamp, or null.</param>
    /// <returns>The time in UTC and its offset, or null when the text is empty or not a time.</returns>
    public static (DateTime Time, TimeSpan Offset)? ParseStructured(string? text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return null;
        }

        string value = text.Trim();
        TimeSpan? offset = null;
        bool isIso = IsoSeparator().IsMatch(value);
        if (isIso && value.EndsWith('Z'))
        {
            value = value[..^1];
            offset = TimeSpan.Zero;
        }
        else if (isIso || IsoOffset().IsMatch(value))
        {
            Match match = IsoOffset().Match(value);
            if (match.Success)
            {
                int sign = match.Groups[1].Value == "+" ? 1 : -1;
                int hours = int.Parse(match.Groups[2].ValueSpan, CultureInfo.InvariantCulture);
                int minutes = match.Groups[3].Success ? int.Parse(match.Groups[3].ValueSpan, CultureInfo.InvariantCulture) : 0;
                offset = new TimeSpan(sign * hours, sign * minutes, 0);
                value = value[..match.Index].Trim();
            }
        }
        else
        {
            int space = value.LastIndexOf(' ');
            if (space >= 0 && value.Length - space - 1 <= 5)
            {
                string zone = value[(space + 1)..];
                if (s_zoneOffsets.TryGetValue(zone.ToUpperInvariant(), out int hours))
                {
                    offset = TimeSpan.FromHours(hours);
                    value = value[..space];
                }
                else if (zone.Length > 0 && zone.All(char.IsLetter))
                {
                    value = value[..space];
                    offset = TimeSpan.Zero;
                }
            }
        }

        if (!TryParseNaive(value.Replace('T', ' '), out DateTime local))
        {
            return null;
        }

        TimeSpan written = offset ?? TimeZoneInfo.Local.GetUtcOffset(local);
        return (DateTime.SpecifyKind(local - written, DateTimeKind.Utc), written);
    }

    /// <summary>
    /// Converts a time to UTC, reading a time without a zone as local time.
    /// </summary>
    /// <param name="value">The time.</param>
    /// <returns>The same instant with <see cref="DateTimeKind.Utc"/>.</returns>
    public static DateTime ToUtc(DateTime value)
    {
        if (value.Kind == DateTimeKind.Utc)
        {
            return value;
        }

        // A local time skipped by a daylight saving change has no instant of its own; the offset in force is used.
        TimeSpan offset = TimeZoneInfo.Local.GetUtcOffset(DateTime.SpecifyKind(value, DateTimeKind.Unspecified));
        return DateTime.SpecifyKind(value - offset, DateTimeKind.Utc);
    }

    /// <summary>
    /// Converts a time to local time for display, leaving a time without a zone as written.
    /// </summary>
    /// <param name="value">The time.</param>
    /// <returns>The local time, with an unspecified kind.</returns>
    public static DateTime ToLocal(DateTime value) => value.Kind == DateTimeKind.Utc
        ? DateTime.SpecifyKind(TimeZoneInfo.ConvertTimeFromUtc(value, TimeZoneInfo.Local), DateTimeKind.Unspecified)
        : DateTime.SpecifyKind(value, DateTimeKind.Unspecified);

    /// <summary>
    /// Formats a time the way ISO 8601 output is written: <c>2024-01-15T10:30:45.123000+00:00</c>.
    /// </summary>
    /// <remarks>
    /// Microseconds are written only when there are some, and the offset only for a UTC time.
    /// </remarks>
    /// <param name="value">The time.</param>
    /// <returns>The text.</returns>
    public static string ToIsoFormat(DateTime value)
    {
        string text = value.ToString("yyyy-MM-dd'T'HH:mm:ss", CultureInfo.InvariantCulture);
        int microseconds = (int)(value.Ticks % TimeSpan.TicksPerSecond / 10);
        if (microseconds != 0)
        {
            text += "." + microseconds.ToString("D6", CultureInfo.InvariantCulture);
        }

        return value.Kind == DateTimeKind.Utc ? text + "+00:00" : text;
    }

    /// <summary>
    /// Formats an entry's time as ISO 8601 in the zone it was written in, such as <c>2024-01-15T10:30:45.123000-07:00</c>.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The time, or null when the entry has none.</returns>
    public static string? ToIsoFormat(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (entry is not { WrittenTime: { } written, Offset: { } offset })
        {
            return entry.Timestamp is { } time ? ToIsoFormat(time) : null;
        }

        char sign = offset < TimeSpan.Zero ? '-' : '+';
        TimeSpan magnitude = offset.Duration();
        return ToIsoFormat(written) + $"{sign}{magnitude.Hours:D2}:{magnitude.Minutes:D2}";
    }

    [GeneratedRegex(@"^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})\s+([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2})(?:\.([0-9]{1,6}))?$")]
    private static partial Regex NaivePattern();

    [GeneratedRegex(@"\dT\d")]
    private static partial Regex IsoSeparator();

    [GeneratedRegex(@"([+-])([0-9]{2}):?([0-9]{2})?$")]
    private static partial Regex IsoOffset();
}
