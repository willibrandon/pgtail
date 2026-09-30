using System.Globalization;
using System.Text;
using Hex1b;
using Pgtail.Commands;
using Pgtail.Configuration;
using Pgtail.Detection;
using Pgtail.Editing;
using Pgtail.Filtering;
using Pgtail.Rendering;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Tail;
using Pgtail.Tailing;
using Pgtail.Updates;

namespace Pgtail.Cli;

/// <summary>
/// Runs pgtail from its command line.
/// </summary>
internal static class PgtailCli
{
    /// <summary>
    /// Runs a command line.
    /// </summary>
    /// <param name="args">The arguments.</param>
    /// <returns>The exit code.</returns>
    public static async Task<int> RunAsync(string[] args)
    {
        ConsoleSupport.EnableEscapeSequences();
        CliArguments arguments;
        try
        {
            arguments = CliParser.Parse(args);
        }
        catch (CliParseException exception)
        {
            await Console.Error.WriteLineAsync(CliHelp.Error(exception));
            return 2;
        }

        switch (arguments.Command)
        {
            case CliCommand.Version:
                Console.Out.WriteLine($"pgtail {PgtailVersion.Current}");
                return 0;
            case CliCommand.Help:
                Console.Out.WriteLine(CliHelp.For(arguments.HelpFor));
                return 0;
            case CliCommand.CheckUpdate:
                return await CheckUpdateAsync();
            case CliCommand.ShowCompletion or CliCommand.InstallCompletion or CliCommand.Complete:
                return ShellCompletion.Run(arguments);
        }

        // Package validation and installers start pgtail with no arguments and no one to type; that must end at once with
        // status 0, before anything is read or written that could fail.
        if (arguments.Command == CliCommand.Repl && !ConsoleSupport.IsInteractive())
        {
            return 0;
        }

        var session = PgtailSession.ForCurrentUser();
        return arguments.Command switch
        {
            CliCommand.ListInstances => ListInstances(session, arguments.Verbose),
            CliCommand.Tail => await TailAsync(session, arguments),
            CliCommand.Config => await ConfigAsync(session, arguments),
            CliCommand.EnableLogging => EnableLogging(session, arguments.Instance!),
            _ => await ReplAsync(session),
        };
    }

    private static async Task<int> ReplAsync(PgtailSession session)
    {
        string executable = Environment.ProcessPath ?? "";
        var updates = new UpdateChecker(PgtailVersion.Current,
            InstallMethods.UpgradeCommand(InstallMethods.Detect(executable, Environment.GetEnvironmentVariable)));
        return await ReplRunner.RunAsync(session, updates);
    }

    private static async Task<int> CheckUpdateAsync()
    {
        string executable = Environment.ProcessPath ?? "";
        var checker = new UpdateChecker(PgtailVersion.Current,
            InstallMethods.UpgradeCommand(InstallMethods.Detect(executable, Environment.GetEnvironmentVariable)));
        string? latest = await checker.FetchLatestAsync(CancellationToken.None);
        bool color = string.IsNullOrEmpty(Environment.GetEnvironmentVariable("NO_COLOR"));
        Console.Out.WriteLine(AnsiText.Render(checker.Report(latest), color, styled: !Console.IsOutputRedirected && color));
        return 0;
    }

    private static int ListInstances(PgtailSession session, bool verbose)
    {
        session.Refresh();
        IReadOnlyList<PostgresInstance> instances = session.Instances;
        if (instances.Count == 0)
        {
            Console.Out.WriteLine("No PostgreSQL instances found.");
            return 1;
        }

        Console.Out.WriteLine($"Found {instances.Count} instance(s):");
        Console.Out.WriteLine();
        Console.Out.WriteLine($"{"ID",-4} {"Version",-10} {"Port",-6} {"Status",-8} Source");
        Console.Out.WriteLine(new string('-', 50));
        foreach (PostgresInstance instance in instances)
        {
            Console.Out.WriteLine(string.Create(CultureInfo.InvariantCulture,
                $"{instance.Id,-4} {instance.Version,-10} {instance.PortText,-6} {instance.StatusText,-8} {instance.Source.ToName()}"));
        }

        if (verbose)
        {
            Console.Out.WriteLine();
            foreach (PostgresInstance instance in instances)
            {
                Console.Out.WriteLine();
                Console.Out.WriteLine($"[Instance {instance.Id}]");
                Console.Out.WriteLine($"  Data directory: {instance.DataDirectory}");
                Console.Out.WriteLine($"  Log path: {instance.LogPath ?? "(none)"}");
                Console.Out.WriteLine($"  Logging enabled: {(instance.LoggingEnabled ? "yes" : "no")}");
            }
        }

        return 0;
    }

