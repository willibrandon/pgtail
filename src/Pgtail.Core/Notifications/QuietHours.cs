using System.Globalization;

namespace Pgtail.Notifications;

/// <summary>
/// A daily time range during which notifications are held back, which may span midnight.
/// </summary>
/// <param name="Start">When quiet hours begin.</param>
/// <param name="End">When quiet hours end, inclusive.</param>
public sealed record QuietHours(TimeOnly Start, TimeOnly End)
{
    private const string FormatHint = "Invalid format. Use: HH:MM-HH:MM";

    /// <summary>
    /// Whether a local time falls within quiet hours.
    /// </summary>
    /// <param name="now">The local time.</param>
    /// <returns>True when notifications are held back.</returns>
    public bool IsActive(DateTime now)
    {
        var current = TimeOnly.FromDateTime(now);
        return Start <= End ? current >= Start && current <= End : current >= Start || current <= End;
    }

    /// <summary>
    /// Reads a range such as <c>22:00-08:00</c>.
    /// </summary>
    /// <param name="text">The range.</param>
    /// <returns>The quiet hours.</returns>
    /// <exception cref="FormatException">The text is not a valid range; the message says why.</exception>
    public static QuietHours Parse(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var parts = text.Split('-');
        if (parts.Length != 2)
        {
            throw new FormatException(FormatHint);
        }

        return new QuietHours(ParseTime(parts[0].Trim()), ParseTime(parts[1].Trim()));
    }

    /// <summary>
    /// The range as <c>HH:MM-HH:MM</c>.
    /// </summary>
    /// <returns>The text.</returns>
    public override string ToString() =>
        $"{Start.ToString("HH:mm", CultureInfo.InvariantCulture)}-{End.ToString("HH:mm", CultureInfo.InvariantCulture)}";

    private static TimeOnly ParseTime(string text)
    {
        var parts = text.Split(':');
        if (parts.Length != 2
            || !int.TryParse(parts[0], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var hour)
            || !int.TryParse(parts[1], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var minute))
        {
            throw new FormatException(FormatHint);
        }

        if (hour is < 0 or > 23 || minute is < 0 or > 59)
        {
            throw new FormatException($"Invalid time: {text}");
        }

        return new TimeOnly(hour, minute);
    }
}
