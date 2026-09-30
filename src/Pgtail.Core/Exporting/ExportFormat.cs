namespace Pgtail.Exporting;

/// <summary>
/// How exported entries are written.
/// </summary>
public enum ExportFormat
{
    /// <summary>
    /// The original log lines.
    /// </summary>
    Text,

    /// <summary>
    /// JSON Lines with the time, level, process ID, and message.
    /// </summary>
    Json,

    /// <summary>
    /// CSV with a header row.
    /// </summary>
    Csv,
}
