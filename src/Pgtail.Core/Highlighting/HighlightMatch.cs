namespace Pgtail.Highlighting;

/// <summary>
/// A range of text a highlighter wants styled.
/// </summary>
/// <param name="Start">The first character.</param>
/// <param name="End">The character just past the range.</param>
/// <param name="Style">A theme element name such as <c>hl_timestamp_date</c>, or a style string such as <c>bold red</c>.</param>
public readonly record struct HighlightMatch(int Start, int End, string Style);
