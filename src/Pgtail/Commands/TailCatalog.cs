using Pgtail.Statistics;
using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// The commands tail mode accepts, with their completions, detailed help, and handlers.
/// </summary>
internal static class TailCatalog
{
    private static readonly ArgumentSpec Levels = ArgumentSpec.Of(
        ("debug", "Debug messages"), ("error", "Errors"), ("fatal", "Fatal errors"), ("info", "Informational"), ("log", "Log messages"),
        ("notice", "Notices"), ("panic", "Panics"), ("warning", "Warnings"));

    private static readonly ArgumentSpec TimePresets = ArgumentSpec.Of(
        ("10m", "Last 10 minutes"), ("15m", "Last 15 minutes"), ("1d", "Last day"), ("1h", "Last hour"), ("2h", "Last 2 hours"),
        ("30m", "Last 30 minutes"), ("4h", "Last 4 hours"), ("5m", "Last 5 minutes"), ("clear", "Remove time filter"));

    private static readonly ArgumentSpec Formats =
        ArgumentSpec.Of(("csv", "CSV with headers"), ("json", "JSON Lines"), ("text", "Raw log lines"));

    private static readonly ArgumentSpec HighlighterNames = ArgumentSpec.From(context =>
        CompletionSources.Highlighters(name => $"{name} highlighter")(context).Concat(context.Session.Highlighting.CustomHighlighters
            .Select(custom => new CompletionItem(custom.Name, "custom highlighter"))));

