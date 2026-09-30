namespace Pgtail.Highlighting;

/// <summary>
/// Remembers which ranges of a text are already styled, so later highlighters cannot style over them.
/// </summary>
/// <param name="length">The length of the text.</param>
public sealed class OccupancyTracker(int length)
{
    private readonly List<(int Start, int End)> _ranges = [];

    /// <summary>
    /// Whether no character of a range is taken.
    /// </summary>
    /// <param name="start">The first character.</param>
    /// <param name="end">The character just past the range.</param>
    /// <returns>True when the whole range is free and inside the text.</returns>
    public bool IsAvailable(int start, int end)
    {
        if (start < 0 || end > length || start >= end)
        {
            return false;
        }

        int low = 0;
        int high = _ranges.Count;
        while (low < high)
        {
            int middle = (low + high) / 2;
            if (_ranges[middle].End <= start)
            {
                low = middle + 1;
            }
            else
            {
                high = middle;
            }
        }

        return low >= _ranges.Count || _ranges[low].Start >= end;
    }

    /// <summary>
    /// Marks a range as taken.
    /// </summary>
    /// <param name="start">The first character.</param>
    /// <param name="end">The character just past the range.</param>
    public void MarkOccupied(int start, int end)
    {
        if (start < 0 || end > length || start >= end)
        {
            return;
        }

        if (_ranges.Count == 0 || start >= _ranges[^1].Start)
        {
            _ranges.Add((start, end));
            return;
        }

        int low = 0;
        int high = _ranges.Count;
        while (low < high)
        {
            int middle = (low + high) / 2;
            if (_ranges[middle].Start < start)
            {
                low = middle + 1;
            }
            else
            {
                high = middle;
            }
        }

        _ranges.Insert(low, (start, end));
    }
}
