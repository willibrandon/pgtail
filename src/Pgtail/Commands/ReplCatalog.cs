using Pgtail.Display;
using Pgtail.Filtering;
using Pgtail.Parsing;

namespace Pgtail.Commands;

/// <summary>
/// The commands the REPL accepts, with their completions and handlers.
/// </summary>
internal static class ReplCatalog
{
    private static readonly ArgumentSpec s_since = ArgumentSpec.Of(
        ("clear", "Remove time filter"), ("5m", "Last 5 minutes"), ("30m", "Last 30 minutes"), ("1h", "Last hour"),
        ("2h", "Last 2 hours"), ("1d", "Last day"));

    private static readonly ArgumentSpec s_formats = ArgumentSpec.Of(
        ("text", "Raw log lines"), ("json", "JSON Lines format"), ("csv", "CSV with headers"));

    private static readonly ArgumentSpec s_paths = ArgumentSpec.From(CompletionSources.Paths);

    private static readonly ArgumentSpec s_instances = ArgumentSpec.From(CompletionSources.Instances);

    /// <summary>
    /// The catalog.
    /// </summary>
    public static CommandCatalog Catalog { get; } = new(
    [
        new("list", "Show detected PostgreSQL instances", ArgumentSpec.None, CoreCommands.List) { Aliases = ["ls"] },
        new("tail", "Tail logs for an instance (by ID or path)", new ArgumentSpec
        {
            Flags =
            [
                new("--file", "Tail arbitrary log file (e.g., ./test.log)", s_paths) { Repeatable = true },
                new("-f", "Short for --file", s_paths) { Repeatable = true },
                new("--since", "Filter from time (e.g., 5m, 14:30)", s_since),
                new("--stream", "Stream entries to the terminal"),
            ],
            Positionals = [s_instances],
        }, TailCommand.Run),
        new("levels", "Set log level filter (e.g., 'levels ERROR WARNING')",
            new ArgumentSpec
            {
                Rest = ArgumentSpec.From(CompletionSources.Levels),
                Positionals = [ArgumentSpec.From(CompletionSources.Levels)],
            },
            FilterCommands.Levels) { Aliases = ["level"] },
        new("filter", "Set regex filter (e.g., 'filter /pattern/')", ArgumentSpec.Positional(new ArgumentSpec
        {
            Values = [new("clear", "Clear all filters")],
            Source = context => context.Partial.Contains('=', StringComparison.Ordinal)
                ? []
                : FieldNames.Aliases.Keys.Order(StringComparer.Ordinal)
                    .Select(field => new CompletionItem(field + "=", $"Filter by {field}", Continues: true)),
        }), FilterCommands.Filter),
        new("highlight", "Highlight text matching regex (e.g., 'highlight /pattern/')", HighlightSpec(), HighlightCommands.Repl),
        new("since", "Filter logs since time (e.g., 'since 5m', 'since 14:30')", ArgumentSpec.Positional(s_since), TimeCommands.Since),
        new("until", "Filter logs until time (e.g., 'until 15:00', 'until 30m')", ArgumentSpec.Positional(ArgumentSpec.Of(
            ("clear", "Remove time filter"), ("15:00", "3 PM today"), ("15:30", "3:30 PM today"), ("16:00", "4 PM today"),
            ("17:00", "5 PM today"))), TimeCommands.Until),
        new("between", "Filter logs in time range (e.g., 'between 14:30 15:00')", new ArgumentSpec
        {
            Positionals =
            [
                ArgumentSpec.Of(("5m", "5 minutes ago (start)"), ("30m", "30 minutes ago (start)"), ("1h", "1 hour ago (start)"),
                    ("14:00", "2 PM today (start)"), ("14:30", "2:30 PM today (start)")),
                ArgumentSpec.Of(("15:00", "3 PM today (end)"), ("15:30", "3:30 PM today (end)"), ("16:00", "4 PM today (end)")),
            ],
        }, TimeCommands.Between),
        new("display", "Control display mode (compact, full, fields)", DisplaySpec(), CoreCommands.Display),
        new("output", "Control output format (json, text)", ArgumentSpec.Positional(ArgumentSpec.Of(
            ("json", "Output as JSON (one object per line)"),
            ("text", "Output as colored text (default)"))), CoreCommands.Output),
        new("slow", "Configure slow query highlighting (e.g., 'slow 100 500 1000')",
            ArgumentSpec.Positional(ArgumentSpec.Of(("off", "Disable slow query highlighting"))), SlowCommands.Slow),
        new("stats", "Show query duration statistics", ArgumentSpec.None, SlowCommands.Stats),
        new("set", "Set a config value (e.g., 'set slow.warn 50')", new ArgumentSpec
        {
            Positionals = [ArgumentSpec.From(CompletionSources.SettingKeys(section => $"{section} setting")), null],
        }, ConfigCommands.Set),
        new("unset", "Remove a config setting (e.g., 'unset slow.warn')",
            ArgumentSpec.Positional(ArgumentSpec.From(CompletionSources.SettingKeys(section => $"reset {section} setting to default"))),
            ConfigCommands.Unset),
        new("config", "Show current configuration (subcommands: path, edit, reset)", new ArgumentSpec
        {
            Subcommands =
            [
                new("path", "Show config file location", ArgumentSpec.None),
                new("edit", "Open config in the built-in editor", ArgumentSpec.None),
                new("reset", "Reset config to defaults (with backup)", ArgumentSpec.None),
            ],
        }, ConfigCommands.Config),
        new("errors", "Show error statistics (--trend, --live, --code, --since, clear)", new ArgumentSpec
        {
            Flags =
            [
                new("--trend", "Show error rate sparkline") { Excludes = ["--live"] },
                new("--live", "Live updating counter") { Excludes = ["--trend"] },
                new("--code", "Filter by SQLSTATE code", ArgumentSpec.Of(
                    ("23505", "unique_violation"), ("23503", "foreign_key_violation"), ("42P01", "undefined_table"),
                    ("42601", "syntax_error"), ("42703", "undefined_column"), ("57014", "query_canceled"),
                    ("53300", "too_many_connections"))),
                new("--since", "Filter by time window", s_since),
            ],
            Rest = ArgumentSpec.Of(("clear", "Reset all error statistics")),
        }, ErrorsCommands.Repl),
        new("connections", "Show connection statistics (--history, --watch, --db=, --user=, --app=, clear)", new ArgumentSpec
        {
            Flags =
            [
                new("--history", "Show connection trends over time") { Excludes = ["--watch"] },
                new("--watch", "Live stream of connection events") { Excludes = ["--history"] },
                new("--db=", "Filter by database name", ArgumentSpec.FreeForm),
                new("--user=", "Filter by user name", ArgumentSpec.FreeForm),
                new("--app=", "Filter by application name", ArgumentSpec.FreeForm),
            ],
            Rest = ArgumentSpec.Of(("clear", "Reset connection statistics")),
        }, ConnectionsCommands.Repl),
        new("notify", "Configure desktop notifications (on, off, test, quiet, clear)", NotifySpec(), NotifyCommands.Run),
        new("theme", "Switch color theme (e.g., 'theme light', 'theme monokai')", ThemeSpec(), ThemeCommands.Repl),
        new("export", "Export filtered logs to file (e.g., 'export errors.log')", new ArgumentSpec
        {
            Flags =
            [
                new("--append", "Append to existing file"),
                new("--follow", "Continuous export (like tail -f | tee)"),
                new("--format", "Output format (text, json, csv)", s_formats),
                new("--since", "Only entries after time (1h, 30m, 2d)", s_since),
                new("--highlighted", "Keep colors (ANSI escapes) in text output"),
            ],
            Positionals = [s_paths],
        }, ExportCommands.Export),
        new("pipe", "Pipe filtered logs to command (e.g., 'pipe wc -l')", new ArgumentSpec
        {
            Flags = [new("--format", "Output format (text, json, csv)", s_formats)],
        }, ExportCommands.Pipe),
        new("stop", "Stop current tail and return to prompt", ArgumentSpec.None, CoreCommands.Stop),
        new("refresh", "Re-scan for PostgreSQL instances", ArgumentSpec.None, CoreCommands.Refresh),
        new("enable-logging", "Enable logging_collector for an instance", ArgumentSpec.Positional(s_instances),
            ConfigCommands.EnableLogging),
        new("clear", "Clear the screen", ArgumentSpec.None, CoreCommands.Clear),
        new("help", "Show help message", ArgumentSpec.None, CoreCommands.Help),
        new("quit", "Exit pgtail", ArgumentSpec.None, CoreCommands.Quit) { Aliases = ["exit", "q"] },
    ]);

