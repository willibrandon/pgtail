namespace Pgtail.Display;

/// <summary>
/// How much of each log entry is shown.
/// </summary>
public enum DisplayMode
{
    /// <summary>
    /// One line: time, process ID, level, SQLSTATE, and message.
    /// </summary>
    Compact,

    /// <summary>
    /// The compact line followed by every other available field, labeled.
    /// </summary>
    Full,

    /// <summary>
    /// Only the fields the user chose.
    /// </summary>
    Custom,
}
