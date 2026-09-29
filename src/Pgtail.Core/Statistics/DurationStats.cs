using System.Globalization;

namespace Pgtail.Statistics;

/// <summary>
/// Query durations observed during a session.
/// </summary>
public sealed class DurationStats
{
    private readonly List<double> _samples = [];
    private double _sum;
    private double _min = double.PositiveInfinity;
    private double[]? _sorted;

    /// <summary>
    /// The samples in the order they were seen.
    /// </summary>
    public IReadOnlyList<double> Samples => _samples;

    /// <summary>
    /// The number of samples.
    /// </summary>
    public int Count => _samples.Count;

    /// <summary>
    /// Whether no sample has been seen.
    /// </summary>
    public bool IsEmpty => _samples.Count == 0;

    /// <summary>
    /// The mean duration in milliseconds, or zero.
    /// </summary>
    public double Average => IsEmpty ? 0 : _sum / Count;

    /// <summary>
    /// The shortest duration in milliseconds, or zero.
    /// </summary>
    public double Min => IsEmpty ? 0 : _min;

    /// <summary>
    /// The longest duration in milliseconds, or zero.
    /// </summary>
    public double Max { get; private set; }

    /// <summary>
    /// The median duration.
    /// </summary>
    public double P50 => Percentile(0.50);

    /// <summary>
    /// The 95th percentile duration.
    /// </summary>
    public double P95 => Percentile(0.95);

    /// <summary>
    /// The 99th percentile duration.
    /// </summary>
    public double P99 => Percentile(0.99);

    /// <summary>
    /// Records a duration.
    /// </summary>
    /// <param name="durationMs">The duration in milliseconds.</param>
    public void Add(double durationMs)
    {
        _samples.Add(durationMs);
        _sum += durationMs;
        _min = Math.Min(_min, durationMs);
        Max = Math.Max(Max, durationMs);
        _sorted = null;
    }

    /// <summary>
    /// Forgets every sample.
    /// </summary>
    public void Clear()
    {
        _samples.Clear();
        _sum = 0;
        _min = double.PositiveInfinity;
        Max = 0;
        _sorted = null;
    }

    /// <summary>
    /// A percentile by linear interpolation between the nearest samples.
    /// </summary>
    /// <param name="p">The percentile as a fraction from 0 to 1.</param>
    /// <returns>The duration, or zero without samples.</returns>
    public double Percentile(double p)
    {
        if (IsEmpty)
        {
            return 0;
        }

        if (Count == 1)
        {
            return _samples[0];
        }

        _sorted ??= [.. _samples.Order()];
        var index = p * (_sorted.Length - 1);
        var lower = (int)index;
        var upper = Math.Min(lower + 1, _sorted.Length - 1);
        return _sorted[lower] + ((index - lower) * (_sorted[upper] - _sorted[lower]));
    }

    /// <summary>
    /// The statistics as the <c>stats</c> command prints them.
    /// </summary>
    /// <returns>The summary.</returns>
    public string FormatSummary() => string.Create(CultureInfo.InvariantCulture,
        $"""
        Query Duration Statistics
        ─────────────────────────
          Queries:  {Count:N0}
          Average:  {Average:F1}ms

          Percentiles:
            p50:    {P50:F1}ms
            p95:    {P95:F1}ms
            p99:    {P99:F1}ms
            max:    {Max:F1}ms
        """);
}