    /// <summary>
    /// The catalog.
    /// </summary>
    public static CommandCatalog Catalog { get; } = new(
    [
        new("level", "Filter by level", ArgumentSpec.Positional(Levels), FilterCommands.TailLevel)
        {
            Aliases = ["levels"],
            Help = new("level <level>[+|-] [level2...]", "Filter log entries by severity level",
                "Show only entries matching the specified log level(s).",
                [
                    "level error        Show only ERROR entries",
                    "level error+       Show ERROR and more severe (FATAL, PANIC)",
                    "level warning-     Show WARNING and less severe (NOTICE, LOG, etc.)",
                    "level error,warn   Show ERROR and WARNING only",
                    "level e+           Same as 'level error+' (abbreviation)",
                    "level all          Show all levels (clear level filter)",
                ])
            {
                Aliases = "e=error, w=warning, f=fatal, p=panic, n=notice, i=info, l=log, d=debug",
            },
        },
        new("filter", "Filter by regex pattern", ArgumentSpec.Positional(null), FilterCommands.TailFilter)
        {
            Help = new("filter /pattern/[c]", "Filter log entries by regex pattern",
                "Show only entries matching the regular expression pattern.",
                [
                    "filter /error/      Match 'error', ignoring case",
                    "filter /error/c     Match 'error' case-sensitively",
                    "filter -/noise/     Hide lines matching 'noise'",
                    "filter &/users/     Also require 'users'",
                    "filter /user_\\d+/   Match 'user_' followed by digits",
                    "filter app=myapp    Filter by field (CSV/JSON logs)",
                    "filter clear        Remove regex filter",
                ]),
        },
        new("since", "Show entries since a time", ArgumentSpec.Positional(TimePresets), TimeCommands.TailSince)
        {
            Help = new("since <time>", "Show entries from a specific time onward",
                "Filter to show only log entries from the specified time.",
                [
                    "since 5m           Entries from last 5 minutes",
                    "since 2h           Entries from last 2 hours",
                    "since 14:30        Entries since 2:30 PM today",
                    "since 14:30:00     Entries since 2:30:00 PM today",
                    "since clear        Remove time filter",
                ]),
        },
        new("until", "Show entries until a time", ArgumentSpec.Positional(TimePresets), TimeCommands.TailUntil)
        {
            Help = new("until <time>", "Show entries up to a specific time",
                "Filter to show only log entries up to the specified time.",
                [
                    "until 5m           Entries up to 5 minutes ago",
                    "until 14:30        Entries until 2:30 PM today",
                    "until clear        Remove time filter",
                ]),
        },
        new("between", "Show entries in a time range", new ArgumentSpec { Positionals = [TimePresets, TimePresets] },
            TimeCommands.TailBetween)
        {
            Help = new("between <start> <end>", "Show entries in a time range",
                "Filter to show only log entries between start and end times.",
                [
                    "between 14:00 15:00    Entries between 2 PM and 3 PM",
                    "between 1h 30m         Entries from 1 hour ago to 30 min ago",
                ]),
        },
        new("slow", "Set slow query threshold", ArgumentSpec.Positional(ArgumentSpec.Of(
            ("100", "100 ms"), ("1000", "1 second"), ("200", "200 ms"), ("50", "50 ms"), ("500", "500 ms"))), SlowCommands.TailSlow)
        {
            Help = new("slow <milliseconds>", "Highlight slow queries above threshold",
                "Set a threshold to highlight queries exceeding the duration.",
                [
                    "slow 100           Highlight queries over 100ms",
                    "slow 1000          Highlight queries over 1 second",
                    "slow clear         Remove slow query threshold",
                ]),
        },
        new("clear", "Reset filters to the initial state", ArgumentSpec.Positional(ArgumentSpec.Of(("force", "Clear all filters"))),
            TailModeCommands.Clear)
        {
            Help = new("clear [force]", "Reset filters to initial state",
                "Clear all filters and return to the state when tail mode started.",
                [
                    "clear              Reset to initial filters",
                    "clear force        Clear ALL filters (ignore initial state)",
                ]),
        },
        new("errors", "Show error statistics", new ArgumentSpec
        {
            Positionals = [ArgumentSpec.Of(("clear", "Reset all error statistics"))],
            Flags =
            [
                new("--code", "Filter by SQLSTATE code", ArgumentSpec.From(_ =>
                    SqlStates.Names.Keys.Order(StringComparer.Ordinal).Select(code => new CompletionItem(code, SqlStates.Names[code])))),
                new("--live", "Live updating counter"),
                new("--since", "Filter by time window", TimePresets),
                new("--trend", "Show error rate sparkline"),
            ],
        }, ErrorsCommands.Tail)
        {
            Help = new("errors [--trend|--code CODE|--since TIME]", "Show error statistics",
                "Display error/warning counts, trends, and SQLSTATE codes.",
                [
                    "errors             Summary with counts by SQLSTATE",
                    "errors --trend     Sparkline of error rate (last 60 min)",
                    "errors --code 23505  Filter by SQLSTATE code",
                    "errors --since 30m   Time-scoped statistics",
                    "errors clear       Reset all statistics",
                ]),
        },
        new("connections", "Show connection statistics", new ArgumentSpec
        {
            Positionals = [ArgumentSpec.Of(("clear", "Reset connection statistics"))],
            Flags =
            [
                new("--app=", "Filter by application name", ArgumentSpec.FreeForm),
                new("--db=", "Filter by database name", ArgumentSpec.FreeForm),
                new("--history", "Show connection trends over time"),
                new("--user=", "Filter by user name", ArgumentSpec.FreeForm),
                new("--watch", "Live stream of connection events"),
            ],
        }, ConnectionsCommands.Tail)
        {
            Help = new("connections [--history|--db=X|--user=X]", "Show connection statistics",
                "Display connection/disconnection counts and active sessions.",
                [
                    "connections            Summary with breakdowns",
                    "connections --history  Connect/disconnect rate history",
                    "connections --db=mydb  Filter by database name",
                    "connections clear      Reset statistics",
                ]),
        },
        new("highlight", "Manage semantic highlighters", new ArgumentSpec
        {
            Subcommands =
            [
                new("add", "Add custom highlighter (name pattern [--style])", new ArgumentSpec { Positionals = [null, null] }),
                new("disable", "Disable a specific highlighter", ArgumentSpec.Positional(HighlighterNames)),
                new("enable", "Enable a specific highlighter", ArgumentSpec.Positional(HighlighterNames)),
                new("export", "Export highlighting config as TOML", new ArgumentSpec
                {
                    Flags = [new("--file", "Export to file path", ArgumentSpec.From(CompletionSources.Paths))],
                }),
                new("import", "Import highlighting config from TOML file",
                    ArgumentSpec.Positional(ArgumentSpec.From(CompletionSources.Paths))),
                new("list", "Show all highlighters with status", ArgumentSpec.None),
                new("off", "Disable all highlighting globally", ArgumentSpec.None),
                new("on", "Enable all highlighting globally", ArgumentSpec.None),
                new("preview", "Preview highlighting with sample log lines", ArgumentSpec.None),
                new("remove", "Remove custom highlighter", ArgumentSpec.Positional(HighlighterNames)),
                new("reset", "Reset all highlighting settings to defaults", ArgumentSpec.None),
            ],
        }, HighlightCommands.Tail)
        {
            Help = new("highlight [list|on|off|enable|disable|add|remove|export|import|preview|reset]", "Manage semantic highlighters",
                "Enable, disable, or add custom semantic highlighters for log output.",
                [
                    "highlight              Show all highlighters with status",
                    "highlight list         Same as above",
                    "highlight on           Enable all highlighting globally",
                    "highlight off          Disable all highlighting globally",
                    "highlight enable timestamp   Enable timestamp highlighting",
                    "highlight disable duration   Disable duration highlighting",
                    "highlight add req_id 'REQ-\\d+' --style yellow --priority 500  Add custom",
                    "highlight remove req_id    Remove custom highlighter",
                    "highlight export --file /tmp/hl.toml   Export config to file",
                    "highlight export       Print config as TOML",
                    "highlight import /tmp/hl.toml   Import config from file",
                    "highlight preview      Preview highlighting with sample log lines",
                    "highlight reset        Reset all settings to defaults",
                ]),
        },
        new("set", "Configure settings", new ArgumentSpec
        {
            Positionals = [ArgumentSpec.From(CompletionSources.SettingKeys(section => $"{section} setting")), null],
        }, ConfigCommands.TailSet)
        {
            Help = new("set <key> [value]", "Configure settings",
                "View or change configuration settings. Changes are persisted immediately.",
                [
                    "set highlighting.duration.slow        Show current value",
                    "set highlighting.duration.slow 50     Set slow threshold to 50ms",
                    "set highlighting.duration.very_slow 200  Set very_slow to 200ms",
                    "set highlighting.duration.critical 1000  Set critical to 1000ms",
                ])
            {
                SeeAlso = "highlight",
            },
        },
        new("export", "Export displayed entries to a file", new ArgumentSpec
        {
            Positionals = [ArgumentSpec.From(CompletionSources.Paths)],
            Flags = [new("--format", "Output format", Formats), new("--highlighted", "Keep colors (ANSI escapes) in text output")],
        }, ExportCommands.TailExport)
        {
            Help = new("export <path> [--format text|json|csv] [--highlighted]", "Export displayed entries to a file",
                "Export log entries currently displayed (matching filters) to a file.",
                [
                    "export /tmp/logs.txt            Export as plain text (default)",
                    "export /tmp/logs.json --format json   Export as JSON Lines",
                    "export /tmp/logs.csv --format csv     Export as CSV",
                    "export /tmp/logs.txt --highlighted    Keep colors as ANSI escapes",
                ]),
        },
        new("theme", "Switch color theme", ArgumentSpec.Positional(ArgumentSpec.From(CompletionSources.Themes)), ThemeCommands.Tail),
        new("notify", "Configure desktop notifications", new ArgumentSpec
        {
            Subcommands =
            [
                new("clear", "Remove all notification rules", ArgumentSpec.None),
                new("off", "Disable all notifications", ArgumentSpec.None),
                new("on", "Enable notifications", new ArgumentSpec { Rest = Levels, Positionals = [Levels] }),
                new("quiet", "Set quiet hours (HH:MM-HH:MM)", ArgumentSpec.Positional(ArgumentSpec.Of(("off", "Disable quiet hours")))),
                new("test", "Send a test notification", ArgumentSpec.Positional(ArgumentSpec.Of(
                    ("info", "Default toast"), ("warning", "Warning toast"), ("error", "Error toast"), ("critical", "Critical toast")))),
            ],
        }, NotifyCommands.Run)
        {
            Help = new("notify [on|off|test|quiet|clear]", "Configure desktop notifications",
                "Set up desktop notifications for log events by level, pattern, or threshold.",
                [
                    "notify                 Show current notification settings",
                    "notify on FATAL PANIC  Enable for FATAL and PANIC levels",
                    "notify on ERROR+       Enable for ERROR and above",
                    "notify on /deadlock/   Enable for pattern match",
                    "notify on errors > 5/min  Alert on error rate spike",
                    "notify on slow > 500ms    Alert on slow queries",
                    "notify test            Send test notification (info)",
                    "notify test error      Send test notification (error severity)",
                    "notify test critical   Send test notification (critical severity)",
                    "notify quiet 22:00-07:00  Silence during quiet hours",
                    "notify quiet off       Disable quiet hours",
                    "notify off             Disable all notifications",
                    "notify clear           Remove all notification rules",
                ]),
        },
        new("help", "Show help", ArgumentSpec.Positional(ArgumentSpec.From(HelpTopics)), TailModeCommands.Help)
        {
            Help = new("help [command|keys]", "Show help information",
                "Display general help or detailed help for a specific command.",
                [
                    "help               Show all commands",
                    "help keys          Show keybinding reference",
                    "help level         Show level command help",
                    "help filter        Show filter command help",
                ]),
        },
        new("pause", "Pause log updates", ArgumentSpec.None, TailModeCommands.Pause)
        {
            Aliases = ["p"],
            Help = new("pause", "Pause log updates (freeze display)",
                "Stop auto-scrolling and freeze the display. New entries are buffered.", ["pause              Freeze display"])
            {
                SeeAlso = "follow, p key",
            },
        },
        new("follow", "Resume following new entries", ArgumentSpec.None, TailModeCommands.Follow)
        {
            Aliases = ["f"],
            Help = new("follow", "Resume following new entries",
                "Resume auto-scrolling and show any entries that arrived while paused.", ["follow             Resume following"])
            {
                SeeAlso = "pause, f key",
            },
        },
        new("stop", "Exit tail mode", ArgumentSpec.None, TailModeCommands.Stop) { Aliases = ["exit", "q"] },
    ]);

