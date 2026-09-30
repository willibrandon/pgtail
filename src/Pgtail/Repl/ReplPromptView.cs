using Hex1b;
using Hex1b.Composition;
using Hex1b.Surfaces;
using Hex1b.Widgets;
using Pgtail.Commands;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Repl;

/// <summary>
/// Draws the REPL prompt.
/// </summary>
/// <remarks>
/// The label and line come first, the completion menu opens under the word being completed, and the toolbar sits on
/// the bottom row of the terminal.
/// </remarks>
/// <param name="Controller">The prompt's key handling and state.</param>
/// <param name="Label">The prompt label, such as <c>pgtail&gt; </c>.</param>
/// <param name="Toolbar">The toolbar text.</param>
/// <param name="Width">The terminal width.</param>
/// <param name="Height">The rows the prompt occupies, down to the bottom of the terminal.</param>
/// <param name="Color">False to drop colors, for <c>NO_COLOR</c>.</param>
internal sealed record ReplPromptView(
    PromptController Controller,
    StyledText Label,
    StyledText Toolbar,
    int Width,
    int Height,
    bool Color) : Hex1bWidget
{
    private static readonly TextStyle s_item = StyleParser.Parse("fg:#000000 bg:#bbbbbb");
    private static readonly TextStyle s_currentItem = StyleParser.Parse("fg:#888888 bg:#ffffff reverse");
    private static readonly TextStyle s_meta = StyleParser.Parse("fg:#000000 bg:#999999");
    private static readonly TextStyle s_currentMeta = StyleParser.Parse("fg:#000000 bg:#aaaaaa");
    private static readonly TextStyle s_searchLabel = StyleParser.Parse("fg:#888888");

    /// <summary>
    /// The most rows the line wraps onto before scrolling.
    /// </summary>
    public const int MaxEditorRows = 4;

    /// <summary>
    /// Builds the prompt.
    /// </summary>
    /// <param name="ctx">The composition context.</param>
    /// <returns>The widget tree.</returns>
    protected override Hex1bWidget Build(CompositionContext ctx)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // A terminal sends pasted text as one event rather than as keys. It is read off this thread, so it is queued and
        // put into the line here, where the line is drawn.
        Controller.ApplyPastes();
        return ctx.Pastable(BuildPrompt(ctx)).OnPaste(async paste => Controller.Paste(await paste.Paste.ReadToEndAsync()));
    }

    private VStackWidget BuildPrompt(CompositionContext ctx)
    {
        PromptState state = Controller.State;
        if (Controller.Search is { } search)
        {
            return BuildSearch(ctx, state, search);
        }

        List<StyledSpan> labelRow = StyledTextFolder.Fold(Label, 0)[0];
        int labelWidth = StyledTextFolder.Width(labelRow);
        int editorWidth = Math.Max(1, Width - labelWidth);
        int textWidth = DisplayWidth.GetStringWidth(state.Text) + 1;
        int editorRows = Math.Clamp((textWidth + editorWidth - 1) / editorWidth, 1, MaxEditorRows);
        int menuRows = state.MenuVisible ? Math.Min(PromptState.MenuRows, state.Candidates.Count) : 0;
        int height = Math.Max(Height, editorRows + menuRows + 1);
        return ctx.VStack(v =>
        {
            var children = new List<Hex1bWidget>
            {
                v.HStack(h =>
                [
                    h.Surface(s => [s.Layer(surface => StyledBlock.DrawRow(surface, 0, 0, labelRow, Color))])
                        .Size(Math.Max(1, labelWidth), 1),
                    h.Editor(state.Editor)
                        .WordWrap()
                        .OnTextChanged(_ => Controller.TextChanged())
                        .InputBindings(Controller.Bind)
                        .FixedHeight(editorRows)
                        .FillWidth(),
                ]).FixedHeight(editorRows),
            };

            if (menuRows > 0)
            {
                int anchor = labelWidth + DisplayWidth.GetStringWidth(state.Text[..Math.Min(state.CompletionStart, state.Text.Length)]);
                children.Add(v.Surface(s => [s.Layer(surface => DrawMenu(surface, state, anchor, menuRows))]).Size(Width, menuRows));
            }

            children.Add(v.Text("").FillHeight());
            List<StyledSpan> toolbarRow = StyledTextFolder.Fold(Toolbar, 0)[0];
            children.Add(v.Surface(s => [s.Layer(surface => DrawToolbar(surface, toolbarRow))]).Size(Width, 1));
            return [.. children];
        }).FixedHeight(height);
    }

    // The search reads as it does in a shell: (reverse-i-search)`text': command found
    private VStackWidget BuildSearch(CompositionContext ctx, PromptState state, HistorySearch search)
    {
        StyledText label = new StyledText().Append("(reverse-i-search)`", s_searchLabel);
        List<StyledSpan> labelRow = StyledTextFolder.Fold(label, 0)[0];
        int labelWidth = StyledTextFolder.Width(labelRow);
        int queryWidth = Math.Min(Math.Max(1, Width - labelWidth - 3), DisplayWidth.GetStringWidth(state.Text) + 1);
        StyledText found = new StyledText().Append("': ", s_searchLabel).Append(search.Match ?? "");
        List<StyledSpan> foundRow = StyledTextFolder.Fold(found, 0)[0];
        List<StyledSpan> toolbarRow = StyledTextFolder.Fold(Toolbar, 0)[0];
        return ctx.VStack(v =>
        [
            v.HStack(h =>
            [
                h.Surface(s => [s.Layer(surface => StyledBlock.DrawRow(surface, 0, 0, labelRow, Color))]).Size(labelWidth, 1),
                h.Editor(state.Editor)
                    .OnTextChanged(_ => Controller.TextChanged())
                    .InputBindings(Controller.Bind)
                    .FixedWidth(queryWidth)
                    .FixedHeight(1),
                h.Surface(s => [s.Layer(surface => StyledBlock.DrawRow(surface, 0, 0, foundRow, Color))])
                    .Size(Math.Max(1, Width - labelWidth - queryWidth), 1),
            ]).FixedHeight(1),
            v.Text("").FillHeight(),
            v.Surface(s => [s.Layer(surface => DrawToolbar(surface, toolbarRow))]).Size(Width, 1),
        ]).FixedHeight(Math.Max(Height, 2));
    }

    private void DrawMenu(Surface surface, PromptState state, int anchor, int rows)
    {
        var shown = state.Candidates.Skip(state.MenuTop).Take(rows).ToList();
        int labelColumn = shown.Max(item => DisplayWidth.GetStringWidth(item.Label));
        int metaColumn = shown.Max(item => DisplayWidth.GetStringWidth(item.Description));
        int menuWidth = labelColumn + 2 + (metaColumn > 0 ? metaColumn + 2 : 0);
        if (menuWidth > Width)
        {
            metaColumn = Math.Max(0, metaColumn - (menuWidth - Width));
            menuWidth = Math.Min(Width, labelColumn + 2 + (metaColumn > 0 ? metaColumn + 2 : 0));
        }

        int x = Math.Clamp(anchor, 0, Math.Max(0, Width - menuWidth));
        for (int row = 0; row < shown.Count; row++)
        {
            CompletionItem item = shown[row];
            bool current = state.MenuTop + row == state.Selected;
            string label = Pad(" " + item.Label, labelColumn + 2);
            int column = StyledBlock.DrawRow(surface, x, row, [new StyledSpan(label, current ? s_currentItem : s_item)], Color);
            if (metaColumn > 0)
            {
                string meta = Pad(" " + Truncate(item.Description, metaColumn), metaColumn + 2);
                _ = StyledBlock.DrawRow(surface, column, row, [new StyledSpan(meta, current ? s_currentMeta : s_meta)], Color);
            }
        }
    }

    private void DrawToolbar(Surface surface, List<StyledSpan> row)
    {
        int end = StyledBlock.DrawRow(surface, 0, 0, row, Color);
        TextStyle fill = row.Count > 0 ? row[^1].Style with { Attributes = TextAttributes.None } : TextStyle.Plain;
        if (end < Width)
        {
            _ = StyledBlock.DrawRow(surface, end, 0, [new StyledSpan(new string(' ', Width - end), fill)], Color);
        }
    }

    private static string Pad(string text, int width)
    {
        int textWidth = DisplayWidth.GetStringWidth(text);
        return textWidth >= width ? text : text + new string(' ', width - textWidth);
    }

    private static string Truncate(string text, int width)
    {
        if (DisplayWidth.GetStringWidth(text) <= width)
        {
            return text;
        }

        (string? slice, int _, int _, int _) = DisplayWidth.SliceByDisplayWidth(text, 0, Math.Max(0, width - 1));
        return slice + "…";
    }
}
