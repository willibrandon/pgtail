namespace Pgtail.Commands;

/// <summary>
/// How options are offered while completing.
/// </summary>
internal enum CompletionStyle
{
    /// <summary>
    /// The REPL menu: options appear on an empty word alongside other values; short options once a dash is typed.
    /// </summary>
    Menu,

    /// <summary>
    /// Tail mode's inline suggestion: options appear only once <c>--</c> is typed.
    /// </summary>
    Inline,
}