    private static IEnumerable<CompletionItem> HelpTopics(CompletionContext context) => Catalog.Commands
        .Where(command => command.Help is not null)
        .Select(command => new CompletionItem(command.Name, command.Help!.Short))
        .Append(new CompletionItem("keys", "Keybinding reference"))
        .OrderBy(item => item.Text, StringComparer.Ordinal);

    /// <summary>
    /// Runs a command line in tail mode.
    /// </summary>
    /// <remarks>
    /// <c>&lt;command&gt; help</c> and <c>&lt;command&gt; ?</c> show the command's detailed help.
    /// </remarks>
    /// <param name="line">The command line.</param>
    /// <param name="host">The tail view.</param>
    /// <returns>A task that completes when the command has run.</returns>
    public static async Task ExecuteAsync(string line, ITailHost host)
    {
        ArgumentNullException.ThrowIfNull(line);
        ArgumentNullException.ThrowIfNull(host);
        var tokens = CommandLineSplitter.Split(line);
        if (tokens.Count == 0)
        {
            return;
        }

        var name = tokens[0].Text;
        if (Catalog.Find(name) is not { } command)
        {
            host.Output.Markup($"[bold red]✗[/] Unknown command: {Markup.Escape(name)}. Type 'help' for commands.");
            return;
        }

        if (tokens.Count > 1 && tokens[1].Text.ToLowerInvariant() is "help" or "?" && command.Help is not null)
        {
            TailModeCommands.ShowCommandHelp(command, host.Output);
            return;
        }

        await command.Handler(new CommandInvocation(command, name, line, [.. tokens.Skip(1)], host));
    }
}