    private static int EnableLogging(PgtailSession session, string instance)
    {
        session.Refresh();
        var host = new ConsoleCommandHost(session);
        CommandInfo command = ReplCatalog.Catalog.Find("enable-logging")!;
        command.Handler(new CommandInvocation(command, "enable-logging", "enable-logging " + instance,
            [new CommandToken(instance, 15, 15 + instance.Length)], host)).GetAwaiter().GetResult();
        List<StyledText> failed = host.Output.Take();
        foreach (StyledText line in failed)
        {
            Console.Out.WriteLine(AnsiText.Render(line, session.ColorEnabled, styled: !Console.IsOutputRedirected));
        }

        return failed.Any(line => line.PlainText.StartsWith("Error:", StringComparison.Ordinal)
            || line.PlainText.StartsWith("Instance not found", StringComparison.Ordinal)) ? 1 : 0;
    }

    private static async Task<int> ConfigAsync(PgtailSession session, CliArguments arguments)
    {
        ConfigStore store = session.Store;
        if (arguments.ConfigPath)
        {
            Console.Out.WriteLine(store.ConfigFile);
            return 0;
        }

        if (arguments.ConfigEdit)
        {
            store.CreateDefault();
            var screen = new FileEditorScreen(ConfigCommands.ConfigEditRequest(session));

            await using Hex1bTerminal terminal = Terminals.Builder()
                .WithMouse()
                .WithHex1bApp(options => options.EnableDefaultCtrlCExit = false, app =>
                {
                    FileEditorScreen.Focus(app);
                    return context => screen.Build(context, app.RequestStop);
                })
                .Build();
            _ = await terminal.RunAsync();
            return 0;
        }

        if (arguments.ConfigReset)
        {
            string? backup = store.Reset(DateTime.Now);
            Console.Out.WriteLine(backup is null ? "No config file to reset." : $"Config reset. Backup saved to: {backup}");
            return 0;
        }

        foreach (string warning in session.TakeWarnings())
        {
            await Console.Error.WriteLineAsync($"Warning: {warning}");
        }

        foreach (string line in ConfigCommands.Show(session.Config, store))
        {
            Console.Out.WriteLine(line);
        }

        return 0;
    }

    private static async Task<int> TailAsync(PgtailSession session, CliArguments arguments)
    {
        TextWriter error = Console.Error;
        if (arguments.Stdin)
        {
            if (arguments.Files.Count > 0)
            {
                await error.WriteLineAsync("Cannot specify both --stdin and --file.");
                return 1;
            }

            if (arguments.Instance is not null)
            {
                await error.WriteLineAsync("Cannot specify both --stdin and instance ID.");
                return 1;
            }

            if (!Console.IsInputRedirected)
            {
                await error.WriteLineAsync("--stdin requires piped input (e.g., cat log.gz | gunzip | pgtail tail --stdin).");
                return 1;
            }
        }
        else if (arguments.Files.Count > 0 && arguments.Instance is not null)
        {
            await error.WriteLineAsync("Cannot specify both --file and instance ID");
            return 1;
        }

        if (arguments.Since is { } since)
        {
            try
            {
                session.Time = new TimeFilter(since: TimeParser.Parse(since));
            }
            catch (FormatException exception)
            {
                await error.WriteLineAsync($"Invalid time format: {exception.Message}");
                return 1;
            }
        }

        TailRequest request;
        if (arguments.Stdin)
        {
            request = new TailRequest(new TailSource(Stdin: true), null, arguments.Stream);
        }
        else if (arguments.Files.Count > 0)
        {
            (List<string> files, string? glob, string? problem) = TailTargets.ResolveFiles(
                arguments.Files,
                session.Home,
                Environment.CurrentDirectory,
                warning => error.WriteLine($"Warning: {warning}"));
            if (problem is not null)
            {
                await error.WriteLineAsync(problem);
                return 1;
            }

            if (arguments.Stream && files.Count > 1)
            {
                await error.WriteLineAsync("--stream mode only supports single file. Use without --stream for multiple files.");
                return 1;
            }

            request = new TailRequest(new TailSource(Files: files, GlobPattern: glob), files[0], arguments.Stream);
        }
        else if (await ResolveInstanceAsync(session, arguments.Instance) is { } instance)
        {
            request = new TailRequest(new TailSource(Instance: instance), instance.LogPath, arguments.Stream);
        }
        else
        {
            return 1;
        }

        session.LastSource = request.Source;
        return request.Stream ? await StreamAsync(session, request) : await FullScreenAsync(session, request);
    }

