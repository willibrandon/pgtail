using System.Globalization;
using Pgtail.Filtering;
using Pgtail.Highlighting;
using Pgtail.Matching;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// The <c>highlight</c> command: semantic highlighter management, and in the REPL the regex highlights too.
/// </summary>
internal static partial class HighlightCommands
{
    private const string Usage = "Usage: highlight add <name> <pattern> [--style <style>] [--priority <num>]";

    /// <summary>
    /// The REPL command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Repl(CommandInvocation invocation)
    {
        var args = invocation.Args;
        var output = invocation.Output;
        var session = invocation.Session;
        var sub = args.Count == 0 ? "list" : args[0].ToLowerInvariant();
        switch (sub)
        {
            case "clear":
                session.Regex.ClearHighlights();
                output.Line("Regex highlights cleared");
                return Task.CompletedTask;
            case "preview":
                Preview(session, output);
                return Task.CompletedTask;
            case "list":
                List(session, output);
                return Task.CompletedTask;
            case "export":
                var (_, exported) = Export(session, [.. args.Skip(1)], invocation.Host.CurrentDirectory);
                output.Line(exported);
                return Task.CompletedTask;
            case "import":
                var (_, imported) = Import(session, [.. args.Skip(1)], invocation.Host.CurrentDirectory, output);
                output.Line(imported);
                return Task.CompletedTask;
        }

        if (Change(session, sub, args, output) is { } result)
        {
            output.Line(result.Message);
            return Task.CompletedTask;
        }

        if (!args[0].StartsWith('/'))
        {
            output.Line($"Unknown subcommand: {sub}");
            output.Line();
            output.Lines(
            [
                "Usage: highlight list             Show semantic highlighters",
                "       highlight on               Enable all highlighting",
                "       highlight off              Disable all highlighting",
                "       highlight enable <name>    Enable a highlighter",
                "       highlight disable <name>   Disable a highlighter",
                "       highlight add <name> <pattern> [--style <style>] [--priority <num>]",
                "       highlight remove <name>    Remove custom highlighter",
                "       highlight export [--file <path>]  Export config as TOML",
                "       highlight import <path>    Import config from TOML",
                "       highlight preview          Preview with sample lines",
                "       highlight reset            Reset all settings to defaults",
                "       highlight /pattern/        Add regex highlight (legacy)",
                "       highlight clear            Clear regex highlights (legacy)",
            ]);
            return Task.CompletedTask;
        }

        AddRegexHighlight(session, args[0], output);
        return Task.CompletedTask;
    }

    /// <summary>
    /// The tail mode command, which redraws the log after a change.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Tail(CommandInvocation invocation)
    {
        var args = invocation.Args;
        var output = invocation.Output;
        var session = invocation.Session;
        var host = (ITailHost)invocation.Host;
        var sub = args.Count == 0 ? "list" : args[0].ToLowerInvariant();
        switch (sub)
        {
            case "list":
                List(session, output);
                return Task.CompletedTask;
            case "preview":
                Preview(session, output);
                return Task.CompletedTask;
            case "export":
                var (exportedOk, exported) = Export(session, [.. args.Skip(1)], invocation.Host.CurrentDirectory);
                if (!exportedOk)
                {
                    output.Line(exported, Red);
                }
                else if (exported.StartsWith('#') || exported.StartsWith('['))
                {
                    foreach (var line in exported.TrimEnd('\n').Split('\n'))
                    {
                        output.Line(line, Dim);
                    }
                }
                else
                {
                    output.Line(exported, Green);
                }

                return Task.CompletedTask;
            case "import":
                var version = session.Highlighting.Version;
                var (importedOk, imported) = Import(session, [.. args.Skip(1)], invocation.Host.CurrentDirectory, output);
                output.Line(imported, importedOk ? Green : Red);
                if (session.Highlighting.Version != version)
                {
                    host.Rebuild();
                }

                return Task.CompletedTask;
        }

        var before = session.Highlighting.Version;
        if (Change(session, sub, args, output) is not { } result)
        {
            output.Line($"Unknown subcommand: {sub}. Use: list, on, off, enable, disable, add, remove, export, import, preview, reset",
                Red);
            return Task.CompletedTask;
        }

        output.Line(result.Message, !result.Success ? Red : sub == "off" ? Yellow : Green);
        if (session.Highlighting.Version != before)
        {
            host.Rebuild();
        }

        return Task.CompletedTask;
    }

