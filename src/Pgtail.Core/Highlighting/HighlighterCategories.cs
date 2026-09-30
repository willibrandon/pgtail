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

}