    private static async Task<PostgresInstance?> ResolveInstanceAsync(PgtailSession session, string? argument)
    {
        TextWriter error = Console.Error;
        session.Refresh();
        IReadOnlyList<PostgresInstance> instances = session.Instances;
        if (instances.Count == 0)
        {
            await error.WriteLineAsync("No PostgreSQL instances found.");
            return null;
        }

        int id = 0;
        if (argument is null)
        {
            if (instances.Count > 1)
            {
                await error.WriteLineAsync("Multiple instances found. Specify an ID or use --file.");
                await error.WriteLineAsync("Use 'pgtail list' to see available instances.");
                return null;
            }
        }
        else
        {
            id = int.Parse(argument, CultureInfo.InvariantCulture);
        }

        if (id < 0 || id >= instances.Count)
        {
            await error.WriteLineAsync($"Invalid instance ID: {id}. Use 'pgtail list' to see instances.");
            return null;
        }

        PostgresInstance instance = instances[id];
        if (!instance.LoggingEnabled)
        {
            await error.WriteLineAsync($"Logging not enabled for instance {id}.");
            await error.WriteLineAsync($"Enable with: pgtail enable-logging {id}");
            return null;
        }

        if (TailTargets.LogFile(instance) is not { } log || !File.Exists(log))
        {
            await error.WriteLineAsync($"Log file not found: {instance.LogPath}");
            return null;
        }

        return instance with { LogPath = log };
    }

    private static async Task<int> StreamAsync(PgtailSession session, TailRequest request)
    {
        bool styled = !Console.IsOutputRedirected;
        TextWriter output = Console.Out;
        if (styled)
        {
            output.WriteLine($"Tailing {(request.Source.Stdin ? "stdin" : request.LogPath)}");
            if (session.Time.IsActive)
            {
                output.WriteLine($"Time filter: {session.Time.FormatDescription()}");
            }

            output.WriteLine("Press Ctrl+C to stop");
            output.WriteLine();
        }

        await using ILogSource source = LogSources.Create(request, session, Environment.CurrentDirectory, Console.OpenStandardInput);
        source.Start();
        await ReplRunner.StreamAsync((writer, cancellationToken) =>
            new EntryStreamer(session, writer, styled).RunAsync(source, cancellationToken));
        return 0;
    }

    private static async Task<int> FullScreenAsync(PgtailSession session, TailRequest request)
    {
        using MemoryStream? piped = request.Source.Stdin ? new MemoryStream() : null;
        if (piped is { } buffer)
        {
            await Console.OpenStandardInput().CopyToAsync(buffer);
            if (buffer.Length == 0 || Encoding.UTF8.GetString(buffer.GetBuffer(), 0, (int)buffer.Length).Trim().Length == 0)
            {
                await Console.Error.WriteLineAsync("No input received from stdin.");
                return 1;
            }

            if (!ConsoleSupport.ReattachKeyboard())
            {
                await Console.Error.WriteLineAsync(
                    "Cannot open the terminal for keyboard input. Use --stream to print the entries instead.");
                return 1;
            }

            buffer.Position = 0;
        }

        ILogSource source = LogSources.Create(request, session, Environment.CurrentDirectory, () => piped!, TailScreen.BacklogLines);
        var screen = new TailScreen(session, request, source, Environment.CurrentDirectory);
        try
        {
            Hex1bAppOptions? options = null;
            await using Hex1bTerminal terminal = Terminals.Builder()
                .WithMouse()
                .WithHex1bApp(configure => options = configure, app => screen.Configure(app, options!))
                .Build();
            _ = await terminal.RunAsync();
        }
        finally
        {
            await screen.DisposeAsync();
        }

        return 0;
    }
}
