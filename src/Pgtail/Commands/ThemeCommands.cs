using System.Text;
using Pgtail.Display;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// The <c>theme</c> command: show, switch, list, preview, edit, and reload color themes.
/// </summary>
internal static class ThemeCommands
{
    private static readonly (LogLevel Level, string Message)[] Samples =
    [
        (LogLevel.Panic, "System shutdown initiated due to memory corruption"),
        (LogLevel.Fatal, "Could not open relation: permission denied"),
        (LogLevel.Error, "duplicate key value violates unique constraint"),
        (LogLevel.Warning, "checkpoints are occurring too frequently"),
        (LogLevel.Notice, "table 'users' does not exist, skipping"),
        (LogLevel.Log, "connection received: host=127.0.0.1 port=5432"),
        (LogLevel.Info, "database system is ready to accept connections"),
        (LogLevel.Debug1, "replication slot 'sub1' advanced to 0/1234567"),
    ];

    /// <summary>
    /// The REPL command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the command has finished.</returns>
    public static async Task Repl(CommandInvocation invocation)
    {
        var args = invocation.Args;
        var output = invocation.Output;
        if (args.Count == 0)
        {
            Show(invocation.Session, output);
            return;
        }

        switch (args[0].ToLowerInvariant())
        {
            case "list":
                List(invocation.Session, output);
                break;
            case "preview" when args.Count < 2:
                output.Line("Usage: theme preview <name>");
                break;
            case "preview":
                Preview(invocation.Session, args[1], output);
                break;
            case "edit" when args.Count < 2:
                output.Line("Usage: theme edit <name>");
                output.Line("Create or edit a custom theme file.");
                break;
            case "edit":
                await EditAsync(invocation, args[1]);
                break;
            case "reload":
                output.Line(invocation.Session.Themes.ReloadCurrent().Message);
                break;
            default:
                Switch(invocation.Session, args[0].ToLowerInvariant(), output);
                break;
        }
    }

    /// <summary>
    /// Tail mode's command: show the current theme, or switch and redraw the log.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Tail(CommandInvocation invocation)
    {
        var session = invocation.Session;
        var output = invocation.Output;
        if (invocation.Args.Count == 0)
        {
            output.Markup($"[dim]Current theme:[/] [bold cyan]{Markup.Escape(session.Theme.Name)}[/]");
            return Task.CompletedTask;
        }

        var name = invocation.Args[0];
        if (!session.Themes.Switch(name))
        {
            var (builtIn, custom) = session.Themes.ListThemes();
            output.Markup($"[bold red]✗[/] Unknown theme [bold yellow]{Markup.Escape(name)}[/]. "
                + $"Available: {Markup.Escape(string.Join(", ", builtIn.Concat(custom).Order(StringComparer.Ordinal)))}");
            return Task.CompletedTask;
        }

        Persist(session, name, output);
        output.Markup($"[bold green]✓[/] Switched to theme [bold cyan]{Markup.Escape(name)}[/]");
        ((ITailHost)invocation.Host).Rebuild();
        return Task.CompletedTask;
    }

    private static void Show(PgtailSession session, CommandOutput output)
    {
        var theme = session.Theme;
        output.Line($"Current theme: {theme.Name}");
        if (theme.Description.Length > 0)
        {
            output.Line($"  {theme.Description}");
        }

        output.Line($"  Type: {(session.Themes.ThemeFile(theme.Name) is var file && File.Exists(file) ? "custom" : "built-in")}");
        output.Line();
        output.Line("Use 'theme list' to see available themes.");
        output.Line("Use 'theme <name>' to switch themes.");
    }

    private static void Switch(PgtailSession session, string name, CommandOutput output)
    {
        var file = session.Themes.ThemeFile(name);
        if (File.Exists(file))
        {
            var (loaded, errors) = Styling.ThemeLoader.Load(file);
            if (errors.Count > 0)
            {
                output.Line($"Theme '{name}' has validation errors:");
                foreach (var error in errors)
                {
                    output.Line($"  {error}");
                }

                output.Line();
                if (loaded is null)
                {
                    output.Line("Theme cannot be loaded due to errors.");
                    return;
                }

                output.Line("Theme loaded with warnings. Colors may not display correctly.");
                output.Line();
            }
        }

        if (!session.Themes.Switch(name))
        {
            var (builtIn, custom) = session.Themes.ListThemes();
            output.Line($"Unknown theme: {name}");
            output.Line();
            output.Line("Available themes:");
            foreach (var theme in builtIn)
            {
                output.Line($"  {theme} (built-in)");
            }

            foreach (var theme in custom)
            {
                output.Line($"  {theme} (custom)");
            }

            var similar = builtIn.Concat(custom)
                .Where(theme => theme.StartsWith(name[..Math.Min(3, name.Length)], StringComparison.Ordinal)
                    || theme.Contains(name, StringComparison.Ordinal))
                .ToList();
            if (similar.Count > 0 && !(similar is [var only] && only == name))
            {
                output.Line();
                output.Line($"Did you mean: {string.Join(", ", similar)}?");
            }

            return;
        }

        Persist(session, name, output);
        output.Line($"Switched to theme: {name}");
        if (session.Theme.Description.Length > 0)
        {
            output.Line($"  {session.Theme.Description}");
        }

        output.Line($"Saved to {session.Store.ConfigFile}");
        if (!session.ColorEnabled)
        {
            output.Line();
            output.Line("Note: NO_COLOR is set - colors are disabled.");
        }
    }

