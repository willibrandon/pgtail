namespace Pgtail.Parsing;

/// <summary>
/// Names of the log formats.
/// </summary>
public static class LogFormats
{
    /// <summary>
    /// The short name of a format: <c>text</c>, <c>csv</c>, or <c>json</c>.
    /// </summary>
    /// <param name="format">The format.</param>
    /// <returns>The name.</returns>
    public static string ToName(this LogFormat format) => format switch
    {
        LogFormat.Csv => "csv",
        LogFormat.Json => "json",
        _ => "text",
    };

    /// <summary>
    /// The PostgreSQL <c>log_destination</c> name of a format: <c>text</c>, <c>csvlog</c>, or <c>jsonlog</c>.
    /// </summary>
    /// <param name="format">The format.</param>
    /// <returns>The name.</returns>
    public static string ToDestinationName(this LogFormat format) => format switch
    {
        LogFormat.Csv => "csvlog",
        LogFormat.Json => "jsonlog",
        _ => "text",
    };
}
