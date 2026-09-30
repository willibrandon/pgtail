using Pgtail.Parsing;

namespace Pgtail.Sessions;

/// <summary>
/// The most recent entries of a tail, kept after tail mode ends for <c>export</c> and <c>pipe</c>.
/// </summary>
/// <param name="capacity">The number of entries kept; older ones are dropped first.</param>
public sealed class LogBuffer(int capacity = LogBuffer.DefaultCapacity)
{
    /// <summary>
    /// The number of entries kept by default.
    /// </summary>
    public const int DefaultCapacity = 10_000;

    private readonly Queue<LogEntry> _entries = new();

    /// <summary>
    /// The number of entries kept.
    /// </summary>
    public int Capacity { get; } = capacity;

    /// <summary>
    /// The number of entries held.
    /// </summary>
    public int Count => _entries.Count;

    /// <summary>
    /// Adds an entry, dropping the oldest when full.
    /// </summary>
    /// <param name="entry">The entry.</param>
    public void Add(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (_entries.Count == Capacity)
        {
            _ = _entries.Dequeue();
        }

        _entries.Enqueue(entry);
    }

    /// <summary>
    /// Removes every entry.
    /// </summary>
    public void Clear() => _entries.Clear();

    /// <summary>
    /// The entries, oldest first.
    /// </summary>
    /// <returns>A copy of the entries.</returns>
    public IReadOnlyList<LogEntry> Snapshot() => [.. _entries];
}
