namespace Pgtail.Tailing;

/// <summary>
/// How a read of a log file went.
/// </summary>
public enum ReadOutcome
{
    /// <summary>
    /// The file was read.
    /// </summary>
    Read,

    /// <summary>
    /// The file does not exist or cannot be opened.
    /// </summary>
    Unavailable,

    /// <summary>
    /// The file exists but this user may not read it.
    /// </summary>
    PermissionDenied,
}
