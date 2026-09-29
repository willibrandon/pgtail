namespace Pgtail.Highlighting;

/// <summary>
/// The categories highlighters are grouped in, by priority range.
/// </summary>
public static class HighlighterCategories
{
    /// <summary>
    /// The categories in display order.
    /// </summary>
    public static IReadOnlyList<string> Ordered { get; } =
        ["structural", "diagnostic", "performance", "objects", "wal", "connection", "sql", "lock", "checkpoint", "misc"];

    /// <summary>
    /// The category of a priority.
    /// </summary>
    /// <param name="priority">The priority.</param>
    /// <returns>The category name.</returns>
    public static string ForPriority(int priority) => priority switch
    {
        < 200 => "structural",
        < 300 => "diagnostic",
        < 400 => "performance",
        < 500 => "objects",
        < 600 => "wal",
        < 700 => "connection",
        < 800 => "sql",
        < 900 => "lock",
        < 1000 => "checkpoint",
        _ => "misc",
    };
}
