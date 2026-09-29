using Pgtail.Display;

namespace Pgtail.Commands;

/// <summary>
/// The REPL's general commands: help, list, refresh, clear, quit, stop, display, and output.
/// </summary>
internal static class CoreCommands
{
    /// <summary>
    /// The text <c>help</c> prints.
    /// </summary>
    public static IReadOnlyList<string> HelpText { get; } =
    [
        "Available commands:",
        "  list              Show detected PostgreSQL instances",
        "  tail <id|path>    Tail logs for an instance (by ID or data directory path)",
        "                    --file <path>  Tail an arbitrary log file",
        "                    -f <path>      Short form of --file",
        "                    --since <time> Start with a time filter",
        "                    --stream       Stream entries to the terminal",
        "  levels [LEVEL...] Set log level filter (e.g., 'levels ERROR WARNING')",
        "                    With no args, shows current filter settings",
        "                    Use 'levels ALL' to show all levels",
        "  filter /pattern/  Filter logs by regex pattern",
        "                    -/pattern/  Exclude matching lines",
        "                    +/pattern/  Add OR pattern",
        "                    &/pattern/  Add AND pattern",
        "                    /pattern/c  Case-sensitive match",
        "                    field=value Filter by field (CSV/JSON only)",
        "                    clear       Clear all filters",
        "  highlight /pattern/  Highlight matching text (yellow background)",
        "                    /pattern/c  Case-sensitive highlight",
        "                    clear       Clear all highlights",
        "  since <time>      Filter logs since time (e.g., 'since 5m', 'since 14:30')",
        "                    clear       Remove time filter",
        "  until <time>      Filter logs until time (e.g., 'until 15:00')",
        "                    Disables live tailing (upper bound set)",
        "  between <s> <e>   Filter logs in time range (e.g., 'between 14:30 15:00')",
        "  display [mode]    Control display mode for log entries",
        "                    compact   Single line (default)",
        "                    full      All available fields with labels",
        "                    fields <f1,f2,...>  Show only specified fields",
        "  output [format]   Control output format",
        "                    json      Output as JSON (one object per line)",
        "                    text      Output as colored text (default)",
        "  slow [w s c]      Configure slow query highlighting (thresholds in ms)",
        "                    With no args, shows current settings",
        "                    'slow off' disables highlighting",
        "  stats             Show query duration statistics",
        "  errors            Show error statistics",
        "                    --trend     Show error rate sparkline",
        "                    --live      Live updating counter",
        "                    --code CODE Filter by SQLSTATE code",
        "                    --since TIME Filter by time window",
        "                    clear       Reset statistics",
        "  connections       Show connection statistics",
        "                    --history   Show connection trends over time",
        "                    --watch     Live stream of connection events",
        "                    --db=NAME   Filter by database name",
        "                    --user=NAME Filter by user name",
        "                    --app=NAME  Filter by application name",
        "                    clear       Reset statistics",
        "  notify            Configure desktop notifications",
        "                    on LEVEL... Enable for log levels (FATAL, PANIC, etc.)",
        "                    on /pattern/  Enable for regex pattern matches",
        "                    off         Disable all notifications",
        "                    test        Send a test notification",
        "                    quiet HH:MM-HH:MM  Set quiet hours",
        "                    quiet off   Disable quiet hours",
        "                    clear       Remove all notification rules",
        "  theme [name]      Switch color theme (e.g., 'theme light', 'theme monokai')",
        "                    list        Show all available themes",
        "                    preview <n> Preview a theme without switching",
        "                    edit <name> Create or edit a custom theme",
        "                    reload      Reload current theme from disk",
        "  set <key> [val]   Set/view a config value (e.g., 'set slow.warn 50')",
        "                    With no value, shows current setting",
        "  unset <key>       Remove a setting to revert to default",
        "  config            Show current configuration as TOML",
        "                    Subcommands: path, edit, reset",
        "  export <file>     Export filtered logs to file",
        "                    --format <fmt>  Output format (text, json, csv)",
        "                    --since <time>  Only entries after time (1h, 30m, 2d)",
        "                    --append        Append to existing file",
        "                    --follow        Continuous export (like tail -f | tee)",
        "                    --highlighted   Keep colors (ANSI) in text output",
        "  pipe <cmd>        Pipe filtered logs to external command",
        "                    --format <fmt>  Output format (text, json, csv)",
        "  stop              Stop current tail and return to prompt",
        "  refresh           Re-scan for PostgreSQL instances",
        "  enable-logging <id>  Enable logging_collector for an instance",
        "  clear             Clear the screen",
        "  help              Show this help message",
        "  quit / exit       Exit pgtail",
        "  !<command>        Run a shell command (e.g., '!ls -la')",
        "  !                 Enter shell mode (next input runs as shell command)",
        "",
        "Keyboard shortcuts:",
        "  Tab       Autocomplete commands and arguments",
        "  Up/Down   Navigate command history",
        "  Ctrl+C    Stop current tail",
        "  Ctrl+D    Exit pgtail",
    ];

