namespace Pgtail.Tailing;

/// <summary>
/// What a log source reports.
/// </summary>
public enum LogSourceEventKind
{
    /// <summary>
    /// An entry was read.
    /// </summary>
    Entry,

    /// <summary>
    /// The format of a file was detected from its first line.
    /// </summary>
    FormatDetected,

    /// <summary>
    /// The source moved to a newer log file after a restart or rotation.
    /// </summary>
    FileSwitched,

    /// <summary>
    /// Piped input ended.
    /// </summary>
    EndOfInput,

    /// <summary>
    /// Everything the source found when it started has been read, so later entries are new.
    /// </summary>
    CaughtUp,

    /// <summary>
    /// Entries logged before everything read so far, read back in the background after catching up.
    /// </summary>
    Older,

    /// <summary>
    /// Reading back older entries ended: the start of the file or of the time filter was reached, or it was stopped.
    /// </summary>
    OlderRead,
}
