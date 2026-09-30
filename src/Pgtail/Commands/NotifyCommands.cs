using System.Globalization;
using Pgtail.Notifications;
using Pgtail.Parsing;
using Pgtail.Sessions;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// The <c>notify</c> command: desktop notification rules, quiet hours, and a test notification.
/// </summary>
internal static class NotifyCommands
{
    private const string OnUsage = "Usage: notify on <levels> | /<pattern>/ | errors > N/min | slow > Nms";

    /// <summary>
    /// Runs the command, in the REPL or in tail mode.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the command has finished.</returns>
    public static async Task Run(CommandInvocation invocation)
    {
        IReadOnlyList<string> args = invocation.Args;
        PgtailSession session = invocation.Session;
        CommandOutput output = invocation.Output;
        if (args.Count == 0)
        {
            Status(session, output);
            return;
        }

        switch (args[0].ToLowerInvariant())
        {
            case "on":
                On(session, [.. args.Skip(1)], invocation.RawFrom(1), output);
                break;
            case "off":
                session.Notifications.Config.Enabled = false;
                Persist(session, output);
                output.Line("Notifications disabled");
                break;
            case "test":
                await TestAsync(session, [.. args.Skip(1)], output);
                break;
            case "clear":
                session.Notifications.Config.Clear();
                Persist(session, output);
                output.Line("Notification rules cleared");
                break;
            case "quiet":
                Quiet(session, [.. args.Skip(1)], output);
                break;
            default:
                output.Line("Usage: notify [on|off|test|clear|quiet]", StyleParser.Parse("ansiyellow"));
                break;
        }
    }

    private static void Status(PgtailSession session, CommandOutput output)
    {
        INotifier notifier = session.Notifications.Notifier;
        NotificationConfig config = session.Notifications.Config;
        if (!notifier.IsAvailable)
        {
            output.Line("Notifications: unavailable");
            output.Line($"Platform: {notifier.PlatformInfo}");
            InstallHint(notifier.PlatformInfo, output);
            return;
        }

        output.Line($"Notifications: {(config.Enabled ? "enabled" : "disabled")}");
        if (config.Enabled)
        {
            if (config.LevelRules() is { Count: > 0 } levels)
            {
                output.Line($"  Levels: {string.Join(", ", levels.Order().Select(level => level.ToName()))}");
            }

            if (config.PatternRules() is { Count: > 0 } patterns)
            {
                output.Line($"  Patterns: {string.Join(", ", patterns.Select(rule => rule.FormatPattern()))}");
            }

            if (config.ErrorRateThreshold() is { } rate)
            {
                output.Line($"  Error rate: > {rate}/min");
            }

            if (config.SlowQueryThreshold() is { } slow)
            {
                output.Line($"  Slow queries: > {slow}ms");
            }

            if (config.QuietHours is { } quiet)
            {
                output.Line($"  Quiet hours: {quiet}{(quiet.IsActive(DateTime.Now) ? " (active)" : "")}");
            }
        }

        output.Line($"Platform: {notifier.PlatformInfo}");
        if (!config.Enabled)
        {
            output.Line("Hint: Use 'notify on FATAL PANIC' to enable");
        }
    }

    private static void InstallHint(string platform, CommandOutput output)
    {
        if (platform.Contains("notify-send not found", StringComparison.Ordinal))
        {
            output.Line("Hint: Install libnotify-bin package");
        }
    }

