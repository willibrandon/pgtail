namespace Pgtail.Exporting;

/// <summary>
/// Reads export format names.
/// </summary>
public static class ExportFormats
{
    /// <summary>
    /// Reads <c>text</c>, <c>json</c>, or <c>csv</c>, ignoring case.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>The format.</returns>
    /// <exception cref="FormatException">The name is not a format; the message lists the valid ones.</exception>
    public static ExportFormat Parse(string name)
    {
        ArgumentNullException.ThrowIfNull(name);
        return name.ToLowerInvariant() switch
        {
            "text" => ExportFormat.Text,
            "json" => ExportFormat.Json,
            "csv" => ExportFormat.Csv,
            _ => throw new FormatException($"Unknown format '{name}'. Valid formats: text, json, csv"),
        };
    }
}
