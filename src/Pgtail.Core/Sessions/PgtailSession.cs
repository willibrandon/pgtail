using Pgtail.Configuration;
using Pgtail.Detection;
using Pgtail.Display;
using Pgtail.Filtering;
using Pgtail.Highlighting;
using Pgtail.Notifications;
using Pgtail.Parsing;
using Pgtail.Statistics;
using Pgtail.Styling;

namespace Pgtail.Sessions;

/// <summary>
/// Everything a pgtail session remembers: settings, detected instances, filters, statistics, and the last tail.
/// </summary>
/// <remarks>
/// The REPL, tail mode, and the command line share one session, so a filter set at the prompt applies when tailing
/// and statistics gathered while tailing are there afterward.
/// </remarks>
public sealed class PgtailSession
{
    private readonly InstanceDetector _detector;
    private readonly List<string> _warnings = [];
    private HighlighterChain? _chain;
    private long _chainVersion = -1;

    /// <summary>
    /// Loads the configuration and applies it.
    /// </summary>
    /// <param name="environment">Reads environment variables.</param>
    /// <param name="home">The user's home directory.</param>
    /// <param name="paths">Where configuration and data live.</param>
    /// <param name="processes">Lists running processes, for instance detection.</param>
    public PgtailSession(
        Func<string, string?> environment,
        string home,
        PgtailPaths paths,
        Func<IReadOnlyList<ProcessEntry>> processes)
    {
        ArgumentNullException.ThrowIfNull(environment);
        ArgumentNullException.ThrowIfNull(home);
        ArgumentNullException.ThrowIfNull(paths);
        ArgumentNullException.ThrowIfNull(processes);
        Environment = environment;
        Home = home;
        Paths = paths;
        Store = new ConfigStore(paths);
        Themes = new ThemeManager(paths.ThemesDirectory);
        _detector = new InstanceDetector(environment, home, processes);
        ColorEnabled = string.IsNullOrEmpty(environment("NO_COLOR"));
        (Config, Highlighting) = Store.Load(_warnings.Add);
        Notifications = new NotificationManager(Notifiers.Create(environment), Errors, () => DateTime.Now);
        ApplyConfig();
    }

    /// <summary>
    /// A session for the current user and machine.
    /// </summary>
    /// <returns>The session.</returns>
    public static PgtailSession ForCurrentUser() => new(
        System.Environment.GetEnvironmentVariable,
        System.Environment.GetFolderPath(System.Environment.SpecialFolder.UserProfile),
        PgtailPaths.ForCurrentUser(System.Environment.GetEnvironmentVariable),
        ProcessTable.List);

    /// <summary>
    /// Reads environment variables.
    /// </summary>
    public Func<string, string?> Environment { get; }

    /// <summary>
    /// The user's home directory.
    /// </summary>
    public string Home { get; }

    /// <summary>
    /// Where configuration and data live.
    /// </summary>
    public PgtailPaths Paths { get; }

    /// <summary>
    /// Reads and writes the configuration file.
    /// </summary>
    public ConfigStore Store { get; }

    /// <summary>
    /// The settings in force.
    /// </summary>
    public PgtailConfig Config { get; private set; }

    /// <summary>
    /// The semantic highlighting settings in force.
    /// </summary>
    public HighlightingConfig Highlighting { get; private set; }

    /// <summary>
    /// The color themes.
    /// </summary>
    public ThemeManager Themes { get; }

    /// <summary>
    /// The current theme.
    /// </summary>
    public Theme Theme => Themes.Current;

    /// <summary>
    /// False when <c>NO_COLOR</c> is set, so output keeps attributes but drops colors.
    /// </summary>
    public bool ColorEnabled { get; }

    /// <summary>
    /// The detected instances.
    /// </summary>
    public IReadOnlyList<PostgresInstance> Instances { get; private set; } = [];

    /// <summary>
    /// The levels shown, or null for all of them.
    /// </summary>
    public HashSet<LogLevel>? ActiveLevels { get; set; }

    /// <summary>
    /// The regular expression filters and highlights.
    /// </summary>
    public RegexFilterState Regex { get; set; } = new();

    /// <summary>
    /// The field filters for csvlog and jsonlog entries.
    /// </summary>
    public FieldFilterState Fields { get; set; } = new();

