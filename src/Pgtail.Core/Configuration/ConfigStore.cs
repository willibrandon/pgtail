using System.Collections.Frozen;
using System.Globalization;
using System.Text;
using Pgtail.Highlighting;
using Pgtail.Toml;

namespace Pgtail.Configuration;

/// <summary>
/// Reads and writes <c>config.toml</c>, keeping the comments and layout of the file.
/// </summary>
/// <param name="paths">Where the configuration lives.</param>
public sealed class ConfigStore(PgtailPaths paths)
{
    // Settings earlier releases wrote or documented that pgtail no longer reads; a file that has them is still valid.
    private static readonly FrozenSet<string> s_retiredKeys =
        ["default.follow", "display.timestamp_format", "display.show_pid", "display.show_level", "updates.last_version", "buffer"];

    /// <summary>
    /// The file a new configuration starts from, documenting every setting.
    /// </summary>
    public const string DefaultTemplate = """
        # pgtail configuration file
        # https://pgtail.dev/configuration/

        [default]
        # levels = ["ERROR", "WARNING", "FATAL"]  # Filter to specific log levels (empty = all)

        [slow]
        # warn = 100      # Yellow highlight threshold (ms)
        # error = 500     # Orange highlight threshold (ms)
        # critical = 1000 # Red highlight threshold (ms)

        [theme]
        # name = "dark"  # Options: dark, light, high-contrast, monokai, solarized-dark, solarized-light

        [notifications]
        # enabled = false                # Enable desktop notifications
        # levels = ["FATAL", "PANIC"]    # Levels that trigger notifications
        # patterns = ["/deadlock detected/"]  # Regex patterns that trigger notifications
        # error_rate = 10                # Alert when errors/min exceeds this threshold
        # slow_query_ms = 500            # Alert when query duration exceeds this (ms)
        # quiet_hours = "22:00-08:00"    # Suppress notifications during these hours

        [updates]
        # check = true                 # Enable startup update check (set to false to disable)
        # last_check = ""              # Timestamp of last update check (managed automatically)

        [highlighting]
        # enabled = true              # Enable semantic highlighting (global toggle)
        # max_length = 10240          # Stop highlighting after this many characters (depth limit)

        [highlighting.duration]
        # slow = 100                  # Slow query threshold (ms) - yellow
        # very_slow = 500             # Very slow query threshold (ms) - orange
        # critical = 5000             # Critical query threshold (ms) - red

        [highlighting.enabled_highlighters]
        # Toggle individual highlighters (all default to true)
        # timestamp = true            # Timestamps with date, time, ms, timezone
        # pid = true                  # Process IDs in brackets
        # context = true              # DETAIL:, HINT:, CONTEXT: labels
        # sqlstate = true             # SQLSTATE error codes
        # error_name = true           # Error names (unique_violation, deadlock_detected)
        # duration = true             # Query durations with threshold coloring
        # memory = true               # Memory values (kB, MB, GB)
        # statistics = true           # Checkpoint/vacuum statistics
        # identifier = true           # Double-quoted identifiers
        # relation = true             # Table/index names
        # schema = true               # Schema-qualified names
        # lsn = true                  # Log sequence numbers
        # wal_segment = true          # WAL segment filenames
        # txid = true                 # Transaction IDs
        # connection = true           # Connection info (host, port, user)
        # ip = true                   # IP addresses
        # backend = true              # Backend process types
        # sql_keyword = true          # SQL keywords
        # sql_string = true           # SQL strings
        # sql_number = true           # SQL numbers
        # sql_param = true            # SQL parameters ($1, $2)
        # sql_operator = true         # SQL operators
        # lock_type = true            # Lock type names
        # lock_wait = true            # Lock wait info
        # checkpoint = true           # Checkpoint messages
        # recovery = true             # Recovery messages
        # boolean = true              # Boolean values
        # null = true                 # NULL keyword
        # oid = true                  # Object IDs
        # path = true                 # File paths

        # [[highlighting.custom]]
        # name = "request_id"         # Custom highlighter name
        # pattern = "REQ-[0-9]{10}"   # Regex pattern
        # style = "yellow"            # Color to apply
        # priority = 1050             # Processing order (higher = later)

        """;

    /// <summary>
    /// Where the configuration lives.
    /// </summary>
    public PgtailPaths Paths { get; } = paths;

    /// <summary>
    /// The configuration file.
    /// </summary>
    public string ConfigFile => Paths.ConfigFile;

    /// <summary>
    /// Whether the configuration file exists.
    /// </summary>
    public bool Exists => File.Exists(ConfigFile);

