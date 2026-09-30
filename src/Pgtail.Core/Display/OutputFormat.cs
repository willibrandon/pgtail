namespace Pgtail.Display;

/// <summary>
/// How log entries are written.
/// </summary>
public enum OutputFormat
{
    /// <summary>
    /// Colored, human-readable text.
    /// </summary>
    Text,

    /// <summary>
    /// One JSON object per line.
    /// </summary>
    Json,
}
