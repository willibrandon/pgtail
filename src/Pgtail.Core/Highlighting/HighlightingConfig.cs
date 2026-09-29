using System.Globalization;
using Pgtail.Toml;

namespace Pgtail.Highlighting;

/// <summary>
/// The semantic highlighting settings.
/// </summary>
/// <remarks>
/// The global switch, per-highlighter switches, duration thresholds, and custom highlighters.
/// </remarks>
public sealed class HighlightingConfig
{
    /// <summary>
    /// The default number of characters highlighted per message.
    /// </summary>
    public const long DefaultMaxLength = 10_240;

    private readonly Dictionary<string, bool> _enabled = new(StringComparer.Ordinal);
    private readonly List<CustomHighlighterDefinition> _custom = [];
    private (long Version, HighlighterChain Chain)? _chain;

    /// <summary>
    /// Creates the default configuration.
    /// </summary>
    public HighlightingConfig() => Reset();

    /// <summary>
    /// Whether highlighting is on at all.
    /// </summary>
    public bool Enabled
    {
        get;
        set => Change(() => field = value);
    }

    /// <summary>
    /// How many characters of each message are highlighted.
    /// </summary>
    public long MaxLength
    {
        get;
        set => Change(() => field = value);
    }

    /// <summary>
    /// The slow duration threshold in milliseconds.
    /// </summary>
    public long DurationSlow
    {
        get;
        set => Change(() => field = value);
    }

    /// <summary>
    /// The very slow duration threshold in milliseconds.
    /// </summary>
    public long DurationVerySlow
    {
        get;
        set => Change(() => field = value);
    }

    /// <summary>
    /// The critical duration threshold in milliseconds.
    /// </summary>
    public long DurationCritical
    {
        get;
        set => Change(() => field = value);
    }

    /// <summary>
    /// The custom highlighters in the order they were added.
    /// </summary>
    public IReadOnlyList<CustomHighlighterDefinition> CustomHighlighters => _custom;

    /// <summary>
    /// Counts every change, so a chain built from an older state is rebuilt.
    /// </summary>
    public long Version { get; private set; }

    /// <summary>
    /// Whether a highlighter runs: highlighting is on and the highlighter is not switched off.
    /// </summary>
    /// <param name="name">The highlighter name.</param>
    /// <returns>True when it runs.</returns>
    public bool IsHighlighterEnabled(string name) => Enabled && _enabled.GetValueOrDefault(name, true);

    /// <summary>
    /// Whether a highlighter is switched on, regardless of the global switch.
    /// </summary>
    /// <param name="name">The highlighter name.</param>
    /// <returns>True unless it was switched off.</returns>
    public bool IsSwitchedOn(string name) => _enabled.GetValueOrDefault(name, true);

    /// <summary>
    /// Switches a highlighter on or off.
    /// </summary>
    /// <param name="name">The highlighter name.</param>
    /// <param name="enabled">True to switch it on.</param>
    public void SetHighlighter(string name, bool enabled) => Change(() => _enabled[name] = enabled);

    /// <summary>
    /// Adds a custom highlighter.
    /// </summary>
    /// <param name="definition">The definition.</param>
    /// <exception cref="ArgumentException">The name belongs to a built-in or an existing custom highlighter.</exception>
    public void AddCustom(CustomHighlighterDefinition definition)
    {
        ArgumentNullException.ThrowIfNull(definition);
        if (BuiltInHighlighters.Names.Contains(definition.Name))
        {
            throw new ArgumentException($"Cannot use name '{definition.Name}': conflicts with built-in highlighter");
        }

        if (_custom.Any(existing => existing.Name == definition.Name))
        {
            throw new ArgumentException($"Custom highlighter '{definition.Name}' already exists");
        }

        Change(() => _custom.Add(definition));
    }

    /// <summary>
    /// Removes a custom highlighter.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>True when it was removed.</returns>
    public bool RemoveCustom(string name)
    {
        var index = _custom.FindIndex(existing => existing.Name == name);
        if (index < 0)
        {
            return false;
        }

        Change(() => _custom.RemoveAt(index));
        return true;
    }

