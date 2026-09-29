using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Statistics;

/// <summary>
/// Reads query durations from log messages.
/// </summary>
public static partial class DurationExtractor
{
    /// <summary>
    /// Finds <c>duration: 234.567 ms</c> or <c>duration: 1.234 s</c> in a text.
    /// </summary>
    /// <param name="text">The message or line.</param>
    /// <returns>The duration in milliseconds, or null when the text has none.</returns>
    public static double? Extract(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        var match = Duration().Match(text);
        if (!match.Success
            || !double.TryParse(match.Groups[1].ValueSpan, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var value))
        {
            return null;
        }

        if (match.Groups[2].Value.Equals("s", StringComparison.OrdinalIgnoreCase))
        {
            value *= 1000;
        }

        return value < 0 ? null : value;
    }

    [GeneratedRegex(@"duration:\s*([0-9]+\.?[0-9]*)\s*(ms|s)", RegexOptions.IgnoreCase | RegexOptions.CultureInvariant)]
    private static partial Regex Duration();
}
