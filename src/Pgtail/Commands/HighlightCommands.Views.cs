using System.Globalization;
using System.Text;
using Pgtail.Highlighting;
using Pgtail.Matching;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Toml;

namespace Pgtail.Commands;

/// <content>
/// Listing, previewing, exporting, and importing highlighting settings.
/// </content>
internal static partial class HighlightCommands
{
    private static readonly TextStyle Bold = StyleParser.Parse("bold");
    private static readonly TextStyle Cyan = StyleParser.Parse("cyan");
    private static readonly TextStyle HeadingStyle = StyleParser.Parse("bold cyan");
    private static readonly TextStyle Warning = StyleParser.Parse("bold yellow");

    private static void List(PgtailSession session, CommandOutput output)
    {
        var config = session.Highlighting;
        var status = config.Enabled ? "enabled" : "disabled";
        output.Line(new StyledText("Semantic Highlighting: ").Append(status, config.Enabled ? Green : Red));
        output.Line();
        foreach (var category in HighlighterCategories.Ordered)
        {
            output.Line(HighlighterMetadata.Heading(category), Bold);
            foreach (var (name, _, description) in HighlighterMetadata.All.Where(item => item.Category == category)
                .OrderBy(item => item.Name, StringComparer.Ordinal))
            {
                output.Line(Row(config.IsHighlighterEnabled(name), name, description));
            }

            output.Line();
        }

        if (config.CustomHighlighters.Count > 0)
        {
            output.Line("Custom", Bold);
            foreach (var custom in config.CustomHighlighters)
            {
                output.Line(Row(custom.Enabled, custom.Name, $"Pattern: {custom.Pattern}"));
            }

            output.Line();
        }
    }

    private static StyledText Row(bool enabled, string name, string description) => new StyledText("  [")
        .Append((enabled ? "on" : "off").PadRight(3), enabled ? Green : Red)
        .Append("] ")
        .Append(name.PadRight(20), Cyan)
        .Append(" " + description, Dim);

    private static void Preview(PgtailSession session, CommandOutput output)
    {
        var config = session.Highlighting;
        output.Line(new StyledText("Highlight Preview", HeadingStyle).Append(" (")
            .Append(config.Enabled ? "enabled" : "disabled", config.Enabled ? Green : Red).Append(")"));
        output.Line();
        if (!config.Enabled)
        {
            output.Line("Highlighting is disabled. Run 'highlight on' to enable.", Dim);
            output.Line();
        }

        var disabled = BuiltInHighlighters.Names.Where(name => !config.IsHighlighterEnabled(name)).ToHashSet(StringComparer.Ordinal);
        var chain = session.Chain;
        foreach (var category in HighlighterCategories.Ordered)
        {
            var samples = HighlighterMetadata.PreviewSamples
                .Where(sample => HighlighterMetadata.All.First(item => item.Name == sample.Highlighters[0]).Category == category)
                .ToList();
            if (samples.Count == 0)
            {
                continue;
            }

            output.Line(HighlighterMetadata.Heading(category), Bold);
            foreach (var (highlighters, line, description) in samples)
            {
                output.Line(new StyledText("  ").Append(description, Dim));
                var off = highlighters.Where(disabled.Contains).ToList();
                if (off.Count > 0)
                {
                    output.Line(new StyledText("  ").Append("Disabled: ", Yellow).Append(string.Join(", ", off), Dim));
                }

                output.Line(new StyledText("  ").Append(chain.Apply(line, session.Theme)));
                output.Line();
            }
        }

        if (disabled.Count > 0)
        {
            output.Line("Disabled Highlighters", Warning);
            foreach (var name in disabled.Order(StringComparer.Ordinal))
            {
                output.Line($"  - {name}", Dim);
            }

            output.Line();
            output.Line("Use 'highlight enable <name>' to enable disabled highlighters.", Dim);
        }

        if (config.CustomHighlighters.Count > 0)
        {
            output.Line();
            output.Line("Custom Highlighters", Bold);
            foreach (var custom in config.CustomHighlighters)
            {
                output.Line(new StyledText("  ").Append(custom.Name, custom.Enabled ? Green : Red).Append($": {custom.Pattern} ")
                    .Append($"(style: {custom.Style})", Dim));
            }
        }
    }

