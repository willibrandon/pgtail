using Hex1b;
using Hex1b.Surfaces;
using Hex1b.Widgets;
using Pgtail.Styling;

namespace Pgtail.Rendering;

/// <summary>
/// Renders lines of styled text as a Hex1b widget.
/// </summary>
internal static class StyledBlock
{
    private static readonly IReadOnlyList<List<StyledSpan>> EmptyRows = [[]];

    /// <summary>
    /// Builds a widget that draws the lines folded to a width.
    /// </summary>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="lines">The lines.</param>
    /// <param name="width">The width to fold at.</param>
    /// <param name="color">False to drop colors and keep attributes, for <c>NO_COLOR</c>.</param>
    /// <returns>The widget, one row tall for no lines.</returns>
    public static Hex1bWidget Build<TParent>(WidgetContext<TParent> context, IReadOnlyList<StyledText> lines, int width, bool color)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(lines);
        return BuildRows(context, Fold(lines, width), width, color);
    }

    /// <summary>
    /// Builds a widget that draws rows already folded to a width.
    /// </summary>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="rows">The rows.</param>
    /// <param name="width">The width.</param>
    /// <param name="color">False to drop colors and keep attributes.</param>
    /// <returns>The widget, one row tall for no rows.</returns>
    public static Hex1bWidget BuildRows<TParent>(
        WidgetContext<TParent> context,
        IReadOnlyList<List<StyledSpan>> rows,
        int width,
        bool color)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(rows);
        var shown = rows.Count == 0 ? EmptyRows : rows;

        // Size hints apply to a widget through its parent, so the surface sits in a stack even when it is a root.
        return context.VStack(v =>
        [
            v.Surface(surface => [surface.Layer(target => Draw(target, shown, color))]).Size(Math.Max(1, width), shown.Count),
        ]);
    }

    /// <summary>
    /// Folds lines to a width.
    /// </summary>
    /// <param name="lines">The lines.</param>
    /// <param name="width">The width.</param>
    /// <returns>The rows.</returns>
    public static List<List<StyledSpan>> Fold(IEnumerable<StyledText> lines, int width)
    {
        ArgumentNullException.ThrowIfNull(lines);
        return [.. lines.SelectMany(line => StyledTextFolder.Fold(line, width))];
    }

    /// <summary>
    /// Draws folded rows onto a surface, starting at its top left.
    /// </summary>
    /// <param name="surface">The surface.</param>
    /// <param name="rows">The rows.</param>
    /// <param name="color">False to drop colors.</param>
    public static void Draw(Surface surface, IReadOnlyList<List<StyledSpan>> rows, bool color)
    {
        ArgumentNullException.ThrowIfNull(surface);
        ArgumentNullException.ThrowIfNull(rows);
        for (var y = 0; y < rows.Count && y < surface.Height; y++)
        {
            DrawRow(surface, 0, y, rows[y], color);
        }
    }

    /// <summary>
    /// Draws one row of spans onto a surface.
    /// </summary>
    /// <param name="surface">The surface.</param>
    /// <param name="x">The starting column.</param>
    /// <param name="y">The row.</param>
    /// <param name="row">The spans.</param>
    /// <param name="color">False to drop colors.</param>
    /// <returns>The column after the last cell written.</returns>
    public static int DrawRow(Surface surface, int x, int y, IReadOnlyList<StyledSpan> row, bool color)
    {
        ArgumentNullException.ThrowIfNull(surface);
        ArgumentNullException.ThrowIfNull(row);
        foreach (var span in row)
        {
            if (x >= surface.Width)
            {
                break;
            }

            var style = span.Style;
            var foreground = color ? style.Foreground?.ToHex1b() : null;
            var background = color ? style.Background?.ToHex1b() : null;
            x += surface.WriteText(x, y, span.Text, foreground, background, style.Attributes.ToCellAttributes());
        }

        return x;
    }
}
