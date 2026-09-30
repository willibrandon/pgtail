using System.Globalization;

namespace Pgtail.Statistics;

/// <summary>
/// Reads query durations from log messages.
/// </summary>
/// <remarks>
/// A duration is <c>duration:</c>, in any case, then a number with an optional decimal point and the unit <c>ms</c> or
/// <c>s</c>, with any spaces between them. The first such duration in the text counts. The text is scanned rather than
/// matched with a pattern, since every entry read is checked and most in a log of statement durations have one.
/// </remarks>
public static class DurationExtractor
{
    private const string Label = "duration:";

    /// <summary>
    /// Finds <c>duration: 234.567 ms</c> or <c>duration: 1.234 s</c> in a text.
    /// </summary>
    /// <param name="text">The message or line.</param>
    /// <returns>The duration in milliseconds, or null when the text has none.</returns>
    public static double? Extract(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        for (int at = text.IndexOf(Label, StringComparison.OrdinalIgnoreCase); at >= 0;
            at = text.IndexOf(Label, at + Label.Length, StringComparison.OrdinalIgnoreCase))
        {
            if (Read(text.AsSpan(at + Label.Length)) is { } duration)
            {
                return duration;
            }
        }

        return null;
    }

    // The number and unit after a label, in milliseconds, or null when they are not there.
    private static double? Read(ReadOnlySpan<char> rest)
    {
        rest = rest.TrimStart();
        int length = Digits(rest, 0);
        if (length == 0)
        {
            return null;
        }

        if (length < rest.Length && rest[length] == '.')
        {
            length = Digits(rest, length + 1);
        }

        ReadOnlySpan<char> unit = rest[length..].TrimStart();
        bool milliseconds = unit.StartsWith("ms", StringComparison.OrdinalIgnoreCase);
        if ((!milliseconds && !unit.StartsWith("s", StringComparison.OrdinalIgnoreCase))
            || !double.TryParse(rest[..length], NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out double value))
        {
            return null;
        }

        return milliseconds ? value : value * 1000;
    }

    // Where the run of digits starting at an index ends.
    private static int Digits(ReadOnlySpan<char> text, int start)
    {
        int end = start;
        while (end < text.Length && char.IsAsciiDigit(text[end]))
        {
            end++;
        }

        return end;
    }
}