    /// <summary>
    /// Finds a custom highlighter.
    /// </summary>
    /// <param name="name">The name.</param>
    /// <returns>The definition, or null.</returns>
    public CustomHighlighterDefinition? GetCustom(string name) => _custom.Find(existing => existing.Name == name);

    /// <summary>
    /// Restores every default: highlighting on, every built-in on, default thresholds, no custom highlighters.
    /// </summary>
    public void Reset() => Change(() =>
    {
        Enabled = true;
        MaxLength = DefaultMaxLength;
        DurationSlow = 100;
        DurationVerySlow = 500;
        DurationCritical = 5000;
        _enabled.Clear();
        _custom.Clear();
    });

    /// <summary>
    /// The chain for the current settings, built again only after a change.
    /// </summary>
    /// <returns>The chain; empty when highlighting is off.</returns>
    public HighlighterChain GetChain()
    {
        if (_chain is { } cached && cached.Version == Version)
        {
            return cached.Chain;
        }

        var highlighters = BuiltInHighlighters.Create(DurationSlow, DurationVerySlow, DurationCritical)
            .Where(highlighter => IsHighlighterEnabled(highlighter.Name))
            .ToList();
        if (Enabled)
        {
            highlighters.AddRange(
                _custom.Where(custom => custom.Enabled).Select(CustomRegexHighlighter.Create).OfType<IHighlighter>());
        }

        var chain = new HighlighterChain(highlighters, (int)Math.Clamp(MaxLength, 0, int.MaxValue));
        _chain = (Version, chain);
        return chain;
    }

    /// <summary>
    /// Reads the <c>[highlighting]</c> section of a configuration document.
    /// </summary>
    /// <remarks>
    /// Values of the wrong type keep their defaults and are reported; custom highlighters without a name or pattern
    /// are skipped.
    /// </remarks>
    /// <param name="root">The configuration root table.</param>
    /// <param name="warn">Receives a message for each value that is ignored.</param>
    /// <returns>The configuration.</returns>
    public static HighlightingConfig FromToml(TomlTable root, Action<string> warn)
    {
        ArgumentNullException.ThrowIfNull(root);
        ArgumentNullException.ThrowIfNull(warn);
        var config = new HighlightingConfig();
        if (!root.TryGetTable("highlighting", out var section))
        {
            return config;
        }

        if (Read<bool>(section, "enabled", "highlighting.enabled", warn) is { } enabled)
        {
            config.Enabled = enabled;
        }

        if (ReadPositive(section, "max_length", "highlighting.max_length", warn) is { } maxLength)
        {
            config.MaxLength = maxLength;
        }

        if (section.TryGetTable("duration", out var duration))
        {
            config.DurationSlow = ReadPositive(duration, "slow", "highlighting.duration.slow", warn) ?? config.DurationSlow;
            config.DurationVerySlow =
                ReadPositive(duration, "very_slow", "highlighting.duration.very_slow", warn) ?? config.DurationVerySlow;
            config.DurationCritical =
                ReadPositive(duration, "critical", "highlighting.duration.critical", warn) ?? config.DurationCritical;
        }

        if (section.TryGetTable("enabled_highlighters", out var switches))
        {
            foreach (var (name, value) in switches)
            {
                if (value is bool flag)
                {
                    config.SetHighlighter(name, flag);
                }
                else
                {
                    warn($"Invalid value for highlighting.enabled_highlighters.{name}: must be true or false. Using default.");
                }
            }
        }

        if (section.TryGetValue("custom", out var custom) && custom is TomlArray entries)
        {
            foreach (var entry in entries)
            {
                if (entry is TomlTable table && ReadCustom(table) is { } definition && definition.Name.Length > 0
                    && !BuiltInHighlighters.Names.Contains(definition.Name) && config.GetCustom(definition.Name) is null)
                {
                    config.Change(() => config._custom.Add(definition));
                }
            }
        }

        return config;
    }

    /// <summary>
    /// Writes every setting to the <c>[highlighting]</c> section of a configuration document, keeping its comments.
    /// </summary>
    /// <param name="document">The configuration document.</param>
    public void SaveTo(TomlDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);
        document.Set(["highlighting", "enabled"], Enabled);
        document.Set(["highlighting", "max_length"], MaxLength);
        document.Set(["highlighting", "duration", "slow"], DurationSlow);
        document.Set(["highlighting", "duration", "very_slow"], DurationVerySlow);
        document.Set(["highlighting", "duration", "critical"], DurationCritical);