    // A pattern is the rest of the line as typed, so it can hold spaces; quoted, it is the one word.
    private static void On(PgtailSession session, IReadOnlyList<string> args, string raw, CommandOutput output)
    {
        if (args.Count == 0)
        {
            output.Line(OnUsage);
            return;
        }

        NotificationConfig config = session.Notifications.Config;
        string first = args[0];
        if (first.StartsWith('/'))
        {
            string text = raw.StartsWith('/') ? raw : first;
            (string? pattern, bool caseSensitive) = text.EndsWith("/i", StringComparison.Ordinal) && text.Length >= 3
                ? (text[1..^2], false)
                : text.EndsWith('/') && text.Length >= 2 ? (text[1..^1], true) : (null, true);
            if (pattern is null)
            {
                output.Line($"Invalid pattern format: {text}");
                output.Line("Use: /pattern/ or /pattern/i");
                return;
            }

            if (pattern.Length == 0)
            {
                output.Line("Pattern cannot be empty");
                return;
            }

            try
            {
                config.Add(NotificationRule.ForPattern(pattern, caseSensitive));
            }
            catch (FormatException exception)
            {
                output.Line($"Invalid regex pattern: {exception.Message}");
                return;
            }

            Enable(session, output);
            output.Line($"Notifications enabled for pattern: {pattern}{(caseSensitive ? "" : " (case-insensitive)")}");
            return;
        }

        if (first.Equals("errors", StringComparison.OrdinalIgnoreCase))
        {
            if (args.Count < 3 || args[1] != ">" || !args[2].EndsWith("/min", StringComparison.Ordinal))
            {
                output.Line("Usage: notify on errors > N/min");
                return;
            }

            if (!int.TryParse(args[2][..^4], NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out int threshold))
            {
                output.Line($"Invalid threshold: {args[2][..^4]}");
                return;
            }

            if (threshold < 1)
            {
                output.Line("Threshold must be at least 1");
                return;
            }

            config.Add(NotificationRule.ForErrorRate(threshold));
            Enable(session, output);
            output.Line($"Notifications enabled: more than {threshold} errors per minute");
            return;
        }

        if (first.Equals("slow", StringComparison.OrdinalIgnoreCase))
        {
            if (args.Count < 3 || args[1] != ">")
            {
                output.Line("Usage: notify on slow > Nms");
                return;
            }

            string text = args[2].ToLowerInvariant();
            (string? digits, int scale) = text.EndsWith("ms", StringComparison.Ordinal) ? (text[..^2], 1)
                : text.EndsWith('s') ? (text[..^1], 1000) : (null, 0);
            if (digits is null)
            {
                output.Line("Invalid duration: use Nms or Ns format");
                return;
            }

            if (!int.TryParse(digits, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out int value))
            {
                output.Line($"Invalid duration: {args[2]}");
                return;
            }

            int milliseconds = value * scale;
            if (milliseconds < 1)
            {
                output.Line("Threshold must be at least 1ms");
                return;
            }

            config.Add(NotificationRule.ForSlowQuery(milliseconds));
            Enable(session, output);
            output.Line($"Notifications enabled: queries slower than {milliseconds}ms");
            return;
        }

        (HashSet<LogLevel>? levels, List<string>? invalid) = LogLevels.ParseArguments(FilterCommands.SplitCommas(args));
        if (invalid.Count > 0)
        {
            foreach (string name in invalid)
            {
                output.Line($"Unknown log level: {name}");
            }

            output.Line($"Valid levels: {string.Join(", ", LogLevels.Names)}");
            return;
        }

        if (levels is null)
        {
            output.Line(OnUsage);
            return;
        }

        config.Add(NotificationRule.ForLevels(levels));
        Enable(session, output);
        output.Line($"Notifications enabled for: {string.Join(", ", levels.Order().Select(level => level.ToName()))}");
    }

    private static void Enable(PgtailSession session, CommandOutput output)
    {
        session.Notifications.Config.Enabled = true;
        Persist(session, output);
    }

    private static async Task TestAsync(PgtailSession session, IReadOnlyList<string> args, CommandOutput output)
    {
        INotifier notifier = session.Notifications.Notifier;
        if (!notifier.IsAvailable)
        {
            output.Line("Test notification failed");
            output.Line($"Platform: {notifier.PlatformInfo}");
            InstallHint(notifier.PlatformInfo, output);
            return;
        }

        NotificationSeverity severity = NotificationSeverity.Info;
        if (args.Count > 0 && !NotificationSeverities.TryParse(args[0], out severity))
        {
            output.Line($"Unknown severity: {args[0]}");
            output.Line($"Valid severities: {string.Join(", ", NotificationSeverities.Names)}");
            return;
        }

        bool sent = await Task.Run(() => session.Notifications.SendTest(severity));
        output.Line(sent ? $"Test notification sent ({severity.ToName().ToUpperInvariant()})" : "Test notification failed");
        output.Line($"Platform: {notifier.PlatformInfo}");
    }

    private static void Quiet(PgtailSession session, IReadOnlyList<string> args, CommandOutput output)
    {
        NotificationConfig config = session.Notifications.Config;
        if (args.Count == 0)
        {
            output.Line("Usage: notify quiet HH:MM-HH:MM | off");
            return;
        }

        if (args[0].Equals("off", StringComparison.OrdinalIgnoreCase))
        {
            config.QuietHours = null;
            Persist(session, output);
            output.Line("Quiet hours disabled");
            return;
        }

        try
        {
            config.QuietHours = QuietHours.Parse(args[0]);
        }
        catch (FormatException exception)
        {
            output.Line(exception.Message);
            return;
        }

        Persist(session, output);
        output.Line($"Notifications silenced {config.QuietHours}");
    }

    private static void Persist(PgtailSession session, CommandOutput output)
    {
        NotificationConfig config = session.Notifications.Config;
        var values = new List<(string Key, object? Value)>
        {
            ("notifications.enabled", config.Enabled),
            ("notifications.levels", config.LevelRules().Order().Select(level => level.ToName()).ToList()),
            ("notifications.patterns", config.PatternRules().Select(rule => rule.FormatPattern()!).ToList()),
            ("notifications.error_rate", config.ErrorRateThreshold()),
            ("notifications.slow_query_ms", config.SlowQueryThreshold()),
            ("notifications.quiet_hours", config.QuietHours?.ToString()),
        };

        foreach ((string key, object? value) in values)
        {
            if (value is null)
            {
                _ = session.Store.Delete(key);
            }
            else if (session.Store.Save(key, value) is { } error)
            {
                output.Line($"Warning: {error}");
                return;
            }

            session.Config[key] = value;
        }
    }
}
