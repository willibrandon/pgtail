using Hex1b;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The keybinding reference shown over tail mode with <c>?</c>.
/// </summary>
internal sealed class TailHelpOverlay
{
    private int _top;

    /// <summary>
    /// The keys, by category.
    /// </summary>
    public static IReadOnlyList<(string Category, IReadOnlyList<(string Key, string Description)> Keys)> Keybindings { get; } =
    [
        ("Navigation",
        [
            ("j / ↓", "Scroll down one line"),
            ("k / ↑", "Scroll up one line"),
            ("g", "Go to top"),
            ("G", "Go to bottom (resume FOLLOW)"),
            ("Ctrl+d", "Half page down"),
            ("Ctrl+u", "Half page up"),
            ("Ctrl+f / PgDn", "Full page down"),
            ("Ctrl+b / PgUp", "Full page up"),
            ("p", "Pause (freeze display)"),
            ("f", "Resume FOLLOW mode"),
        ]),
        ("Selection",
        [
            ("v", "Visual mode (character)"),
            ("V", "Visual line mode"),
            ("h / l", "Move cursor left/right"),
            ("0 / $", "Line start/end"),
            ("y", "Yank (copy) selection"),
            ("Escape", "Clear selection"),
            ("Ctrl+a", "Select all"),
            ("Ctrl+c", "Copy selection"),
        ]),
        ("Command input",
        [
            ("/ or Tab", "Focus command input"),
            ("Enter", "Run the command"),
            ("PgUp / PgDn", "Scroll the log"),
            ("↑ / ↓", "Previous / next command"),
            ("Escape", "Clear the input, go to the log"),
        ]),
        ("Commands",
        [
            ("level <lvl>", "Filter by level"),
            ("filter /re/", "Filter by regex"),
            ("since <time>", "Filter by time"),
            ("pause", "Pause log updates"),
            ("follow", "Resume updates"),
            ("clear", "Reset filters"),
            ("errors", "Show error stats"),
            ("connections", "Show connection stats"),
            ("help", "Show command help"),
            ("q / stop", "Exit tail mode"),
        ]),
        ("Help",
        [
            ("?", "Show this help"),
            ("Escape / q", "Close help"),
        ]),
    ];

    /// <summary>
    /// Shows the overlay from its first line.
    /// </summary>
    public void Open() => _top = 0;

    /// <summary>
    /// Builds the overlay, centered, closed by Escape, <c>q</c>, or <c>?</c>.
    /// </summary>
    /// <remarks>
    /// When the screen is shorter than the keys, the overlay fills the screen's height and the keys scroll with the
    /// arrow keys, <c>j</c> and <c>k</c>, Page Up and Page Down, and Home and End.
    /// </remarks>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="height">The screen's height.</param>
    /// <param name="close">Closes the overlay.</param>
    /// <returns>The overlay.</returns>
    public Hex1bWidget Build<TParent>(WidgetContext<TParent> context, int height, Action<InputBindingActionContext> close)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(close);
        var body = new List<StyledText>();
        foreach (var (category, keys) in Keybindings)
        {
            if (body.Count > 0)
            {
                body.Add(new StyledText());
            }

            body.Add(Markup.Parse($"[bold magenta]{category}[/]"));
            foreach (var (key, description) in keys)
            {
                body.Add(Markup.Parse($"[green]{Markup.Escape(key.PadRight(16))}[/] [dim]{Markup.Escape(description)}[/]"));
            }
        }

        // The border, the title and the blank line under it, and the blank line and footer below the keys.
        var rows = Math.Max(1, Math.Min(body.Count, height - 6));
        var page = Math.Max(1, rows - 1);
        _top = Math.Clamp(_top, 0, body.Count - rows);
        var scrolls = rows < body.Count;
        var lines = new List<StyledText> { Markup.Parse("[bold]pgtail Keybindings[/]"), new() };
        lines.AddRange(body.Skip(_top).Take(rows));
        lines.Add(new StyledText());
        lines.Add(Markup.Parse(scrolls
            ? "[dim]↑↓ PgUp PgDn scroll · Press Escape, q, or ? to close[/]"
            : "[dim]Press Escape, q, or ? to close[/]"));
        const int width = 66;
        return context.Center(context.Interactable(i => i.Border(StyledBlock.Build(i, lines, width, color: true)))
            .InputBindings(bindings =>
            {
                bindings.Key(Hex1bKey.Escape).Action(close, "Close help");
                bindings.Key(Hex1bKey.Q).Action(close, "Close help");
                bindings.Character(text => text == "?").Action((_, actionContext) =>
                {
                    close(actionContext);
                    return Task.CompletedTask;
                }, "Close help");

                bindings.Key(Hex1bKey.DownArrow).Action(_ => _top++, "Scroll down");
                bindings.Key(Hex1bKey.UpArrow).Action(_ => _top--, "Scroll up");
                bindings.Key(Hex1bKey.J).Action(_ => _top++, "Scroll down");
                bindings.Key(Hex1bKey.K).Action(_ => _top--, "Scroll up");
                bindings.Key(Hex1bKey.PageDown).Action(_ => _top += page, "Page down");
                bindings.Key(Hex1bKey.PageUp).Action(_ => _top -= page, "Page up");
                bindings.Key(Hex1bKey.Home).Action(_ => _top = 0, "Top");
                bindings.Key(Hex1bKey.End).Action(_ => _top = body.Count, "Bottom");
            }).FixedWidth(width + 2));
    }
}