    private static (bool Success, string Message) Export(PgtailSession session, IReadOnlyList<string> args, string currentDirectory)
    {
        string? file = null;
        for (var i = 0; i < args.Count - 1; i++)
        {
            if (args[i] is "--file" or "-f")
            {
                file = args[i + 1];
                break;
            }
        }

        var document = TomlDocument.Parse("# pgtail highlighting configuration\n# Export generated by: highlight export\n\n");
        session.Highlighting.SaveTo(document);
        var text = document.ToString();
        if (file is null)
        {
            return (true, text);
        }

        var path = PathDisplay.Resolve(file, session.Home, currentDirectory);
        try
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, text, new UTF8Encoding(false));
            return (true, $"Exported highlighting config to {path}");
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return (false, $"Failed to write to {path}: {exception.Message}");
        }
    }

    private static (bool Success, string Message) Import(
        PgtailSession session,
        IReadOnlyList<string> args,
        string currentDirectory,
        CommandOutput output)
    {
        if (args.Count == 0)
        {
            return (false, "Usage: highlight import <path>");
        }

        var path = PathDisplay.Resolve(args[0], session.Home, currentDirectory);
        if (Directory.Exists(path))
        {
            return (false, $"Not a file: {path}");
        }

        if (!File.Exists(path))
        {
            return (false, $"File not found: {path}");
        }

        TomlDocument document;
        try
        {
            document = TomlDocument.Load(path);
        }
        catch (TomlException exception)
        {
            return (false, $"Invalid TOML: {exception.Message}");
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return (false, $"Failed to read {path}: {exception.Message}");
        }

        var (error, warnings) = Validate(document.Root);
        if (error is not null)
        {
            return (false, $"Invalid configuration: {error}");
        }

        foreach (var warning in warnings)
        {
            output.Line($"Warning: {warning}");
        }

        Apply(session.Highlighting, document.Root);
        Save(session, output);
        return (true, $"Imported highlighting config from {path}" + (warnings.Count > 0 ? $" ({warnings.Count} warning(s))" : ""));
    }

    private static (string? Error, List<string> Warnings) Validate(TomlTable root)
    {
        var warnings = new List<string>();
        if (!root.TryGetValue("highlighting", out var section))
        {
            return ("Missing [highlighting] section", warnings);
        }

        if (section is not TomlTable highlighting)
        {
            return ("[highlighting] section must be a table", warnings);
        }

        if (highlighting.TryGetValue("enabled_highlighters", out var switches))
        {
            if (switches is not TomlTable table)
            {
                return ("[highlighting.enabled_highlighters] must be a table", warnings);
            }

            foreach (var name in table.Keys.Where(name => !BuiltInHighlighters.Names.Contains(name)))
            {
                warnings.Add(CloseMatches.Best(name, BuiltInHighlighters.Names) is { } suggestion
                    ? $"Unknown highlighter '{name}'. Did you mean '{suggestion}'?"
                    : $"Unknown highlighter '{name}' - will be ignored");
            }
        }

        if (highlighting.TryGetValue("duration", out var durations) && durations is TomlTable thresholds)
        {
            foreach (var key in new[] { "slow", "very_slow", "critical" })
            {
                if (!thresholds.TryGetValue(key, out var value))
                {
                    continue;
                }

                if (value is not long number || number < 0)
                {
                    return ($"Duration threshold '{key}' must be a non-negative integer", warnings);
                }

                if (number > 3_600_000)
                {
                    warnings.Add($"Duration threshold '{key}' ({number}ms) is very high");
                }
            }
        }

        if (!highlighting.TryGetValue("custom", out var custom))
        {
            return (null, warnings);
        }

        if (custom is not TomlArray entries)
        {
            return ("[highlighting.custom] must be an array", warnings);
        }

        for (var i = 0; i < entries.Count; i++)
        {
            if (entries[i] is not TomlTable entry)
            {
                return ($"Custom highlighter {i} must be a table", warnings);
            }

            if (!entry.TryGetValue("name", out var nameValue))
            {
                return ($"Custom highlighter {i} missing 'name'", warnings);
            }

            var name = Convert.ToString(nameValue, CultureInfo.InvariantCulture) ?? "";
            if (!entry.TryGetValue("pattern", out var patternValue))
            {
                return ($"Custom highlighter '{name}' missing 'pattern'", warnings);
            }

            if (!CustomName().IsMatch(name))
            {
                return ($"Custom highlighter name '{name}' must be lowercase alphanumeric with underscores", warnings);
            }

            if (CustomRegexHighlighter.Validate(Convert.ToString(patternValue, CultureInfo.InvariantCulture) ?? "")
                is { } patternError)
            {
                return ($"Custom highlighter '{name}' has invalid pattern: {patternError}", warnings);
            }

            if (BuiltInHighlighters.Names.Contains(name))
            {
                return ($"Custom highlighter name '{name}' conflicts with built-in highlighter", warnings);
            }
        }

        return (null, warnings);
    }

    private static void Apply(HighlightingConfig config, TomlTable root)
    {
        var highlighting = (TomlTable)root["highlighting"];
        if (highlighting.TryGetValue("enabled", out var enabled) && enabled is bool on)
        {
            config.Enabled = on;
        }

        if (highlighting.TryGetValue("max_length", out var length) && length is long maxLength)
        {
            config.MaxLength = maxLength;
        }

        if (highlighting.TryGetValue("duration", out var durations) && durations is TomlTable thresholds)
        {
            if (thresholds.TryGetValue("slow", out var slow))
            {
                config.DurationSlow = (long)slow;
            }

            if (thresholds.TryGetValue("very_slow", out var verySlow))
            {
                config.DurationVerySlow = (long)verySlow;
            }

            if (thresholds.TryGetValue("critical", out var critical))
            {
                config.DurationCritical = (long)critical;
            }
        }

        if (highlighting.TryGetValue("enabled_highlighters", out var switches) && switches is TomlTable table)
        {
            foreach (var (name, value) in table)
            {
                if (BuiltInHighlighters.Names.Contains(name) && value is bool state)
                {
                    config.SetHighlighter(name, state);
                }
            }
        }

        if (highlighting.ContainsKey("custom"))
        {
            config.ClearCustom();
            config.LoadCustom(root);
        }
    }
}
