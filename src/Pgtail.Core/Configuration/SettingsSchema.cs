using System.Text.RegularExpressions;
using Pgtail.Filtering;
using Pgtail.Highlighting;
using Pgtail.Matching;
using Pgtail.Styling;

namespace Pgtail.Configuration;

/// <summary>
/// Every configuration setting with its default and validation.
/// </summary>
public static partial class SettingsSchema
{
    private static readonly string[] s_validLevels =
        ["DEBUG", "DEBUG1", "DEBUG2", "DEBUG3", "DEBUG4", "DEBUG5", "ERROR", "FATAL", "INFO", "LOG", "NOTICE", "PANIC", "WARNING"];

    /// <summary>
    /// The settings in display order.
    /// </summary>
    public static IReadOnlyList<SettingDefinition> All { get; } = Build();

    /// <summary>
    /// The setting keys in display order.
    /// </summary>
    public static IReadOnlyList<string> Keys { get; } = [.. All.Select(setting => setting.Key)];

    /// <summary>
    /// Finds a setting.
    /// </summary>
    /// <param name="key">The dotted key.</param>
    /// <returns>The setting, or null for an unknown key.</returns>
    public static SettingDefinition? Find(string key) => All.FirstOrDefault(setting => setting.Key == key);

    private static List<SettingDefinition> Build()
    {
        var settings = new List<SettingDefinition>
        {
            new("default.levels", new List<string>(), SettingType.List, LogLevelList),
            new("slow.warn", 100L, SettingType.Integer, value => PositiveInteger(value)),
            new("slow.error", 500L, SettingType.Integer, value => PositiveInteger(value)),
            new("slow.critical", 1000L, SettingType.Integer, value => PositiveInteger(value)),
            new("theme.name", BuiltInThemes.DefaultName, SettingType.Text, ThemeName),
            new("notifications.enabled", false, SettingType.Boolean, value => Boolean(value)),
            new("notifications.levels", new List<string> { "FATAL", "PANIC" }, SettingType.List, LogLevelList),
            new("notifications.patterns", new List<string>(), SettingType.List, PatternList),
            new("notifications.error_rate", null, SettingType.Integer, value => PositiveInteger(value)),
            new("notifications.slow_query_ms", null, SettingType.Integer, value => PositiveInteger(value)),
            new("notifications.quiet_hours", null, SettingType.Text, QuietHours),
            new("updates.check", true, SettingType.Boolean, value => Boolean(value)),
            new("updates.last_check", "", SettingType.Text, Iso8601),
            new("highlighting.enabled", true, SettingType.Boolean, value => Boolean(value)),
            new("highlighting.max_length", HighlightingConfig.DefaultMaxLength, SettingType.Integer, value => PositiveInteger(value)),
            new("highlighting.duration.slow", 100L, SettingType.Integer, value => PositiveInteger(value)),
            new("highlighting.duration.very_slow", 500L, SettingType.Integer, value => PositiveInteger(value)),
            new("highlighting.duration.critical", 5000L, SettingType.Integer, value => PositiveInteger(value)),
        };

        settings.AddRange(BuiltInHighlighters.Names.Select(name =>
            new SettingDefinition($"highlighting.enabled_highlighters.{name}", true, SettingType.Boolean, value => Boolean(value))));
        return settings;
    }

    private static bool Boolean(object value) => value as bool? ?? throw new FormatException("must be true or false");

    private static long PositiveInteger(object value) => value is long number && number > 0
        ? number
        : throw new FormatException("must be a positive integer");

    private static List<string> LogLevelList(object value)
    {
        if (value is not IEnumerable<object> items || value is string)
        {
            throw new FormatException("must be a list of log levels");
        }

        var levels = new List<string>();
        foreach (object item in items)
        {
            if (item is not string text)
            {
                throw new FormatException($"invalid log level: {item}");
            }

            string level = text.ToUpperInvariant();
            if (!s_validLevels.Contains(level))
            {
                throw new FormatException($"invalid log level: {text}. Valid: {string.Join(", ", s_validLevels)}");
            }

            levels.Add(level);
        }

        return levels;
    }

    private static List<string> PatternList(object value)
    {
        if (value is not IEnumerable<object> items || value is string)
        {
            throw new FormatException("must be a list of regex patterns");
        }

        var patterns = new List<string>();
        foreach (object item in items)
        {
            if (item is not string text)
            {
                throw new FormatException($"invalid pattern: {item}");
            }

            (string? pattern, bool _) = NotificationPattern(text);
            if (!LogPattern.TryCompile(pattern, caseSensitive: true, out _, out string? error))
            {
                throw new FormatException($"invalid regex pattern '{text}': {error}");
            }

            patterns.Add(text);
        }

        return patterns;
    }

    /// <summary>
    /// Reads a notification pattern written as <c>/pattern/</c>, <c>/pattern/i</c>, or a bare pattern.
    /// </summary>
    /// <param name="text">The pattern as written.</param>
    /// <returns>The regular expression and whether it matches case.</returns>
    public static (string Pattern, bool CaseSensitive) NotificationPattern(string text)
    {
        ArgumentNullException.ThrowIfNull(text);
        if (!text.StartsWith('/'))
        {
            return (text, true);
        }

        if (text.Length >= 3 && text.EndsWith("/i", StringComparison.Ordinal))
        {
            return (text[1..^2], false);
        }

        return text.Length >= 2 && text.EndsWith('/') ? (text[1..^1], true) : (text, true);
    }

    private static string ThemeName(object value)
    {
        if (value is string name && (BuiltInThemes.All.ContainsKey(name) || ThemeNamePattern().IsMatch(name)))
        {
            return name;
        }

        throw new FormatException(
            $"must be a valid theme name. Built-in: {string.Join(", ", BuiltInThemes.All.Keys.Order(StringComparer.Ordinal))}");
    }

    private static string QuietHours(object value)
    {
        if (value is not string text)
        {
            throw new FormatException("must be a time range like '22:00-08:00'");
        }

        return QuietHoursPattern().IsMatch(text) ? text : throw new FormatException("must be in format 'HH:MM-HH:MM'");
    }

    private static string Iso8601(object value)
    {
        if (value is not string text)
        {
            throw new FormatException("must be an ISO 8601 datetime string");
        }

        return text.Length == 0 || IsoDateTime.TryParse(text, out _) ? text : throw new FormatException("invalid ISO 8601 datetime");
    }

    [GeneratedRegex("^[A-Za-z0-9_-]+$")]
    private static partial Regex ThemeNamePattern();

    [GeneratedRegex("^[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2}$")]
    private static partial Regex QuietHoursPattern();
}
