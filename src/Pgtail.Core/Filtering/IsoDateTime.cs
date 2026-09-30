using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Filtering;

/// <summary>
/// Parses the ISO 8601 date and time forms people type on the command line.
/// </summary>
/// <remarks>
/// Dates are <c>2024-01-15</c>, <c>20240115</c>, or week dates such as <c>2024-W03-1</c>. A time may follow after
/// <c>T</c>, a space, or any other single character, as <c>14</c>, <c>14:30</c>, <c>14:30:45</c>, or <c>14:30:45.123</c>,
/// or in basic form such as <c>143045</c>. An offset of <c>Z</c>, <c>+05</c>, <c>+05:30</c>, or <c>-0800</c> may end it.
/// </remarks>
public static partial class IsoDateTime
{
    /// <summary>
    /// Parses a date with an optional time and offset.
    /// </summary>
    /// <param name="text">The text.</param>
    /// <param name="value">The time in UTC when an offset was given, otherwise with an unspecified kind.</param>
    /// <returns>True when the text is a valid date and time.</returns>
    public static bool TryParse(string text, out DateTime value)
    {
        ArgumentNullException.ThrowIfNull(text);
        value = default;
        if (!TryParseDate(text, out DateTime date, out int consumed))
        {
            return false;
        }

        if (consumed == text.Length)
        {
            value = date;
            return true;
        }

        // Any single character may separate the date from the time.
        string rest = text[(consumed + 1)..];
        if (rest.Length == 0)
        {
            return false;
        }

        int offsetStart = rest.IndexOfAny(['Z', '+', '-']);
        string timeText = offsetStart < 0 ? rest : rest[..offsetStart];
        string offsetText = offsetStart < 0 ? "" : rest[offsetStart..];
        if (!TryParseTime(timeText, out TimeSpan time))
        {
            return false;
        }

        DateTime local = date + time;
        if (offsetText.Length == 0)
        {
            value = local;
            return true;
        }

        if (!TryParseOffset(offsetText, out TimeSpan offset))
        {
            return false;
        }

        value = DateTime.SpecifyKind(local - offset, DateTimeKind.Utc);
        return true;
    }

    private static bool TryParseDate(string text, out DateTime date, out int consumed)
    {
        date = default;
        consumed = 0;
        Match match = CalendarDate().Match(text);
        if (match.Success)
        {
            consumed = match.Length;
            return TryDate(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value, out date);
        }

        match = BasicDate().Match(text);
        if (match.Success)
        {
            consumed = match.Length;
            return TryDate(match.Groups[1].Value, match.Groups[2].Value, match.Groups[3].Value, out date);
        }

        match = WeekDate().Match(text);
        if (!match.Success)
        {
            return false;
        }

        consumed = match.Length;
        int year = Number(match.Groups[1].Value);
        int week = Number(match.Groups[2].Value);
        int day = match.Groups[3].Success ? Number(match.Groups[3].Value) : 1;
        if (year < 1 || week < 1 || week > ISOWeek.GetWeeksInYear(year) || day is < 1 or > 7)
        {
            return false;
        }

        date = ISOWeek.ToDateTime(year, week, day == 7 ? DayOfWeek.Sunday : (DayOfWeek)day);
        return true;
    }

    private static bool TryDate(string yearText, string monthText, string dayText, out DateTime date)
    {
        date = default;
        int year = Number(yearText);
        int month = Number(monthText);
        int day = Number(dayText);
        if (year < 1 || month is < 1 or > 12 || day < 1 || day > DateTime.DaysInMonth(year, month))
        {
            return false;
        }

        date = new DateTime(year, month, day, 0, 0, 0, DateTimeKind.Unspecified);
        return true;
    }

    private static bool TryParseTime(string text, out TimeSpan time)
    {
        time = default;
        Match match = ExtendedTime().Match(text);
        if (!match.Success)
        {
            match = BasicTime().Match(text);
        }

        if (!match.Success)
        {
            return false;
        }

        int hour = Number(match.Groups[1].Value);
        int minute = match.Groups[2].Success ? Number(match.Groups[2].Value) : 0;
        int second = match.Groups[3].Success ? Number(match.Groups[3].Value) : 0;
        string fraction = match.Groups[4].Success ? match.Groups[4].Value : "";
        if (fraction.Length > 0 && !match.Groups[3].Success)
        {
            return false;
        }

        if (hour > 23 || minute > 59 || second > 59)
        {
            return false;
        }

        // Digits beyond microseconds are dropped.
        int micro = fraction.Length == 0 ? 0 : Number(fraction.Length > 6 ? fraction[..6] : fraction.PadRight(6, '0'));
        time = new TimeSpan(0, hour, minute, second) + TimeSpan.FromTicks(micro * 10L);
        return true;
    }

    private static bool TryParseOffset(string text, out TimeSpan offset)
    {
        offset = TimeSpan.Zero;
        if (text == "Z")
        {
            return true;
        }

        Match match = Offset().Match(text);
        if (!match.Success)
        {
            return false;
        }

        int sign = match.Groups[1].Value == "-" ? -1 : 1;
        int hours = Number(match.Groups[2].Value);
        int minutes = match.Groups[3].Success ? Number(match.Groups[3].Value) : 0;
        int seconds = match.Groups[4].Success ? Number(match.Groups[4].Value) : 0;
        if (hours > 23 || minutes > 59 || seconds > 59)
        {
            return false;
        }

        offset = sign * new TimeSpan(hours, minutes, seconds);
        return true;
    }

    private static int Number(string digits) => int.Parse(digits, NumberStyles.None, CultureInfo.InvariantCulture);

    [GeneratedRegex("^([0-9]{4})-([0-9]{2})-([0-9]{2})")]
    private static partial Regex CalendarDate();

    [GeneratedRegex("^([0-9]{4})([0-9]{2})([0-9]{2})")]
    private static partial Regex BasicDate();

    [GeneratedRegex("^([0-9]{4})-?W([0-9]{2})(?:-?([0-9]))?")]
    private static partial Regex WeekDate();

    [GeneratedRegex("^([0-9]{2})(?::([0-9]{2})(?::([0-9]{2})(?:[.,]([0-9]+))?)?)?$")]
    private static partial Regex ExtendedTime();

    [GeneratedRegex("^([0-9]{2})(?:([0-9]{2})(?:([0-9]{2})(?:[.,]([0-9]+))?)?)?$")]
    private static partial Regex BasicTime();

    [GeneratedRegex("^([+-])([0-9]{2})(?::?([0-9]{2})(?::?([0-9]{2})(?:[.,][0-9]+)?)?)?$")]
    private static partial Regex Offset();
}
