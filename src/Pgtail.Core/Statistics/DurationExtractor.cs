using System.Globalization;
using Pgtail.Matching;
using Scout.Text.Regex;

namespace Pgtail.Statistics;

/// <summary>
/// Reads query durations from log messages.
/// </summary>
public static class DurationExtractor
{
    private static readonly ByteRegex Duration = ByteRegex.Compile(@"(?i)duration:\s*([0-9]+\.?[0-9]*)\s*(ms|s)");

    /// <summary>
    /// Finds <c>duration: 234.567 ms</c> or <c>duration: 1.234 s</c> in a text.
    /// </summary>
    /// <param name="text">The message or line.</param>
    /// <returns>The duration in milliseconds, or null when the text has none.</returns>
    public static double? Extract(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        using var utf8 = new Utf8Text(text);
        if (Duration.FindCaptures(utf8.Bytes) is not { } captures || captures.GetGroup(1) is not { } number
            || !double.TryParse(number.Value(utf8.Bytes), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var value))
        {
            return null;
        }

        if (captures.GetGroup(2) is { Length: 1 })
        {
            value *= 1000;
        }

        return value < 0 ? null : value;
    }
}
