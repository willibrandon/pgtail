using Hex1b.Documents;
using Hex1b.Theming;

namespace Pgtail.Tail;

/// <summary>
/// Shows the grey suggestion after the text typed.
/// </summary>
internal sealed class TailInputHints : ITextDecorationProvider
{
    private static readonly TextDecoration Grey = new() { Foreground = Hex1bColor.FromBright(0, 128, 128, 128) };
    private IEditorSession? _session;
    private (int Column, string Text)? _shown;
    private (int Column, string Text)? _wanted;

    /// <inheritdoc/>
    public void Activate(IEditorSession session)
    {
        _session = session;
        _shown = null;
        Push();
    }

    /// <inheritdoc/>
    public void Deactivate() => _session = null;

    /// <inheritdoc/>
    public IReadOnlyList<TextDecorationSpan> GetDecorations(int startLine, int endLine, IHex1bDocument document) => [];

    /// <summary>
    /// Shows grey text at a column of the line, or nothing.
    /// </summary>
    /// <param name="column">The column, counting from zero.</param>
    /// <param name="text">The text, or null to show nothing.</param>
    public void Show(int column, string? text)
    {
        _wanted = text is { Length: > 0 } ? (column, text) : null;
        Push();
    }

    private void Push()
    {
        var next = _wanted;
        if (next == _shown || _session is not { } session)
        {
            return;
        }

        _shown = next;
        if (next is { } hint)
        {
            session.PushInlineHints([new InlineHint(new DocumentPosition(1, hint.Column + 1), hint.Text, Grey)]);
        }
        else
        {
            session.ClearInlineHints();
        }
    }
}