    /// <summary>
    /// The time filter.
    /// </summary>
    public TimeFilter Time { get; set; } = TimeFilter.Empty;

    /// <summary>
    /// The slow query thresholds.
    /// </summary>
    public SlowQueryConfig Slow { get; set; } = new();

    /// <summary>
    /// Query durations seen this session.
    /// </summary>
    public DurationStats Durations { get; } = new();

    /// <summary>
    /// Errors and warnings seen this session.
    /// </summary>
    public ErrorStats Errors { get; } = new();

    /// <summary>
    /// Connections seen this session.
    /// </summary>
    public ConnectionStats Connections { get; } = new();

    /// <summary>
    /// Desktop notification rules and delivery.
    /// </summary>
    public NotificationManager Notifications { get; }

    /// <summary>
    /// The display mode and output format.
    /// </summary>
    public DisplayState Display { get; } = new();

    /// <summary>
    /// What the last tail read, or null before the first tail.
    /// </summary>
    public TailSource? LastSource { get; set; }

    /// <summary>
    /// The log format the last tail detected, or null before one was detected.
    /// </summary>
    public LogFormat? DetectedFormat { get; set; }

    /// <summary>
    /// The entries of the last tail.
    /// </summary>
    public LogBuffer Buffer { get; } = new();

    /// <summary>
    /// The semantic highlighters for the current highlighting settings, rebuilt when they change.
    /// </summary>
    public HighlighterChain Chain
    {
        get
        {
            if (_chain is null || _chainVersion != Highlighting.Version)
            {
                _chain = Highlighting.GetChain();
                _chainVersion = Highlighting.Version;
            }

            return _chain;
        }
    }

    /// <summary>
    /// Takes the warnings gathered while loading the configuration.
    /// </summary>
    /// <returns>The warnings, which are then forgotten.</returns>
    public IReadOnlyList<string> TakeWarnings()
    {
        var warnings = _warnings.ToArray();
        _warnings.Clear();
        return warnings;
    }

    /// <summary>
    /// Scans for PostgreSQL instances again.
    /// </summary>
    public void Refresh() => Instances = _detector.DetectAll();

    /// <summary>
    /// Loads the configuration file again and applies it, as after <c>config reset</c> or <c>config edit</c>.
    /// </summary>
    public void Reload()
    {
        (Config, Highlighting) = Store.Load(_warnings.Add);
        ApplyConfig();
    }

    /// <summary>
    /// Whether an entry passes every filter, applied in order: time, level, fields, then regular expressions.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>True when it should be shown.</returns>
    public bool ShouldShow(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        return (!Time.IsActive || Time.Matches(entry))
            && LogLevels.ShouldShow(entry.Level, ActiveLevels)
            && Fields.Matches(entry)
            && (!Regex.HasFilters || Regex.ShouldShow(entry.RawUtf8.Span));
    }

    /// <summary>
    /// Counts an entry in the statistics and checks it against the notification rules.
    /// </summary>
    /// <remarks>
    /// Every entry read is observed, whether or not the filters show it.
    /// </remarks>
    /// <param name="entry">The entry.</param>
    /// <returns>The notification the entry triggered, for the caller to deliver off the UI thread, or null.</returns>
    public Notification? Observe(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (DurationExtractor.Extract(entry.Message) is { } duration)
        {
            Durations.Add(duration);
        }

        Errors.Add(entry);
        _ = Connections.Add(entry);
        return Notifications.Check(entry);
    }

    /// <summary>
    /// Formats an entry for streaming output: JSON, a slow query, legacy highlights, or the display mode.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <param name="highlighted">False for output that drops styles anyway, such as a pipe, which skips semantic
    /// highlighting.</param>
    /// <returns>The formatted entry.</returns>
    public StyledText FormatEntry(LogEntry entry, bool highlighted = true)
    {
        ArgumentNullException.ThrowIfNull(entry);
        if (Display.OutputFormat == OutputFormat.Json)
        {
            return new StyledText(EntryFormatter.Json(entry));
        }

        if (SlowLevel(entry) is { } level)
        {
            return EntryFormatter.SlowQuery(entry, level, Theme);
        }

        if (Regex.HasHighlights)
        {
            using var message = new Matching.Utf8Text(entry.Message);
            var spans = Regex.Highlights.SelectMany(highlight => highlight.FindSpans(message)).ToList();
            if (spans.Count > 0)
            {
                return EntryFormatter.WithHighlights(entry, spans, Theme);
            }
        }

        return EntryFormatter.Format(entry, Display, Theme, highlighted ? Chain : HighlighterChain.None);
    }