        var disabled = BuiltInHighlighters.Names.Where(name => !IsSwitchedOn(name)).ToList();
        if (disabled.Count == 0)
        {
            document.RemoveTable(["highlighting", "enabled_highlighters"]);
        }
        else
        {
            if (document.Root.GetPath(["highlighting", "enabled_highlighters"]) is TomlTable existing)
            {
                foreach (var name in existing.Keys.ToList())
                {
                    document.Remove(["highlighting", "enabled_highlighters", name]);
                }
            }

            foreach (var name in disabled)
            {
                document.Set(["highlighting", "enabled_highlighters", name], false);
            }
        }

        document.RemoveTable(["highlighting", "custom"]);
        if (_custom.Count > 0)
        {
            document.Set(["highlighting", "custom"], _custom.Select(ToInlineTable).ToList());
        }
    }

    /// <summary>
    /// Writes one highlighter's switch to a configuration document, storing only a switched-off highlighter.
    /// </summary>
    /// <param name="document">The configuration document.</param>
    /// <param name="name">The highlighter name.</param>
    /// <param name="enabled">Whether it is on.</param>
    public static void SaveSwitch(TomlDocument document, string name, bool enabled)
    {
        ArgumentNullException.ThrowIfNull(document);
        if (enabled)
        {
            document.Remove(["highlighting", "enabled_highlighters", name]);
            if (document.Root.GetPath(["highlighting", "enabled_highlighters"]) is TomlTable { Count: 0 })
            {
                document.RemoveTable(["highlighting", "enabled_highlighters"]);
            }
        }
        else
        {
            document.Set(["highlighting", "enabled_highlighters", name], false);
        }
    }

    /// <summary>
    /// A custom highlighter as an ordered list of TOML keys and values.
    /// </summary>
    /// <param name="definition">The definition.</param>
    /// <returns>The keys and values; <c>enabled</c> appears only when false.</returns>
    public static List<KeyValuePair<string, object>> ToInlineTable(CustomHighlighterDefinition definition)
    {
        ArgumentNullException.ThrowIfNull(definition);
        var pairs = new List<KeyValuePair<string, object>>
        {
            new("name", definition.Name),
            new("pattern", definition.Pattern),
            new("style", definition.Style),
            new("priority", definition.Priority),
        };

        if (!definition.Enabled)
        {
            pairs.Add(new("enabled", false));
        }

        return pairs;
    }

    private static CustomHighlighterDefinition? ReadCustom(TomlTable table)
    {
        if (!table.TryGetValue("name", out var name) || !table.TryGetValue("pattern", out var pattern))
        {
            return null;
        }

        return new CustomHighlighterDefinition(
            Text(name),
            Text(pattern),
            table.TryGetValue("style", out var style) ? Text(style) : "yellow",
            table.TryGetValue("priority", out var priority) && priority is long number ? number : 1050,
            !table.TryGetValue("enabled", out var enabled) || enabled is not bool flag || flag);
    }

    private static string Text(object value) => value switch
    {
        string text => text,
        bool flag => flag ? "true" : "false",
        _ => Convert.ToString(value, CultureInfo.InvariantCulture) ?? "",
    };

    private static T? Read<T>(TomlTable table, string key, string setting, Action<string> warn)
        where T : struct
    {
        if (!table.TryGetValue(key, out var value))
        {
            return null;
        }

        if (value is T typed)
        {
            return typed;
        }

        warn($"Invalid value for {setting}: must be true or false. Using default.");
        return null;
    }

    private static long? ReadPositive(TomlTable table, string key, string setting, Action<string> warn)
    {
        if (!table.TryGetValue(key, out var value))
        {
            return null;
        }

        if (value is long number && number > 0)
        {
            return number;
        }

        warn($"Invalid value for {setting}: must be a positive integer. Using default.");
        return null;
    }

    private void Change(Action change)
    {
        change();
        Version++;
    }
}
