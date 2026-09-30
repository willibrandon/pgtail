namespace Pgtail.Parsing;

/// <summary>
/// The PostgreSQL log destinations pgtail can read.
/// </summary>
public enum LogFormat
{
    /// <summary>
    /// The plain text stderr format.
    /// </summary>
    Text,

    /// <summary>
    /// The csvlog format.
    /// </summary>
    Csv,

    /// <summary>
    /// The jsonlog format of PostgreSQL 15 and later.
    /// </summary>
    Json,
}