    private static readonly TextStyle Green = StyleParser.Parse("green");
    private static readonly TextStyle Red = StyleParser.Parse("red");
    private static readonly TextStyle Yellow = StyleParser.Parse("yellow");
    private static readonly TextStyle Dim = StyleParser.Parse("dim");

    private static (bool Success, string Message)? Change(
        PgtailSession session,
        string sub,
        IReadOnlyList<string> args,
        CommandOutput output)
    {
        var config = session.Highlighting;
        return sub switch
        {
            "on" => SetGlobal(session, true, output),
            "off" => SetGlobal(session, false, output),
            "enable" when args.Count < 2 => (false, "Usage: highlight enable <name>"),
            "enable" => SetHighlighter(session, args[1], true, output),
            "disable" when args.Count < 2 => (false, "Usage: highlight disable <name>"),
            "disable" => SetHighlighter(session, args[1], false, output),
            "add" => Add(session, [.. args.Skip(1)], output),
            "remove" when args.Count < 2 => (false, "Usage: highlight remove <name>"),
            "remove" => Remove(session, args[1], output),
            "reset" => Reset(session, config, output),
            _ => null,
        };
    }

    private static (bool, string) SetGlobal(PgtailSession session, bool enabled, CommandOutput output)
    {
        var config = session.Highlighting;
        if (config.Enabled == enabled)
        {
            return (true, enabled ? "Highlighting is already enabled." : "Highlighting is already disabled.");
        }

        config.Enabled = enabled;
        Save(session, output);
        return (true, enabled ? "Highlighting enabled." : "Highlighting disabled.");
    }

    private static (bool, string) SetHighlighter(PgtailSession session, string name, bool enabled, CommandOutput output)
    {
        var config = session.Highlighting;
        var verb = enabled ? "Enabled" : "Disabled";
        if (!BuiltInHighlighters.Names.Contains(name))
        {
            if (config.SetCustomEnabled(name, enabled))
            {
                Save(session, output);
                return (true, $"{verb} custom highlighter '{name}'.");
            }

            return CloseMatches.Best(name, BuiltInHighlighters.Names) is { } suggestion
                ? (false, $"Unknown highlighter '{name}'. Did you mean '{suggestion}'?")
                : (false, $"Unknown highlighter '{name}'. Use 'highlight list' to see available highlighters.");
        }

        config.SetHighlighter(name, enabled);
        Warn(session.Store.SaveHighlighterSwitch(name, enabled), output);
        SyncConfig(session);
        return (true, $"{verb} highlighter '{name}'.");
    }

    private static (bool, string) Add(PgtailSession session, IReadOnlyList<string> args, CommandOutput output)
    {
        if (args.Count < 2)
        {
            return (false, Usage);
        }

        var (name, pattern) = (args[0], args[1]);
        var style = "yellow";
        int? priority = null;
        for (var i = 2; i < args.Count; i++)
        {
            if (args[i] == "--style" && i + 1 < args.Count)
            {
                style = args[++i];
            }
            else if (args[i] == "--priority" && i + 1 < args.Count)
            {
                if (int.TryParse(args[++i], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out var value))
                {
                    priority = value;
                }
            }
        }

        var config = session.Highlighting;
        if (!CustomName().IsMatch(name))
        {
            return (false, "Name must start with a letter and contain only lowercase letters, numbers, and underscores");
        }

        if (BuiltInHighlighters.Names.Contains(name))
        {
            return (false, $"Name '{name}' conflicts with built-in highlighter");
        }

        if (config.GetCustom(name) is not null)
        {
            return (false, $"Custom highlighter '{name}' already exists");
        }

        if (CustomRegexHighlighter.Validate(pattern) is { } error)
        {
            return (false, error);
        }

        if (!StyleParser.TryParse(style, out _, out var styleError))
        {
            return (false, $"Invalid style '{style}': {styleError}");
        }

        config.AddCustom(new CustomHighlighterDefinition(name, pattern, style, priority ?? 1050 + config.CustomHighlighters.Count));
        Save(session, output);
        return (true, $"Added custom highlighter '{name}' with pattern '{pattern}'.");
    }