    private static ArgumentSpec HighlightSpec()
    {
        var names = ArgumentSpec.From(context => CompletionSources.Highlighters(
            name => $"{(context.Arguments is [var sub, ..] && sub == "disable" ? "Disable" : "Enable")} {name} highlighter")(context));
        return new ArgumentSpec
        {
            Subcommands =
            [
                new("list", "Show all highlighters with status", ArgumentSpec.None),
                new("on", "Enable all highlighting globally", ArgumentSpec.None),
                new("off", "Disable all highlighting globally", ArgumentSpec.None),
                new("enable", "Enable a specific highlighter", ArgumentSpec.Positional(ArgumentSpec.From(
                    CompletionSources.Highlighters(name => $"Enable {name} highlighter")))),
                new("disable", "Disable a specific highlighter", ArgumentSpec.Positional(ArgumentSpec.From(
                    CompletionSources.Highlighters(name => $"Disable {name} highlighter")))),
                new("add", "Add custom highlighter (name pattern [--style])", new ArgumentSpec
                {
                    Positionals = [null, null],
                    Flags = [new("--style", "Rich style, such as 'bold red'"), new("--priority", "Lower runs first (default 1050)")],
                }),
                new("remove", "Remove custom highlighter",
                    ArgumentSpec.Positional(ArgumentSpec.From(CompletionSources.CustomHighlighters))),
                new("export", "Export highlighting config as TOML", new ArgumentSpec
                {
                    Flags = [new("--file", "Export to file path", s_paths)],
                }),
                new("import", "Import highlighting config from TOML file", ArgumentSpec.Positional(s_paths)),
                new("preview", "Preview highlighting with sample log lines", ArgumentSpec.None),
                new("reset", "Reset all highlighting settings to defaults", ArgumentSpec.None),
                new("clear", "Clear all regex highlight patterns (legacy)", ArgumentSpec.None),
            ],
            Positionals = [names],
        };
    }

