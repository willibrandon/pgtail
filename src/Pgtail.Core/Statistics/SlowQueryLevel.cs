namespace Pgtail.Statistics;

/// <summary>
/// How far a query's duration is over the slow query thresholds.
/// </summary>
public enum SlowQueryLevel
{
    /// <summary>
    /// Over the warning threshold.
    /// </summary>
    Warning,

    /// <summary>
    /// Over the slow threshold.
    /// </summary>
    Slow,

    /// <summary>
    /// Over the critical threshold.
    /// </summary>
    Critical,
}