    /// <summary>
    /// Prints the command reference.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Help(CommandInvocation invocation)
    {
        invocation.Output.Lines(HelpText);
        return Task.CompletedTask;
    }

    /// <summary>
    /// Prints the detected instances.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task List(CommandInvocation invocation)
    {
        invocation.Output.Lines(InstanceTable.Format(invocation.Session.Instances, invocation.Session.Home));
        return Task.CompletedTask;
    }

    /// <summary>
    /// Scans for instances again.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Refresh(CommandInvocation invocation)
    {
        invocation.Output.Line("Scanning for PostgreSQL instances...");
        invocation.Session.Refresh();
        invocation.Output.Line(invocation.Session.Instances.Count switch
        {
            0 => "No PostgreSQL instances found.",
            1 => "Found 1 PostgreSQL instance.",
            var count => $"Found {count} PostgreSQL instances.",
        });

        return Task.CompletedTask;
    }

    /// <summary>
    /// Clears the screen.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Clear(CommandInvocation invocation)
    {
        Repl(invocation).ClearScreen();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Leaves pgtail, stopping a paused streaming tail first.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Quit(CommandInvocation invocation)
    {
        var host = Repl(invocation);
        if (host.IsStreaming)
        {
            host.StopStreaming();
        }

        host.Exit();
        return Task.CompletedTask;
    }

    /// <summary>
    /// Stops a paused streaming tail.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Stop(CommandInvocation invocation)
    {
        var host = Repl(invocation);
        if (!host.IsStreaming)
        {
            invocation.Output.Line("Not currently tailing.");
            return Task.CompletedTask;
        }

        host.StopStreaming();
        invocation.Output.Line("Stopped tailing.");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Shows or sets the display mode.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Display(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var display = invocation.Session.Display;
        var args = invocation.Args;
        var validFields = $"Valid fields: {string.Join(", ", DisplayFields.Valid)}";
        if (args.Count == 0)
        {
            output.Line(display.FormatStatus());
            return Task.CompletedTask;
        }

        switch (args[0].ToLowerInvariant())
        {
            case "compact":
                display.SetCompact();
                output.Line("Display mode: compact");
                break;
            case "full":
                display.SetFull();
                output.Line("Display mode: full");
                break;
            case "fields" when args.Count < 2:
                output.Line("Usage: display fields <field1,field2,...>");
                output.Line(validFields);
                break;
            case "fields":
                var fields = args[1].Split(',', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
                if (fields.Length == 0)
                {
                    output.Line("No fields specified.");
                    output.Line(validFields);
                    break;
                }

                var invalid = display.SetCustom(fields);
                if (invalid.Count > 0)
                {
                    output.Line($"Unknown fields: {string.Join(", ", invalid)}");
                    output.Line(validFields);
                    if (display.CustomFields.Count > 0)
                    {
                        output.Line($"Using valid fields: {string.Join(", ", display.CustomFields)}");
                    }
                }
                else
                {
                    output.Line($"Display mode: custom ({fields.Length} fields)");
                }

                break;
            default:
                output.Line($"Unknown display mode: {args[0].ToLowerInvariant()}");
                output.Line("Usage: display [compact|full|fields <field1,field2,...>]");
                break;
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Shows or sets the output format.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Output(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var display = invocation.Session.Display;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            output.Line($"Output format: {(display.OutputFormat == OutputFormat.Json ? "json" : "text")}");
            output.Line();
            output.Line("Usage: output json   Output as JSON (one object per line)");
            output.Line("       output text   Output as colored text (default)");
            return Task.CompletedTask;
        }

        switch (args[0].ToLowerInvariant())
        {
            case "json":
                display.OutputFormat = OutputFormat.Json;
                output.Line("Output format: json");
                output.Line("Note: Slow query highlighting and regex highlights disabled in JSON mode");
                break;
            case "text":
                display.OutputFormat = OutputFormat.Text;
                output.Line("Output format: text");
                break;
            default:
                output.Line($"Unknown output format: {args[0].ToLowerInvariant()}");
                output.Line("Usage: output [json|text]");
                break;
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL host of a REPL command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>The host.</returns>
    public static IReplHost Repl(CommandInvocation invocation) => (IReplHost)invocation.Host;
}
