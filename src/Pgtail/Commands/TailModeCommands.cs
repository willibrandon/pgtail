using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// Tail mode's own commands: pause, follow, stop, clear, and help.
/// </summary>
internal static class TailModeCommands
{
    /// <summary>
    /// Freezes the log.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Pause(CommandInvocation invocation)
    {
        Host(invocation).Pause();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Resumes following.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Follow(CommandInvocation invocation)
    {
        Host(invocation).Follow();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Leaves tail mode.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Stop(CommandInvocation invocation)
    {
        Host(invocation).Stop();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Returns to the filters tail mode started with, or with <c>force</c> clears every filter and entry.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Clear(CommandInvocation invocation)
    {
        var host = Host(invocation);
        if (invocation.Args is [var force, ..] && force.Equals("force", StringComparison.OrdinalIgnoreCase))
        {
            host.ClearEverything();
        }
        else
        {
            host.ResetToAnchor();
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Shows the command and key overview, <c>help keys</c>, or <c>help &lt;command&gt;</c>.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Help(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var args = invocation.Args;
        if (args.Count > 0 && args[0].Equals("keys", StringComparison.OrdinalIgnoreCase))
        {
            Keys(output);
            return Task.CompletedTask;
        }

        if (args.Count > 0 && TailCatalog.Catalog.Find(args[0]) is { Help: not null } command)
        {
            ShowCommandHelp(command, output);
            return Task.CompletedTask;
        }

        output.Markup("[bold cyan]Navigation[/bold cyan]");
        foreach (var (key, description) in new[]
        {
            ("Up/Down", "Scroll 1 line"),
            ("PgUp/PgDn", "Scroll full page"),
            ("Ctrl+u/d", "Scroll half page"),
            ("Ctrl+b/f", "Scroll full page"),
            ("Home", "Go to top"),
            ("End", "Go to bottom (resume FOLLOW mode)"),
        })
        {
            output.Markup($"  [green]{Markup.Escape(key.PadRight(12))}[/green] [dim]{Markup.Escape(description)}[/dim]");
        }

        output.Line();
        output.Markup("[bold cyan]Command Input[/bold cyan]");
        foreach (var (key, description) in new[]
        {
            ("Enter", "Run the command; its output stays above the input"),
            ("PgUp/PgDn", "Scroll the output, or the log"),
            ("Up/Down", "Previous/next command"),
            ("Escape", "Close the output, then go to the log"),
            ("Tab", "Switch between the input and the log"),
        })
        {
            output.Markup($"  [green]{Markup.Escape(key.PadRight(12))}[/green] [dim]{Markup.Escape(description)}[/dim]");
        }

        output.Line();
        output.Markup("[bold cyan]Utility Keys[/bold cyan]");
        foreach (var (key, description) in new[] { ("Ctrl+C", "Copy the selection, or exit tail mode"), ("q", "Exit tail mode") })
        {
            output.Markup($"  [green]{Markup.Escape(key.PadRight(12))}[/green] [dim]{Markup.Escape(description)}[/dim]");
        }

        output.Line();
        output.Markup("[bold cyan]Commands[/bold cyan]");
        foreach (var (name, description) in new[]
        {
            ("help", "Show this help"),
            ("help keys", "Show keybinding reference"),
            ("pause", "Enter PAUSED mode"),
            ("follow", "Resume FOLLOW mode"),
            ("level <lvl>", "Filter by level (e.g., 'level error,warning')"),
            ("filter /re/", "Filter by regex pattern"),
            ("since <time>", "Show entries since time (e.g., '5m', '14:30')"),
            ("until <time>", "Show entries until time"),
            ("between s e", "Show entries in time range"),
            ("slow <ms>", "Set slow query threshold"),
            ("clear", "Clear all filters"),
            ("errors", "Show error statistics"),
            ("connections", "Show connection statistics"),
            ("highlight", "Manage semantic highlighters"),
            ("theme <name>", "Switch color theme"),
            ("notify", "Configure desktop notifications"),
            ("set <key>", "Configure settings"),
            ("export <path>", "Export entries to file"),
            ("stop/exit/q", "Exit tail mode"),
        })
        {
            output.Markup($"  [yellow]{Markup.Escape(name.PadRight(12))}[/yellow] [dim]{Markup.Escape(description)}[/dim]");
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Shows a command's detailed help.
    /// </summary>
    /// <param name="command">The command.</param>
    /// <param name="output">Where to write.</param>
    public static void ShowCommandHelp(CommandInfo command, CommandOutput output)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(output);
        var help = command.Help!;
        output.Markup($"[bold cyan]{command.Name.ToUpperInvariant()}[/bold cyan]");
        output.Markup($"  [dim]{Markup.Escape(help.Short)}[/dim]");
        output.Line();
        output.Markup($"[bold]Usage:[/bold] [green]{Markup.Escape(help.Usage)}[/green]");
        output.Line();
        output.Line($"  {help.Description}");
        output.Line();
        output.Markup("[bold]Examples:[/bold]");
        foreach (var example in help.Examples)
        {
            output.Markup($"  [yellow]{Markup.Escape(example)}[/yellow]");
        }

        output.Line();
        if (help.Aliases is { } aliases)
        {
            output.Markup($"[bold]Aliases:[/bold] [dim]{Markup.Escape(aliases)}[/dim]");
        }

        if (help.SeeAlso is { } seeAlso)
        {
            output.Markup($"[bold]See also:[/bold] [dim]{Markup.Escape(seeAlso)}[/dim]");
        }
    }

    private static void Keys(CommandOutput output)
    {
        foreach (var (category, keys) in Tail.TailHelpOverlay.Keybindings)
        {
            output.Markup($"[bold cyan]{category}[/bold cyan]");
            foreach (var (key, description) in keys)
            {
                output.Markup($"  [green]{Markup.Escape(key.PadRight(16))}[/green] [dim]{Markup.Escape(description)}[/dim]");
            }
        }
    }

    private static ITailHost Host(CommandInvocation invocation) => (ITailHost)invocation.Host;
}