    /// <summary>
    /// Loads the configuration, reporting invalid values and keeping their defaults.
    /// </summary>
    /// <remarks>
    /// A missing file gives the defaults. A file that is not valid TOML gives the defaults with a warning. Slow
    /// thresholds that are not ascending are replaced by their defaults, and settings pgtail does not know are reported
    /// and ignored.
    /// </remarks>
    /// <param name="warn">Receives each warning.</param>
    /// <returns>The settings and the highlighting configuration.</returns>
    public (PgtailConfig Config, HighlightingConfig Highlighting) Load(Action<string> warn)
    {
        ArgumentNullException.ThrowIfNull(warn);
        var config = new PgtailConfig();
        var highlighting = new HighlightingConfig();
        if (!Exists)
        {
            return (config, highlighting);
        }

        TomlDocument document;
        try
        {
            document = TomlDocument.Load(ConfigFile);
        }
        catch (Exception exception) when (exception is TomlException or IOException or UnauthorizedAccessException)
        {
            warn($"Config parse error: {exception.Message}. Using defaults.");
            return (config, highlighting);
        }

        foreach (string key in UnknownKeys(document.Root))
        {
            warn($"Unknown setting {key}, ignored.");
        }

        foreach (SettingDefinition setting in SettingsSchema.All)
        {
            if (document.Root.GetPath(setting.Path) is not { } raw)
            {
                continue;
            }

            try
            {
                config[setting.Key] = setting.Validate(raw);
            }
            catch (FormatException exception)
            {
                warn($"Invalid value for {setting.Key}: {exception.Message}. Using default.");
            }
        }

        CheckSlowOrder(config, warn);
        ApplyHighlighting(config, highlighting);
        highlighting.LoadCustom(document.Root);
        return (config, highlighting);
    }

    /// <summary>
    /// Copies the highlighting settings of a configuration into a highlighting configuration.
    /// </summary>
    /// <param name="config">The settings.</param>
    /// <param name="highlighting">The highlighting configuration to update.</param>
    public static void ApplyHighlighting(PgtailConfig config, HighlightingConfig highlighting)
    {
        ArgumentNullException.ThrowIfNull(config);
        ArgumentNullException.ThrowIfNull(highlighting);
        highlighting.Enabled = (bool)config["highlighting.enabled"]!;
        highlighting.MaxLength = (long)config["highlighting.max_length"]!;
        highlighting.DurationSlow = (long)config["highlighting.duration.slow"]!;
        highlighting.DurationVerySlow = (long)config["highlighting.duration.very_slow"]!;
        highlighting.DurationCritical = (long)config["highlighting.duration.critical"]!;
        foreach (string name in BuiltInHighlighters.Names)
        {
            highlighting.SetHighlighter(name, (bool)config[$"highlighting.enabled_highlighters.{name}"]!);
        }
    }

    /// <summary>
    /// Saves one setting.
    /// </summary>
    /// <param name="key">The dotted key.</param>
    /// <param name="value">The validated value.</param>
    /// <returns>Null on success, otherwise why the file was not changed.</returns>
    public string? Save(string key, object value) => Edit(document => document.Set(key.Split('.'), value));

    /// <summary>
    /// Removes one setting from the file.
    /// </summary>
    /// <param name="key">The dotted key.</param>
    /// <returns>True when the setting was in the file and was removed.</returns>
    public bool Delete(string key)
    {
        if (!Exists)
        {
            return false;
        }

        bool removed = false;
        return Edit(document => removed = document.Remove(key.Split('.'))) is null && removed;
    }

    /// <summary>
    /// Saves the whole highlighting configuration.
    /// </summary>
    /// <param name="highlighting">The highlighting configuration.</param>
    /// <returns>Null on success, otherwise why the file was not changed.</returns>
    public string? SaveHighlighting(HighlightingConfig highlighting) => Edit(highlighting.SaveTo);

    /// <summary>
    /// Saves one highlighter's switch.
    /// </summary>
    /// <param name="name">The highlighter name.</param>
    /// <param name="enabled">Whether it is on.</param>
    /// <returns>Null on success, otherwise why the file was not changed.</returns>
    public string? SaveHighlighterSwitch(string name, bool enabled) =>
        Edit(document => HighlightingConfig.SaveSwitch(document, name, enabled));

    /// <summary>
    /// Moves the configuration file aside so every setting returns to its default.
    /// </summary>
    /// <param name="now">The time used in the backup name.</param>
    /// <returns>The backup file, or null when there was no configuration file.</returns>
    /// <exception cref="IOException">The file could not be moved.</exception>
    public string? Reset(DateTime now)
    {
        if (!Exists)
        {
            return null;
        }

        string backup = ConfigFile + ".bak." + now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        File.Move(ConfigFile, backup, overwrite: false);
        return backup;
    }

