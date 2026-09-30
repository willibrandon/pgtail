namespace Pgtail.Display;

/// <summary>
/// The display mode and output format chosen with <c>display</c> and <c>output</c>.
/// </summary>
public sealed class DisplayState
{
    /// <summary>
    /// The display mode.
    /// </summary>
    public DisplayMode Mode { get; private set; } = DisplayMode.Compact;

    /// <summary>
    /// The fields shown in custom mode, in the order given.
    /// </summary>
    public IReadOnlyList<string> CustomFields { get; private set; } = [];

    /// <summary>
    /// The output format.
    /// </summary>
    public OutputFormat OutputFormat { get; set; } = OutputFormat.Text;

    /// <summary>
    /// Shows one line per entry.
    /// </summary>
    public void SetCompact() => Mode = DisplayMode.Compact;

    /// <summary>
    /// Shows every available field.
    /// </summary>
    public void SetFull() => Mode = DisplayMode.Full;

    /// <summary>
    /// Shows only the given fields, when at least one of them is valid.
    /// </summary>
    /// <param name="fields">The field names.</param>
    /// <returns>The names that are not valid fields.</returns>
    public IReadOnlyList<string> SetCustom(IReadOnlyList<string> fields)
    {
        ArgumentNullException.ThrowIfNull(fields);
        var valid = fields.Where(DisplayFields.IsValid).ToList();
        if (valid.Count > 0)
        {
            Mode = DisplayMode.Custom;
            CustomFields = valid;
        }

        return [.. fields.Where(field => !DisplayFields.IsValid(field))];
    }

    /// <summary>
    /// Describes the settings, as in <c>Display: compact, Output: text</c>.
    /// </summary>
    /// <returns>The description.</returns>
    public string FormatStatus()
    {
        string mode = Mode switch
        {
            DisplayMode.Full => "full",
            DisplayMode.Custom when CustomFields.Count > 0 => $"custom({string.Join(',', CustomFields)})",
            DisplayMode.Custom => "custom",
            _ => "compact",
        };

        string output = OutputFormat == OutputFormat.Json ? "json" : "text";
        return $"Display: {mode}, Output: {output}";
    }
}
