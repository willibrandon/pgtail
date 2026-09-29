using Pgtail.Configuration;
using Pgtail.Detection;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Toml;

namespace Pgtail.Commands;

/// <summary>
/// Settings and configuration: <c>set</c>, <c>unset</c>, <c>config</c>, and <c>enable-logging</c>.
/// </summary>
internal static class ConfigCommands
{
    /// <summary>
    /// The REPL's <c>set</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Set(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            output.Line("Usage: set <key> [value]");
            output.Line();
            ListSettings(output, withDefaults: true);
            return Task.CompletedTask;
        }

        if (SettingsSchema.Find(args[0]) is not { } setting)
        {
            output.Line($"Unknown setting: {args[0]}");
            output.Line();
            ListSettings(output, withDefaults: false);
            return Task.CompletedTask;
        }

        if (args.Count == 1)
        {
            var current = session.Config[setting.Key];
            output.Line($"{setting.Key} = {Show(current)}");
            if (!Equal(current, setting.Default))
            {
                output.Line($"  (default: {Show(setting.Default)})");
            }

            return Task.CompletedTask;
        }

        if (Save(invocation, setting, [.. args.Skip(1)], out var error) is not { } value)
        {
            output.Line(error!);
            return Task.CompletedTask;
        }

        output.Line($"{setting.Key} = {Show(value)}");
        output.Line($"Saved to {session.Store.ConfigFile}");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Tail mode's <c>set</c> command, which redraws the log when a highlighting setting changes.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailSet(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            output.Markup("[dim]Usage: set <key> [value][/dim]");
            output.Line();
            output.Markup("[bold]Available settings:[/bold]");
            foreach (var key in SettingsSchema.Keys)
            {
                output.Markup($"  [cyan]{key}[/cyan]");
            }

            return Task.CompletedTask;
        }

        if (SettingsSchema.Find(args[0]) is not { } setting)
        {
            output.Markup($"[red]Unknown setting: {Markup.Escape(args[0])}[/red]");
            return Task.CompletedTask;
        }

        if (args.Count == 1)
        {
            var current = session.Config[setting.Key];
            var line = $"[cyan]{setting.Key}[/cyan] = [magenta]{Markup.Escape(Show(current))}[/magenta]";
            if (!Equal(current, setting.Default))
            {
                line += $" [dim](default: {Markup.Escape(Show(setting.Default))})[/dim]";
            }

            output.Markup(line);
            return Task.CompletedTask;
        }

        var version = session.Highlighting.Version;
        var theme = session.Theme;
        if (Save(invocation, setting, [.. args.Skip(1)], out var error) is not { } value)
        {
            output.Markup($"[red]{Markup.Escape(error!)}[/red]");
            return Task.CompletedTask;
        }

        output.Markup($"[green]Set[/green] [cyan]{setting.Key}[/cyan] = [magenta]{Markup.Escape(Show(value))}[/magenta]");
        var host = (ITailHost)invocation.Host;
        host.RefreshStatus();
        if (session.Highlighting.Version != version || session.Theme != theme || setting.Key == "default.levels")
        {
            host.Rebuild();
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// The <c>unset</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task Unset(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        if (args.Count == 0)
        {
            output.Line("Usage: unset <key>");
            output.Line();
            output.Line("Remove a setting to revert to its default value.");
            output.Line();
            ListSettings(output, withDefaults: true);
            return Task.CompletedTask;
        }

        if (SettingsSchema.Find(args[0]) is not { } setting)
        {
            output.Line($"Unknown setting: {args[0]}");
            output.Line();
            ListSettings(output, withDefaults: false);
            return Task.CompletedTask;
        }

        if (!session.Store.Exists)
        {
            output.Line($"{setting.Key} is not set (no config file exists).");
            output.Line($"Already using default: {Show(setting.Default)}");
            return Task.CompletedTask;
        }

        if (!session.Store.Delete(setting.Key))
        {
            output.Line($"{setting.Key} is not set in config file.");
            output.Line($"Current value is already the default: {Show(setting.Default)}");
            return Task.CompletedTask;
        }

        session.Config[setting.Key] = setting.Default;
        session.ApplySetting(setting.Key);
        output.Line($"{setting.Key} reset to default: {Show(setting.Default)}");
        return Task.CompletedTask;
    }

    /// <summary>
    /// The <c>config</c> command: show the settings, or <c>path</c>, <c>edit</c>, or <c>reset</c>.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the command has finished.</returns>
    public static async Task Config(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var store = session.Store;
        if (invocation.Args.Count > 0)
        {
            switch (invocation.Args[0].ToLowerInvariant())
            {
                case "path":
                    output.Line(store.ConfigFile);
                    output.Line(store.Exists ? "  (file exists)" : "  (file not created yet - use 'set' to create)");
                    return;
                case "edit":
                    await EditAsync(invocation);
                    return;
                case "reset":
                    Reset(invocation);
                    return;
                default:
                    output.Line($"Unknown subcommand: {invocation.Args[0].ToLowerInvariant()}");
                    output.Line("Available: path, edit, reset");
                    return;
            }
        }

        output.Lines(Show(session.Config, store));
    }

    /// <summary>
    /// The settings as TOML, as <c>config</c> prints them.
    /// </summary>
    /// <param name="config">The settings.</param>
    /// <param name="store">The store, for the file path.</param>
    /// <returns>The lines.</returns>
    public static IReadOnlyList<string> Show(PgtailConfig config, ConfigStore store)
    {
        ArgumentNullException.ThrowIfNull(config);
        ArgumentNullException.ThrowIfNull(store);
        var lines = new List<string>();
        if (store.Exists)
        {
            lines.Add($"# Config file: {store.ConfigFile}");
        }
        else
        {
            lines.Add($"# Config file: {store.ConfigFile} (not created yet)");
            lines.Add("# Showing default values");
        }

        lines.Add("");
        lines.Add("[default]");
        lines.Add($"levels = {TomlFormatter.Format(config["default.levels"]!)}");
        lines.Add("");
        lines.Add("[slow]");
        lines.Add($"warn = {config.SlowWarn}");
        lines.Add($"error = {config.SlowError}");
        lines.Add($"critical = {config.SlowCritical}");
        lines.Add("");
        lines.Add("[theme]");
        lines.Add($"name = {TomlFormatter.Quote(config.ThemeName)}");
        lines.Add("");
        lines.Add("[notifications]");
        lines.Add($"enabled = {TomlFormatter.Format(config.NotificationsEnabled)}");
        lines.Add($"levels = {TomlFormatter.Format(config["notifications.levels"]!)}");
        lines.Add(config.QuietHours is { } quiet ? $"quiet_hours = {TomlFormatter.Quote(quiet)}" : "# quiet_hours = \"22:00-08:00\"");
        return lines;
    }

    /// <summary>
    /// The <c>enable-logging</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task EnableLogging(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        if (invocation.Args.Count == 0)
        {
            output.Line("Usage: enable-logging <id|path>");
            output.Line();
            output.Line("Enables logging_collector in postgresql.conf");
            output.Line("After running, you must restart PostgreSQL for changes to take effect.");
            return Task.CompletedTask;
        }

        if (InstanceTable.Find(session.Instances, invocation.Args[0], invocation.Host.CurrentDirectory) is not { } instance)
        {
            InstanceNotFound(invocation, invocation.Args[0]);
            return Task.CompletedTask;
        }

        if (instance.LogPath is { } log && File.Exists(log))
        {
            output.Line($"Logging is already enabled for instance {instance.Id}");
            output.Line($"Log file: {log}");
            return Task.CompletedTask;
        }

        output.Line($"Enabling logging for instance {instance.Id}...");
        output.Line($"Data directory: {instance.DataDirectory}");
        output.Line();
        var result = LoggingEnabler.Enable(instance.DataDirectory, instance.ConfigPath);
        if (result.Changes.Count > 0)
        {
            output.Line("Changes made:");
            foreach (var change in result.Changes)
            {
                output.Line($"  • {change}");
            }

            output.Line();
        }

        if (!result.Success)
        {
            output.Line($"Error: {result.Message}");
            return Task.CompletedTask;
        }

        output.Line(result.Message);
        output.Line();
        output.Line("⚠️  PostgreSQL must be restarted for changes to take effect:");
        output.Line(instance.Running ? $"    pg_ctl restart -D {instance.DataDirectory}" : $"    pg_ctl start -D {instance.DataDirectory}");
        output.Line();
        output.Line("After restarting, run 'refresh' to update instance list.");
        return Task.CompletedTask;
    }

    /// <summary>
    /// Reports an instance that was not found, listing those that were.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <param name="argument">The ID or path typed.</param>
    public static void InstanceNotFound(CommandInvocation invocation, string argument)
    {
        ArgumentNullException.ThrowIfNull(invocation);
        var output = invocation.Output;
        output.Line($"Instance not found: {argument}");
        output.Line();
        output.Line("Available instances:");
        foreach (var instance in invocation.Session.Instances)
        {
            output.Line($"  {instance.Id}: {instance.DataDirectory}");
        }
    }

    /// <summary>
    /// A setting's value as TOML, or <c>(not set)</c>.
    /// </summary>
    /// <param name="value">The value.</param>
    /// <returns>The text.</returns>
    public static string Show(object? value) => value is null ? "(not set)" : TomlFormatter.Format(value);

    private static object? Save(CommandInvocation invocation, SettingDefinition setting, IReadOnlyList<string> words, out string? error)
    {
        var session = invocation.Session;
        object value;
        try
        {
            value = setting.Validate(setting.Parse(words));
        }
        catch (FormatException exception)
        {
            error = $"Invalid value for {setting.Key}: {exception.Message}";
            return null;
        }

        if (session.Store.Save(setting.Key, value) is { } failure)
        {
            error = $"Failed to save configuration: {failure}";
            return null;
        }

        session.Config[setting.Key] = value;
        session.ApplySetting(setting.Key);
        error = null;
        return value;
    }

    /// <summary>
    /// The request to edit the configuration file in the built-in editor, which saves only valid settings.
    /// </summary>
    /// <param name="session">The session.</param>
    /// <returns>The request.</returns>
    public static EditRequest ConfigEditRequest(PgtailSession session)
    {
        ArgumentNullException.ThrowIfNull(session);
        var file = session.Store.ConfigFile;
        return new EditRequest(file, $"Editing {PathDisplay.Shorten(file, session.Home)}", ConfigStore.DefaultTemplate,
            ConfigStore.Problems);
    }

    private static async Task EditAsync(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var store = session.Store;
        if (!store.Exists)
        {
            output.Line($"Creating config file: {store.ConfigFile}");
            store.CreateDefault();
        }

        var saved = await CoreCommands.Repl(invocation).EditAsync(ConfigEditRequest(session));
        if (!saved)
        {
            output.Line("No changes saved.");
            return;
        }

        output.Line("Reloading configuration...");
        session.Reload();
        foreach (var warning in session.TakeWarnings())
        {
            output.Line($"Warning: {warning}");
        }

        output.Line("Configuration reloaded.");
    }

    private static void Reset(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        if (!session.Store.Exists)
        {
            output.Line("No config file to reset.");
            output.Line($"Config path: {session.Store.ConfigFile}");
            output.Line();
            output.Line("Already using default settings.");
            return;
        }

        string? backup;
        try
        {
            backup = session.Store.Reset(DateTime.Now);
        }
        catch (IOException exception)
        {
            output.Line($"Error: Could not reset config file ({exception.Message})");
            return;
        }

        session.Reload();
        output.Line("Configuration reset to defaults.");
        output.Line();
        output.Line($"Backup saved: {backup}");
    }

    private static void ListSettings(CommandOutput output, bool withDefaults)
    {
        output.Line("Available settings:");
        foreach (var setting in SettingsSchema.All)
        {
            output.Line(withDefaults ? $"  {setting.Key} (default: {Show(setting.Default)})" : $"  {setting.Key}");
        }
    }

    private static bool Equal(object? left, object? right) => (left, right) switch
    {
        (IEnumerable<string> a, IEnumerable<string> b) => a.SequenceEqual(b),
        _ => Equals(left, right),
    };
}
