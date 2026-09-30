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
    private static readonly TextStyle s_bold = StyleParser.Parse("bold");
    private static readonly TextStyle s_cyan = StyleParser.Parse("cyan");
    private static readonly TextStyle s_headingStyle = StyleParser.Parse("bold cyan");
    private static readonly TextStyle s_warning = StyleParser.Parse("bold yellow");

    private static void List(PgtailSession session, CommandOutput output)
    {
        HighlightingConfig config = session.Highlighting;
        string status = config.Enabled ? "enabled" : "disabled";
        output.Line(new StyledText("Semantic Highlighting: ").Append(status, config.Enabled ? s_green : s_red));
        output.Line();
        foreach (string category in HighlighterCategories.Ordered)
        {
            output.Line(HighlighterMetadata.Heading(category), s_bold);
            foreach ((string name, string _, string description) in HighlighterMetadata.All.Where(item => item.Category == category)
                .OrderBy(item => item.Name, StringComparer.Ordinal))
            {
                output.Line(Row(config.IsHighlighterEnabled(name), name, description));
            }

            output.Line();
        }

        if (config.CustomHighlighters.Count > 0)
        {
            output.Line("Custom", s_bold);
            foreach (CustomHighlighterDefinition custom in config.CustomHighlighters)
            {
                output.Line(Row(custom.Enabled, custom.Name, $"Pattern: {custom.Pattern}"));
            }

            output.Line();
        }
    }

    private static StyledText Row(bool enabled, string name, string description) => new StyledText("  [")
        .Append((enabled ? "on" : "off").PadRight(3), enabled ? s_green : s_red)
        .Append("] ")
        .Append(name.PadRight(20), s_cyan)
        .Append(" " + description, s_dim);

    private static void Preview(PgtailSession session, CommandOutput output)
    {
        HighlightingConfig config = session.Highlighting;
        output.Line(new StyledText("Highlight Preview", s_headingStyle).Append(" (")
            .Append(config.Enabled ? "enabled" : "disabled", config.Enabled ? s_green : s_red).Append(")"));
        output.Line();
        if (!config.Enabled)
        {
            output.Line("Highlighting is disabled. Run 'highlight on' to enable.", s_dim);
            output.Line();
        }

        var disabled = BuiltInHighlighters.Names.Where(name => !config.IsHighlighterEnabled(name)).ToHashSet(StringComparer.Ordinal);
        HighlighterChain chain = session.Chain;
        foreach (string category in HighlighterCategories.Ordered)
        {
            var samples = HighlighterMetadata.PreviewSamples
                .Where(sample => HighlighterMetadata.All.First(item => item.Name == sample.Highlighters[0]).Category == category)
                .ToList();
            if (samples.Count == 0)
            {
                continue;
            }

            output.Line(HighlighterMetadata.Heading(category), s_bold);
            foreach ((string[] highlighters, string line, string description) in samples)
            {
                output.Line(new StyledText("  ").Append(description, s_dim));
                var off = highlighters.Where(disabled.Contains).ToList();
                if (off.Count > 0)
                {
                    output.Line(new StyledText("  ").Append("Disabled: ", s_yellow).Append(string.Join(", ", off), s_dim));
                }

                output.Line(new StyledText("  ").Append(chain.Apply(line, session.Theme)));
                output.Line();
            }
        }

        if (disabled.Count > 0)
        {
            output.Line("Disabled Highlighters", s_warning);
            foreach (string? name in disabled.Order(StringComparer.Ordinal))
            {
                output.Line($"  - {name}", s_dim);
            }

            output.Line();
            output.Line("Use 'highlight enable <name>' to enable disabled highlighters.", s_dim);
        }

        if (config.CustomHighlighters.Count > 0)
        {
            output.Line();
            output.Line("Custom Highlighters", s_bold);
            foreach (CustomHighlighterDefinition custom in config.CustomHighlighters)
            {
                output.Line(new StyledText("  ").Append(custom.Name, custom.Enabled ? s_green : s_red).Append($": {custom.Pattern} ")
                    .Append($"(style: {custom.Style})", s_dim));
            }
        }
    }

    private static (bool Success, string Message) Export(PgtailSession session, IReadOnlyList<string> args, string currentDirectory)
    {
        string? file = null;
        for (int i = 0; i < args.Count - 1; i++)
        {
            if (args[i] is "--file" or "-f")
            {
                file = args[i + 1];
                break;
            }
        }

        var document = TomlDocument.Parse("# pgtail highlighting configuration\n# Export generated by: highlight export\n\n");
        session.Highlighting.SaveTo(document);
        string text = document.ToString();
        if (file is null)
        {
            return (true, text);
        }

        string path = PathDisplay.Resolve(file, session.Home, currentDirectory);
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

        string path = PathDisplay.Resolve(args[0], session.Home, currentDirectory);
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

        (string? error, List<string>? warnings) = Validate(document.Root);
        if (error is not null)
        {
            return (false, $"Invalid configuration: {error}");
        }

        foreach (string warning in warnings)
        {
            output.Line($"s_warning: {warning}");
        }

        Apply(session.Highlighting, document.Root);
        Save(session, output);
        return (true, $"Imported highlighting config from {path}" + (warnings.Count > 0 ? $" ({warnings.Count} warning(s))" : ""));
    }

    private static (string? Error, List<string> Warnings) Validate(TomlTable root)
    {
        var warnings = new List<string>();
        if (!root.TryGetValue("highlighting", out object? section))
        {
            return ("Missing [highlighting] section", warnings);
        }

        if (section is not TomlTable highlighting)
        {
            return ("[highlighting] section must be a table", warnings);
        }

        if (highlighting.TryGetValue("enabled_highlighters", out object? switches))
        {
            if (switches is not TomlTable table)
            {
                return ("[highlighting.enabled_highlighters] must be a table", warnings);
            }

            foreach (string? name in table.Keys.Where(name => !BuiltInHighlighters.Names.Contains(name)))
            {
                warnings.Add(CloseMatches.Best(name, BuiltInHighlighters.Names) is { } suggestion
                    ? $"Unknown highlighter '{name}'. Did you mean '{suggestion}'?"
                    : $"Unknown highlighter '{name}' - will be ignored");
            }
        }

        if (highlighting.TryGetValue("duration", out object? durations) && durations is TomlTable thresholds)
        {
            foreach (string? key in new[] { "slow", "very_slow", "critical" })
            {
                if (!thresholds.TryGetValue(key, out object? value))
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

        if (!highlighting.TryGetValue("custom", out object? custom))
        {
            return (null, warnings);
        }

        if (custom is not TomlArray entries)
        {
            return ("[highlighting.custom] must be an array", warnings);
        }

        for (int i = 0; i < entries.Count; i++)
        {
            if (entries[i] is not TomlTable entry)
            {
                return ($"Custom highlighter {i} must be a table", warnings);
            }

            if (!entry.TryGetValue("name", out object? nameValue))
            {
                return ($"Custom highlighter {i} missing 'name'", warnings);
            }

            string name = Convert.ToString(nameValue, CultureInfo.InvariantCulture) ?? "";
            if (!entry.TryGetValue("pattern", out object? patternValue))
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
        if (highlighting.TryGetValue("enabled", out object? enabled) && enabled is bool on)
        {
            config.Enabled = on;
        }

        if (highlighting.TryGetValue("max_length", out object? length) && length is long maxLength)
        {
            config.MaxLength = maxLength;
        }

        if (highlighting.TryGetValue("duration", out object? durations) && durations is TomlTable thresholds)
        {
            if (thresholds.TryGetValue("slow", out object? slow))
            {
                config.DurationSlow = (long)slow;
            }

            if (thresholds.TryGetValue("very_slow", out object? verySlow))
            {
                config.DurationVerySlow = (long)verySlow;
            }

            if (thresholds.TryGetValue("critical", out object? critical))
            {
                config.DurationCritical = (long)critical;
            }
        }

        if (highlighting.TryGetValue("enabled_highlighters", out object? switches) && switches is TomlTable table)
        {
            foreach ((string name, object value) in table)
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