    private static void Persist(PgtailSession session, string name, CommandOutput output)
    {
        if (session.Store.Save("theme.name", name) is { } error)
        {
            output.Line($"Warning: {error}");
            return;
        }

        session.Config["theme.name"] = name;
    }

    private static void List(PgtailSession session, CommandOutput output)
    {
        var (builtIn, custom) = session.Themes.ListThemes();
        var current = session.Theme.Name;
        output.Line("Available themes:");
        output.Line();
        output.Line("Built-in:");
        foreach (var name in builtIn)
        {
            output.Line(ListLine(session, name, current));
        }

        if (custom.Count > 0)
        {
            output.Line();
            output.Line("Custom:");
            foreach (var name in custom)
            {
                output.Line(ListLine(session, name, current));
            }
        }

        output.Line();
        output.Line("* = current theme");
        output.Line();
        output.Line("Use 'theme <name>' to switch themes.");
        output.Line("Use 'theme preview <name>' to preview a theme.");
    }

    private static string ListLine(PgtailSession session, string name, string current)
    {
        var marker = name == current ? " *" : "";
        var description = session.Themes.GetTheme(name)?.Description is { Length: > 0 } text ? $"  - {text}" : "";
        return $"  {name}{marker}{description}";
    }

    private static void Preview(PgtailSession session, string name, CommandOutput output)
    {
        session.Themes.ScanCustomThemes();
        if (session.Themes.GetTheme(name) is not { } theme)
        {
            var (builtIn, custom) = session.Themes.ListThemes();
            output.Line($"Unknown theme: {name}");
            output.Line();
            output.Line("Available themes:");
            foreach (var available in builtIn.Concat(custom))
            {
                output.Line($"  {available}");
            }

            return;
        }

        output.Line($"Preview: {name}");
        if (theme.Description.Length > 0)
        {
            output.Line($"  {theme.Description}");
        }

        output.Line();
        var now = DateTime.Now;
        foreach (var (level, message) in Samples)
        {
            output.Line(new StyledText($"{EntryFormatter.FormatTime(now)} ", theme.Style("timestamp"))
                .Append("[12345] ", theme.Style("pid"))
                .Append($"{EntryFormatter.PadLevel(level)}: {message}", EntryFormatter.LevelStyle(level, theme)));
        }

        output.Line();
        output.Line($"Use 'theme {name}' to switch to this theme.");
    }

    private static async Task EditAsync(CommandInvocation invocation, string name)
    {
        var session = invocation.Session;
        var output = invocation.Output;
        if (ThemeManager.IsBuiltIn(name))
        {
            output.Line($"Cannot edit built-in theme: {name}");
            output.Line();
            output.Line("Built-in themes are read-only. To customize:");
            output.Line($"  1. Create a custom theme with a new name: theme edit my-{name}");
            output.Line("  2. Or copy the built-in theme colors to your custom theme");
            return;
        }

        var file = session.Themes.ThemeFile(name);
        var template = ThemeLoader.Template.Replace("{name}", name, StringComparison.Ordinal);
        if (!File.Exists(file))
        {
            Directory.CreateDirectory(session.Themes.ThemesDirectory);
            File.WriteAllText(file, template, new UTF8Encoding(false));
            output.Line($"Created new theme file: {file}");
        }
        else
        {
            output.Line($"Editing theme file: {file}");
        }

        _ = await CoreCommands.Repl(invocation).EditAsync(new EditRequest(
            file,
            $"Editing theme {name}",
            template,
            text => ThemeLoader.FromText(name, text).Errors));
        output.Line();
        output.Line($"Use 'theme {name}' to apply this theme.");
        output.Line("Use 'theme reload' to reload after further edits.");
    }
}
