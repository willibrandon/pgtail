using System.Globalization;

namespace Pgtail.Statistics;

/// <summary>
/// The thresholds that mark queries as slow.
/// </summary>
public sealed class SlowQueryConfig
{
    /// <summary>
    /// The default warning threshold in milliseconds.
    /// </summary>
    public const double DefaultWarningMs = 100;

    /// <summary>
    /// The default slow threshold in milliseconds.
    /// </summary>
    public const double DefaultSlowMs = 500;

    /// <summary>
    /// The default critical threshold in milliseconds.
    /// </summary>
    public const double DefaultCriticalMs = 1000;

    /// <summary>
    /// Whether slow query highlighting is on.
    /// </summary>
    public bool Enabled { get; set; }

    /// <summary>
    /// The warning threshold in milliseconds.
    /// </summary>
    public double WarningMs { get; set; } = DefaultWarningMs;

    /// <summary>
    /// The slow threshold in milliseconds.
    /// </summary>
    public double SlowMs { get; set; } = DefaultSlowMs;

    /// <summary>
    /// The critical threshold in milliseconds.
    /// </summary>
    public double CriticalMs { get; set; } = DefaultCriticalMs;

    /// <summary>
    /// Checks that thresholds are positive and ascending.
    /// </summary>
    /// <param name="warning">The warning threshold.</param>
    /// <param name="slow">The slow threshold.</param>
    /// <param name="critical">The critical threshold.</param>
    /// <returns>The problem, or null when the thresholds are valid.</returns>
    public static string? Validate(double warning, double slow, double critical)
    {
        if (warning <= 0 || slow <= 0 || critical <= 0)
        {
            return "All thresholds must be positive numbers";
        }

        return warning < slow && slow < critical ? null : "Thresholds must be in ascending order: warning < slow < critical";
    }

    /// <summary>
    /// The level a duration reaches.
    /// </summary>
    /// <param name="durationMs">The duration in milliseconds.</param>
    /// <returns>The highest threshold exceeded, or null.</returns>
    public SlowQueryLevel? GetLevel(double durationMs)
    {
        if (durationMs > CriticalMs)
        {
            return SlowQueryLevel.Critical;
        }

        if (durationMs > SlowMs)
        {
            return SlowQueryLevel.Slow;
        }

        return durationMs > WarningMs ? SlowQueryLevel.Warning : null;
    }

    /// <summary>
    /// Lists the thresholds with the colors they are shown in.
    /// </summary>
    /// <returns>Three indented lines.</returns>
    public string FormatThresholds() => string.Create(CultureInfo.InvariantCulture,
        $"  Warning (yellow):      > {WarningMs:F0}ms\n  Slow (yellow bold):    > {SlowMs:F0}ms\n")
        + string.Create(CultureInfo.InvariantCulture, $"  Critical (red bold):   > {CriticalMs:F0}ms");
}
