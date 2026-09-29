using Hex1b;
using Hex1b.Documents;
using Hex1b.Layout;
using Hex1b.Widgets;

namespace Pgtail.Tail;

/// <summary>
/// Draws the tail log with Hex1b's text renderer, leaving the rows past the last line blank.
/// </summary>
/// <remarks>
/// The stock renderer marks rows past the end of a document with <c>~</c>, as vim does; a log that has not filled
/// the screen yet should just be empty there.
/// </remarks>
internal sealed class LogViewRenderer : IEditorViewRenderer
{
    private static readonly TextEditorViewRenderer Inner = TextEditorViewRenderer.Instance;

    /// <inheritdoc/>
    public void Render(
        Hex1bRenderContext context,
        EditorState state,
        Rect viewport,
        int scrollOffset,
        int horizontalScrollOffset,
        bool isFocused,
        char? pendingNibble = null,
        IReadOnlyList<ITextDecorationProvider>? decorationProviders = null,
        IReadOnlyList<InlineHint>? inlineHints = null,
        bool wordWrap = false,
        IReadOnlyList<FoldingRegion>? foldingRegions = null)
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(state);
        var lines = Math.Clamp(state.Document.LineCount - scrollOffset + 1, 0, viewport.Height);
        if (lines > 0)
        {
            Inner.Render(context, state, new Rect(viewport.X, viewport.Y, viewport.Width, lines), scrollOffset, horizontalScrollOffset,
                isFocused, pendingNibble, decorationProviders, inlineHints, wordWrap, foldingRegions);
        }

        var blank = new string(' ', Math.Max(0, viewport.Width));
        for (var row = lines; row < viewport.Height; row++)
        {
            context.WriteClipped(viewport.X, viewport.Y + row, blank);
        }
    }

    /// <inheritdoc/>
    public DocumentOffset? HitTest(
        int localX,
        int localY,
        EditorState state,
        int viewportColumns,
        int viewportLines,
        int scrollOffset,
        int horizontalScrollOffset) =>
        Inner.HitTest(localX, localY, state, viewportColumns, viewportLines, scrollOffset, horizontalScrollOffset);

    /// <inheritdoc/>
    public int GetTotalLines(IHex1bDocument document, int viewportColumns) => Inner.GetTotalLines(document, viewportColumns);

    /// <inheritdoc/>
    public int GetMaxLineWidth(IHex1bDocument document, int scrollOffset, int viewportLines, int viewportColumns) =>
        Inner.GetMaxLineWidth(document, scrollOffset, viewportLines, viewportColumns);
}
