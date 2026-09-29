using Pgtail.Detection;
using Pgtail.Filtering;
using Pgtail.Sessions;

namespace Pgtail.Commands;

/// <summary>
/// The REPL's <c>tail</c> command.
/// </summary>
internal static class TailCommand
{
    /// <summary>
    /// Tails an instance or files, full screen or with <c>--stream</c>.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when tailing ends or pauses.</returns>
    public static async Task Run(CommandInvocation invocation)
    {
        var output = invocation.Output;
        var session = invocation.Session;
        var args = invocation.Args;
        DateTime? since = null;
        var stream = false;
        var files = new List<string>();
        string? instanceArgument = null;
        for (var i = 0; i < args.Count; i++)
        {
            switch (args[i])
            {
                case "--since" when i + 1 < args.Count:
                    try
                    {
                        since = TimeParser.Parse(args[++i]);
                    }
                    catch (FormatException exception)
                    {
                        output.Line($"Error parsing --since time: {exception.Message}");
                        return;
                    }

                    break;
                case "--stream":
                    stream = true;
                    break;
                case "--file" or "-f" when i + 1 >= args.Count:
                    output.Line("Error: --file requires a path argument");
                    output.Line("Usage: tail --file <path>");
                    return;
                case "--file" or "-f":
                    files.Add(args[++i]);
                    break;
                case var option when option.StartsWith("--", StringComparison.Ordinal):
                    output.Line($"Unknown option: {option}");
                    return;
                default:
                    instanceArgument ??= args[i];
                    break;
            }
        }

        if (files.Count > 0 && instanceArgument is not null && instanceArgument.All(char.IsAsciiDigit))
        {
            output.Line("Error: Cannot specify both --file and instance ID");
            return;
        }

        var host = CoreCommands.Repl(invocation);
        if (files.Count > 0)
        {
            var (resolved, glob, error) = TailTargets.ResolveFiles(files, session.Home, invocation.Host.CurrentDirectory,
                warning => output.Line($"Warning: {warning}"));
            if (error is not null)
            {
                output.Line($"Error: {error}");
                return;
            }

            if (stream && resolved.Count > 1)
            {
                output.Line("Error: --stream mode only supports single file");
                output.Line("Use without --stream for multiple files");
                return;
            }

            ApplySince(session, since);
            await host.TailAsync(new TailRequest(new TailSource(Files: resolved, GlobPattern: glob), resolved[0], stream));
            return;
        }

        PostgresInstance? instance;
        if (instanceArgument is null)
        {
            switch (session.Instances.Count)
            {
                case 0:
                    output.Line("No instances detected. Run 'refresh' to scan.");
                    return;
                case > 1:
                    output.Line("Multiple instances found. Specify an ID or use --file:");
                    output.Line("  tail <id>");
                    output.Line("  tail --file <path>");
                    output.Line();
                    output.Lines(InstanceTable.Format(session.Instances, session.Home));
                    return;
            }

            instance = session.Instances[0];
        }
        else if (InstanceTable.Find(session.Instances, instanceArgument, invocation.Host.CurrentDirectory) is { } found)
        {
            instance = found;
        }
        else
        {
            ConfigCommands.InstanceNotFound(invocation, instanceArgument);
            return;
        }

        if (TailTargets.LogFile(instance) is not { } log)
        {
            if (instance.LoggingEnabled)
            {
                output.Line($"Cannot access log files for instance {instance.Id}");
                output.Line($"Log directory: {instance.LogDirectory ?? "unknown"}");
                output.Line();
                output.Lines(PermissionAdvice.LogsNotFound());
            }
            else
            {
                output.Line($"Logging not enabled for instance {instance.Id}");
                output.Line($"Data directory: {instance.DataDirectory}");
                output.Line();
                output.Line($"Enable logging with: enable-logging {instance.Id}");
            }

            return;
        }

        if (!File.Exists(log))
        {
            output.Line($"Log file not found: {log}");
            return;
        }

        ApplySince(session, since);
        await host.TailAsync(new TailRequest(new TailSource(Instance: instance with { LogPath = log }), log, stream));
    }

    private static void ApplySince(PgtailSession session, DateTime? since)
    {
        if (since is { } time)
        {
            session.Time = new TimeFilter(since: time);
        }
    }
}
