namespace Pgtail.Parsing;

/// <summary>
/// Joins the lines that continue a text log entry, such as its <c>DETAIL:</c> and <c>STATEMENT:</c> lines, to it.
/// </summary>
/// <remarks>
/// Entries are added as lines are read. Each entry is held until the next one shows it is complete, or until the end of
/// a read, since PostgreSQL writes a message and its continuation lines together. A labeled line continues only the
/// entry of the same backend; a tab-indented line continues whatever came before it.
/// </remarks>
public sealed class EntryGrouper
{
    private LogEntry? _pending;

    /// <summary>
    /// Adds the next entry read.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The entry this one shows to be complete, or null.</returns>
    public LogEntry? Add(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (_pending is { Format: LogFormat.Text } pending && entry.Continues && (entry.Pid is null || entry.Pid == pending.Pid))
        {
            _pending = pending.Join(entry);
            return null;
        }

        var complete = _pending;
        _pending = entry;
        return complete;
    }

    /// <summary>
    /// Takes the entry held back, at the end of a read.
    /// </summary>
    /// <returns>The entry, or null.</returns>
    public LogEntry? Flush()
    {
        var pending = _pending;
        _pending = null;
        return pending;
    }
}