    /// <summary>
    /// Writes the documented template when no configuration file exists yet.
    /// </summary>
    public void CreateDefault()
    {
        if (!Exists)
        {
            Write(DefaultTemplate);
        }
    }

    /// <summary>
    /// Writes the configuration file, creating its directory.
    /// </summary>
    /// <param name="text">The file contents.</param>
    public void Write(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        Directory.CreateDirectory(Paths.ConfigDirectory);
        string temporary = ConfigFile + ".tmp";
        File.WriteAllText(temporary, text, new UTF8Encoding(encoderShouldEmitUTF8Identifier: false));
        File.Move(temporary, ConfigFile, overwrite: true);
    }

    private string? Edit(Action<TomlDocument> change)
    {
        TomlDocument document;
        try
        {
            document = Exists ? TomlDocument.Load(ConfigFile) : TomlDocument.Parse("");
        }
        catch (TomlException exception)
        {
            return $"Cannot update {ConfigFile}: {exception.Message}. Fix the file with 'config edit' first.";
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return $"Cannot read config: {exception.Message}";
        }

        try
        {
            change(document);
            Write(document.ToString());
            return null;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return $"Cannot save config: {exception.Message}";
        }
        catch (InvalidOperationException exception)
        {
            return $"Cannot save config: {exception.Message}";
        }
    }

    /// <summary>
    /// Finds what keeps configuration text from being saved.
    /// </summary>
    /// <remarks>
    /// A problem is a TOML error, a setting pgtail does not know, an invalid value, or slow thresholds that do not ascend.
    /// </remarks>
    /// <param name="text">The text.</param>
    /// <returns>The problems, empty when the text can be saved.</returns>
    public static List<string> Problems(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        TomlDocument document;
        try
        {
            document = TomlDocument.Parse(Encoding.UTF8.GetBytes(text));
        }
        catch (TomlException exception)
        {
            return [exception.Message];
        }

        var problems = UnknownKeys(document.Root).Select(key => $"Unknown setting {key}").ToList();
        var config = new PgtailConfig();
        foreach (SettingDefinition setting in SettingsSchema.All)
        {
            if (document.Root.GetPath(setting.Path) is not { } raw)
            {
                continue;
            }

            try
            {
                config[setting.Key] = setting.Validate(raw);
            }
            catch (FormatException exception)
            {
                problems.Add($"Invalid value for {setting.Key}: {exception.Message}");
            }
        }

        if (SlowOrderProblem(config) is { } order)
        {
            problems.Add(order);
        }

        return problems;
    }

    // The keys of a table and the tables in it that are not settings, as dotted paths. Custom highlighters are checked
    // when they load, and a highlighter switch must name a built-in highlighter.
    private static IEnumerable<string> UnknownKeys(TomlTable table, string prefix = "")
    {
        foreach ((string name, object value) in table)
        {
            string key = prefix.Length == 0 ? name : $"{prefix}.{name}";
            if (key == "highlighting.custom" || s_retiredKeys.Contains(key) || SettingsSchema.Find(key) is not null)
            {
                continue;
            }

            if (key == "highlighting.enabled_highlighters" && value is TomlTable switches)
            {
                foreach (string? highlighter in switches.Keys.Where(highlighter => !BuiltInHighlighters.Names.Contains(highlighter)))
                {
                    yield return $"{key}.{highlighter}";
                }

                continue;
            }

            if (value is not TomlTable child)
            {
                yield return key;
                continue;
            }

            foreach (string inner in UnknownKeys(child, key))
            {
                yield return inner;
            }
        }
    }

    private static string? SlowOrderProblem(PgtailConfig config) =>
        config.SlowWarn >= config.SlowError
            ? $"slow.error ({config.SlowError}) must be greater than slow.warn ({config.SlowWarn})"
            : config.SlowError >= config.SlowCritical
                ? $"slow.critical ({config.SlowCritical}) must be greater than slow.error ({config.SlowError})"
                : null;

    private static void CheckSlowOrder(PgtailConfig config, Action<string> warn)
    {
        if (SlowOrderProblem(config) is not { } problem)
        {
            return;
        }

        warn($"{problem}. Using defaults.");
        foreach (string? key in new[] { "slow.warn", "slow.error", "slow.critical" })
        {
            config[key] = SettingsSchema.Find(key)!.Default;
        }
    }
}
