using System.Globalization;
using System.Text.RegularExpressions;

namespace Pgtail.Highlighting;

/// <summary>
/// Styles millisecond durations by how slow they are.
/// </summary>
/// <param name="slow">The slow threshold in milliseconds.</param>
/// <param name="verySlow">The very slow threshold in milliseconds.</param>
/// <param name="critical">The critical threshold in milliseconds.</param>
public sealed class DurationHighlighter(long slow = 100, long verySlow = 500, long critical = 5000)
    : RegexHighlighter("duration", 300, "", HighlightPatterns.Duration(), "hl_duration_fast")
{
    /// <inheritdoc />
    public override string Description => $"Query durations (slow: {slow}ms, critical: {critical}ms)";

    /// <inheritdoc />
    public override IEnumerable<HighlightMatch> FindMatches(string text)
    {
        foreach (Match match in Regex.Matches(text))
        {
            if (!double.TryParse(match.Groups[1].ValueSpan, NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out var ms))
            {
                continue;
            }

            var style = ms >= critical ? "hl_duration_critical"
                : ms >= verySlow ? "hl_duration_very_slow"
                : ms >= slow ? "hl_duration_slow"
                : "hl_duration_fast";
            yield return new HighlightMatch(match.Index, match.Index + match.Length, style);
        }
    }
}