    private static ArgumentSpec NotifySpec()
    {
        var levels = ArgumentSpec.From(context =>
        {
            string partial = context.Partial.ToLowerInvariant();
            var items = new List<CompletionItem>();
            if (partial.StartsWith("error", StringComparison.Ordinal))
            {
                items.Add(new CompletionItem("errors", "Rate threshold (errors > N/min)"));
            }

            if (partial.StartsWith("slow", StringComparison.Ordinal))
            {
                items.Add(new CompletionItem("slow", "Duration threshold (slow > Nms)"));
            }

            if (partial.Length == 0 || partial.StartsWith('/'))
            {
                items.Add(new CompletionItem("/deadlock/", "Match 'deadlock' in messages"));
                items.Add(new CompletionItem("/timeout/i", "Match 'timeout' case-insensitive"));
                items.Add(new CompletionItem("/error.*connection/", "Match error with connection"));
            }

            var chosen = context.Arguments.Where(argument => !argument.StartsWith('/'))
                .Select(argument => argument.ToUpperInvariant()).ToHashSet(StringComparer.Ordinal);
            items.AddRange(LogLevels.All.Where(level => !chosen.Contains(level.ToName()))
                .Select(level => new CompletionItem(level.ToName(), $"Severity {(int)level}")));
            return items;
        });

        return new ArgumentSpec
        {
            Subcommands =
            [
                new("on", "Enable notifications (levels, patterns, thresholds)",
                    new ArgumentSpec { Rest = levels, Positionals = [levels] }),
                new("off", "Disable all notifications", ArgumentSpec.None),
                new("test", "Send a test notification", ArgumentSpec.Positional(ArgumentSpec.Of(
                    ("info", "Default toast (short, single chime)"), ("warning", "Warning toast (short, single chime)"),
                    ("error", "Error toast (long duration, high priority)"), ("critical", "Critical toast (alarm, looping sound)")))),
                new("quiet", "Set quiet hours (HH:MM-HH:MM)", ArgumentSpec.Positional(ArgumentSpec.Of(("off", "Disable quiet hours")))),
                new("clear", "Remove all notification rules", ArgumentSpec.None),
            ],
        };
    }

    private static ArgumentSpec ThemeSpec()
    {
        var themes = ArgumentSpec.From(CompletionSources.Themes);
        return new ArgumentSpec
        {
            Subcommands =
            [
                new("list", "Show all available themes", ArgumentSpec.None),
                new("preview", "Preview a theme without switching", ArgumentSpec.Positional(themes)),
                new("edit", "Create or edit a custom theme", ArgumentSpec.Positional(themes)),
                new("reload", "Reload current theme from disk", ArgumentSpec.None),
            ],
            Positionals = [themes],
        };
    }

    private static ArgumentSpec DisplaySpec()
    {
        var fields = ArgumentSpec.From(DisplayFieldCompletions);
        return new ArgumentSpec
        {
            Subcommands =
            [
                new("compact", "Single line per entry (default)", ArgumentSpec.None),
                new("full", "All available fields with labels", ArgumentSpec.None),
                new("fields", "Show only specified fields", ArgumentSpec.Positional(fields)),
            ],
        };
    }

    private static IEnumerable<CompletionItem> DisplayFieldCompletions(CompletionContext context)
    {
        string partial = context.Partial;
        int comma = partial.LastIndexOf(',');
        string prefix = comma >= 0 ? partial[..(comma + 1)] : "";
        var chosen = prefix.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(field => field.ToLowerInvariant()).ToHashSet(StringComparer.Ordinal);
        foreach (string? field in DisplayFields.Valid.Order(StringComparer.Ordinal))
        {
            if (!chosen.Contains(field))
            {
                yield return new CompletionItem(prefix + field, comma >= 0 ? $"Add {field} field" : $"Show {field} field")
                {
                    Display = field,
                };
            }
        }
    }
}
