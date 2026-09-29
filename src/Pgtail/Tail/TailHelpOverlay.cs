using Hex1b;
using Hex1b.Input;
using Hex1b.Widgets;
using Pgtail.Rendering;
using Pgtail.Styling;

namespace Pgtail.Tail;

/// <summary>
/// The keybinding reference shown over tail mode with <c>?</c>.
/// </summary>
internal static class TailHelpOverlay
{
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
        ("Commands",
        [
            ("/ or Tab", "Focus command input"),
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
    /// Builds the overlay, centered, closed by Escape, <c>q</c>, or <c>?</c>.
    /// </summary>
    /// <typeparam name="TParent">The parent widget type.</typeparam>
    /// <param name="context">The widget context.</param>
    /// <param name="close">Closes the overlay.</param>
    /// <returns>The overlay.</returns>
    public static Hex1bWidget Build<TParent>(WidgetContext<TParent> context, Action close)
        where TParent : Hex1bWidget
    {
        ArgumentNullException.ThrowIfNull(context);
        ArgumentNullException.ThrowIfNull(close);
        var lines = new List<StyledText> { Markup.Parse("[bold]pgtail Keybindings[/]"), new() };
        foreach (var (category, keys) in Keybindings)
        {
            lines.Add(Markup.Parse($"[bold magenta]{category}[/]"));
            foreach (var (key, description) in keys)
            {
                lines.Add(Markup.Parse($"[green]{Markup.Escape(key.PadRight(16))}[/] [dim]{Markup.Escape(description)}[/]"));
            }

            lines.Add(new StyledText());
        }

        lines.Add(Markup.Parse("[dim]Press Escape, q, or ? to close[/]"));
        const int width = 66;
        return context.Center(context.Interactable(i => i.Border(StyledBlock.Build(i, lines, width, color: true)))
            .InputBindings(bindings =>
            {
                bindings.Key(Hex1bKey.Escape).Action(_ => close(), "Close help");
                bindings.Key(Hex1bKey.Q).Action(_ => close(), "Close help");
                bindings.Character(text => text == "?").Action(_ => close(), "Close help");
            }).FixedWidth(width + 2));
    }
}
