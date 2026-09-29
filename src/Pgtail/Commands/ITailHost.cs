using Pgtail.Parsing;

namespace Pgtail.Commands;

/// <summary>
/// What tail mode commands can ask of the full screen tail view beyond printing into the log.
/// </summary>
internal interface ITailHost : ICommandHost
{
    /// <summary>
    /// The entries read so far, oldest first, up to the buffer limit.
    /// </summary>
    IReadOnlyList<LogEntry> Entries { get; }

    /// <summary>
    /// The format detected in the log, or null before the first entry.
    /// </summary>
    LogFormat? Format { get; }

    /// <summary>
    /// Leaves tail mode.
    /// </summary>
    void Stop();

    /// <summary>
    /// Freezes the log; new entries are counted but not shown.
    /// </summary>
    void Pause();

    /// <summary>
    /// Shows entries that arrived while paused and follows new ones.
    /// </summary>
    void Follow();

    /// <summary>
    /// Redraws the log from the stored entries with the current filters, theme, and highlighting.
    /// </summary>
    /// <remarks>
    /// The command's output appears after the redrawn entries.
    /// </remarks>
    void Rebuild();

    /// <summary>
    /// Restores the filters tail mode started with and redraws the log.
    /// </summary>
    void ResetToAnchor();

    /// <summary>
    /// Clears every filter and every stored entry.
    /// </summary>
    void ClearEverything();

    /// <summary>
    /// Shows the filters and slow query threshold in the status bar again after they change.
    /// </summary>
    void RefreshStatus();
}