    private static (bool, string) Remove(PgtailSession session, string name, CommandOutput output)
    {
        var config = session.Highlighting;
        if (BuiltInHighlighters.Names.Contains(name))
        {
            return (false, $"Cannot remove built-in highlighter '{name}'. Use 'highlight disable {name}' instead.");
        }

        if (!config.RemoveCustom(name))
        {
            var names = config.CustomHighlighters.Select(custom => custom.Name).ToList();
            return names.Count > 0
                ? (false, $"Custom highlighter '{name}' not found. Available: {string.Join(", ", names)}")
                : (false, $"Custom highlighter '{name}' not found. No custom highlighters defined.");
        }

        Save(session, output);
        return (true, $"Removed custom highlighter '{name}'.");
    }

    private static (bool, string) Reset(PgtailSession session, HighlightingConfig config, CommandOutput output)
    {
        var items = new List<string>();
        if (!config.Enabled)
        {
            items.Add("enabled highlighting");
        }

        if (BuiltInHighlighters.Names.Any(name => !config.IsSwitchedOn(name)))
        {
            items.Add("enabled all highlighters");
        }

        if (config.DurationSlow != 100 || config.DurationVerySlow != 500 || config.DurationCritical != 5000)
        {
            items.Add("reset duration thresholds");
        }

        if (config.CustomHighlighters.Count > 0)
        {
            items.Add("removed custom highlighters");
        }

        config.Reset();
        Save(session, output);
        return (true, items.Count > 0 ? $"Reset complete: {string.Join(", ", items)}." : "All settings were already at defaults.");
    }

    private static void Save(PgtailSession session, CommandOutput output)
    {
        Warn(session.Store.SaveHighlighting(session.Highlighting), output);
        SyncConfig(session);
    }

    private static void Warn(string? error, CommandOutput output)
    {
        if (error is not null)
        {
            output.Line($"Warning: {error}");
        }
    }

    /// <summary>
    /// Copies the highlighting settings into the session's configuration, so <c>set</c> shows them.
    /// </summary>
    /// <param name="session">The session.</param>
    public static void SyncConfig(PgtailSession session)
    {
        ArgumentNullException.ThrowIfNull(session);
        var config = session.Config;
        var highlighting = session.Highlighting;
        config["highlighting.enabled"] = highlighting.Enabled;
        config["highlighting.max_length"] = highlighting.MaxLength;
        config["highlighting.duration.slow"] = highlighting.DurationSlow;
        config["highlighting.duration.very_slow"] = highlighting.DurationVerySlow;
        config["highlighting.duration.critical"] = highlighting.DurationCritical;
        foreach (var name in BuiltInHighlighters.Names)
        {
            config[$"highlighting.enabled_highlighters.{name}"] = highlighting.IsSwitchedOn(name);
        }
    }

    private static void AddRegexHighlight(PgtailSession session, string argument, CommandOutput output)
    {
        (string Pattern, bool CaseSensitive) parsed;
        try
        {
            parsed = FilterSyntax.Parse(argument);
        }
        catch (FormatException exception)
        {
            output.Line($"Error: {exception.Message}");
            return;
        }

        try
        {
            session.Regex.Highlights.Add(RegexHighlight.Create(parsed.Pattern, parsed.CaseSensitive));
        }
        catch (FormatException exception)
        {
            output.Line($"Invalid regex pattern: {exception.Message}");
            return;
        }

        output.Line($"Regex highlight added: /{parsed.Pattern}/{(parsed.CaseSensitive ? " (case-sensitive)" : "")}");
    }

    [System.Text.RegularExpressions.GeneratedRegex("^[a-z][a-z0-9_]*$")]
    private static partial System.Text.RegularExpressions.Regex CustomName();
}
