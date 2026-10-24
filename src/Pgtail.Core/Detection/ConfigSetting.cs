using System.Globalization;

namespace Pgtail.Detection;

/// <summary>
/// A setting the server reads when it starts, and where it is set, as <c>pg_settings</c> shows in its source columns.
/// </summary>
/// <param name="Name">The setting's name as written.</param>
/// <param name="Value">The value, without its quotes and escapes.</param>
/// <param name="File">The file that sets it, or null when the server's command line sets it.</param>
/// <param name="Line">The line of the file, counting from 1, or 0 for the command line.</param>
public sealed record ConfigSetting(string Name, string Value, string? File, int Line)
{
    /// <summary>
    /// Where the setting is set, for messages: a file and a line, or the server's command line.
    /// </summary>
    public string Source => File is null
        ? "the server's command line (postmaster.opts)"
        : string.Create(CultureInfo.InvariantCulture, $"{File} line {Line}");

    /// <summary>
    /// Whether the value is true, as PostgreSQL reads a boolean.
    /// </summary>
    /// <remarks>
    /// True is <c>on</c>, <c>1</c>, or <c>true</c>, <c>yes</c>, or a prefix of either, in any case.
    /// </remarks>
    public bool IsOn
    {
        get
        {
            string value = Value.Trim();
            return value.Length > 0 && (value.Equals("on", StringComparison.OrdinalIgnoreCase) || value == "1"
                || "true".StartsWith(value, StringComparison.OrdinalIgnoreCase)
                || "yes".StartsWith(value, StringComparison.OrdinalIgnoreCase));
        }
    }
}