    /// <summary>
    /// How slow a query an entry logged was, when slow query highlighting is on and its duration passes a threshold.
    /// </summary>
    /// <param name="entry">The entry.</param>
    /// <returns>The level, or null.</returns>
    public SlowQueryLevel? SlowLevel(LogEntry entry)
    {
        ArgumentNullException.ThrowIfNull(entry);
        return Slow.Enabled && DurationExtractor.Extract(entry.Message) is { } duration ? Slow.GetLevel(duration) : null;
    }

    /// <summary>
    /// Applies one setting after <c>set</c> or <c>unset</c> changed it.
    /// </summary>
    /// <param name="key">The dotted key.</param>
    public void ApplySetting(string key)
    {
        ArgumentNullException.ThrowIfNull(key);
        if (key == "default.levels")
        {
            ActiveLevels = ParseLevels(Config.DefaultLevels);
        }
        else if (key.StartsWith("slow.", StringComparison.Ordinal))
        {
            Slow = new SlowQueryConfig
            {
                Enabled = true,
                WarningMs = Config.SlowWarn,
                SlowMs = Config.SlowError,
                CriticalMs = Config.SlowCritical,
            };
        }
        else if (key == "theme.name")
        {
            _ = Themes.Switch(Config.ThemeName);
        }
        else if (key.StartsWith("notifications.", StringComparison.Ordinal))
        {
            ApplyNotifications();
        }
        else if (key.StartsWith("highlighting.", StringComparison.Ordinal))
        {
            ConfigStore.ApplyHighlighting(Config, Highlighting);
        }
    }

    private static HashSet<LogLevel>? ParseLevels(IEnumerable<string> names)
    {
        var levels = new HashSet<LogLevel>();
        foreach (var name in names)
        {
            if (LogLevels.TryParse(name, out var level))
            {
                _ = levels.Add(level);
            }
        }

        return levels.Count > 0 ? levels : null;
    }

    private void ApplyConfig()
    {
        ActiveLevels = ParseLevels(Config.DefaultLevels);
        Slow = new SlowQueryConfig
        {
            Enabled = true,
            WarningMs = Config.SlowWarn,
            SlowMs = Config.SlowError,
            CriticalMs = Config.SlowCritical,
        };

        if (!Themes.Switch(Config.ThemeName))
        {
            _ = Themes.Switch(BuiltInThemes.DefaultName);
        }

        ApplyNotifications();
    }

    private void ApplyNotifications()
    {
        var config = Notifications.Config;
        config.Clear();
        config.Enabled = Config.NotificationsEnabled;
        var levels = new HashSet<LogLevel>();
        foreach (var name in Config.NotificationLevels)
        {
            if (LogLevels.TryParse(name, out var level))
            {
                _ = levels.Add(level);
            }
        }

        if (levels.Count > 0)
        {
            config.Add(NotificationRule.ForLevels(levels));
        }

        foreach (var text in Config.NotificationPatterns)
        {
            var (pattern, caseSensitive) = SettingsSchema.NotificationPattern(text);
            try
            {
                config.Add(NotificationRule.ForPattern(pattern, caseSensitive));
            }
            catch (FormatException exception)
            {
                _warnings.Add($"Invalid notification pattern {text}: {exception.Message}");
            }
        }

        if (Config.NotificationErrorRate is { } rate)
        {
            config.Add(NotificationRule.ForErrorRate(rate));
        }

        if (Config.NotificationSlowQueryMs is { } slow)
        {
            config.Add(NotificationRule.ForSlowQuery(slow));
        }

        config.QuietHours = null;
        if (Config.QuietHours is { } quiet)
        {
            try
            {
                config.QuietHours = QuietHours.Parse(quiet);
            }
            catch (FormatException exception)
            {
                _warnings.Add($"Invalid quiet hours {quiet}: {exception.Message}");
            }
        }
    }
}
