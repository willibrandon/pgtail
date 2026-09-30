using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.CompilerServices;
using System.Text;
using Pgtail.Exporting;
using Pgtail.Filtering;
using Pgtail.Parsing;
using Pgtail.Rendering;
using Pgtail.Sessions;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Commands;

/// <summary>
/// The <c>export</c> and <c>pipe</c> commands, which write the filtered entries of the last tail elsewhere.
/// </summary>
internal static class ExportCommands
{
    private const string NoLog = "No log file loaded. Use 'tail <instance>' first.";

    /// <summary>
    /// The REPL's <c>export</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the export has finished.</returns>
    public static async Task Export(CommandInvocation invocation)
    {
        CommandOutput output = invocation.Output;
        PgtailSession session = invocation.Session;
        if (session.LastSource is not { } source)
        {
            output.Line(NoLog);
            return;
        }

        (bool append, bool follow, bool highlighted) = (false, false, false);
        ExportFormat format = ExportFormat.Text;
        DateTime? since = null;
        string? file = null;
        IReadOnlyList<string> args = invocation.Args;
        for (int i = 0; i < args.Count; i++)
        {
            switch (args[i])
            {
                case "--append":
                    append = true;
                    break;
                case "--follow":
                    follow = true;
                    break;
                case "--highlighted":
                    highlighted = true;
                    break;
                case "--format" when i + 1 < args.Count:
                    try
                    {
                        format = ExportFormats.Parse(args[++i]);
                    }
                    catch (FormatException exception)
                    {
                        output.Line($"Error: {exception.Message}");
                        return;
                    }

                    break;
                case "--since" when i + 1 < args.Count:
                    try
                    {
                        since = TimeParser.Parse(args[++i]);
                    }
                    catch (FormatException exception)
                    {
                        output.Line($"Error: {exception.Message}");
                        return;
                    }

                    break;
                case var option when option.StartsWith("--", StringComparison.Ordinal):
                    output.Line($"Unknown option: {option}");
                    return;
                default:
                    file = args[i];
                    break;
            }
        }

        if (file is null)
        {
            output.Lines(
            [
                "Usage: export [options] <filename>",
                "",
                "Export filtered log entries to a file.",
                "",
                "Options:",
                "  --append         Append to existing file",
                "  --format <fmt>   Output format (text, json, csv)",
                "  --since <time>   Only entries after time (e.g., 1h, 30m, 2d)",
                "  --follow         Continuous export (like tail -f | tee)",
                "  --highlighted    Keep colors (ANSI escapes) in text output",
            ]);
            return;
        }

        if (follow && append)
        {
            output.Line("Error: Cannot use --follow with --append");
            return;
        }

        if (follow && since is not null)
        {
            output.Line("Error: Cannot use --follow with --since");
            return;
        }

        string path = PathDisplay.Resolve(file, session.Home, invocation.Host.CurrentDirectory);
        IReplHost host = CoreCommands.Repl(invocation);
        if (!append && File.Exists(path) && !await host.ConfirmAsync($"File {file} exists. Overwrite? [y/N] "))
        {
            output.Line("Export cancelled.");
            return;
        }

        if (follow)
        {
            // The log is opened before the header shows, so every entry written after it is exported.
            string? logPath = source.Instance?.LogPath ?? (source.Files is [var first, ..] ? first : null);
            ILogSource tail = LogSources.Create(new TailRequest(source, logPath, Stream: true), session, invocation.Host.CurrentDirectory,
                Console.OpenStandardInput);
            tail.Start();
            output.Line($"Exporting to {file} (Ctrl+C to stop)");
            output.Line();
            await host.WatchAsync(cancellationToken => FollowAsync(session, tail, path, file, format, highlighted, cancellationToken));
            return;
        }

        IEnumerable<LogEntry> entries = Filtered(session, session.Buffer.Snapshot(), since);
        try
        {
            int count = EntryExporter.WriteFile(entries, path, format, append, Highlighter(session, highlighted));
            output.Line(count == 0 ? "No entries to export (buffer is empty or all filtered out)." : $"Exported {count} entries to {file}");
        }
        catch (UnauthorizedAccessException)
        {
            output.Line($"Error: Permission denied: {file}");
            output.Line("Try a different location or check permissions.");
        }
        catch (IOException exception)
        {
            output.Line($"Error writing to file: {exception.Message}");
        }
    }

    /// <summary>
    /// Tail mode's <c>export</c> command, which writes the entries the log currently shows.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A completed task.</returns>
    public static Task TailExport(CommandInvocation invocation)
    {
        CommandOutput output = invocation.Output;
        PgtailSession session = invocation.Session;
        var host = (ITailHost)invocation.Host;
        IReadOnlyList<string> args = invocation.Args;
        if (args.Count == 0)
        {
            output.Markup("[bold red]✗[/] Usage: export <path> [--format text|json|csv] [--highlighted]");
            return Task.CompletedTask;
        }

        string? file = null;
        ExportFormat format = ExportFormat.Text;
        bool highlighted = false;
        for (int i = 0; i < args.Count; i++)
        {
            switch (args[i])
            {
                case "--format" when i + 1 < args.Count:
                    try
                    {
                        format = ExportFormats.Parse(args[++i]);
                    }
                    catch (FormatException exception)
                    {
                        output.Markup($"[bold red]✗[/] {Markup.Escape(exception.Message)}");
                        return Task.CompletedTask;
                    }

                    break;
                case "--highlighted":
                    highlighted = true;
                    break;
                case var option when option.StartsWith('-'):
                    output.Markup($"[bold red]✗[/] Unknown option: {Markup.Escape(option)}");
                    return Task.CompletedTask;
                default:
                    file = args[i];
                    break;
            }
        }

        if (file is null)
        {
            output.Markup("[bold red]✗[/] No output path specified");
            return Task.CompletedTask;
        }

        var entries = host.Entries.Where(session.ShouldShow).ToList();
        if (entries.Count == 0)
        {
            output.Markup("[yellow]⚠[/] No entries to export (buffer empty or all filtered)");
            return Task.CompletedTask;
        }

        string path = PathDisplay.Resolve(file, session.Home, invocation.Host.CurrentDirectory);
        try
        {
            Func<LogEntry, string>? line = highlighted
                ? entry => AnsiText.Render(Display.EntryFormatter.TailLine(entry, session.Theme, session.Chain, session.SlowLevel(entry)),
                    session.ColorEnabled)
                : null;
            int count = EntryExporter.WriteFile(entries, path, format, append: false, line);
            output.Markup($"[bold green]✓[/] Exported {count} entries to [cyan]{Markup.Escape(path)}[/]");
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            output.Markup($"[bold red]✗[/] Export failed: {Markup.Escape(exception.Message)}");
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// The REPL's <c>pipe</c> command.
    /// </summary>
    /// <param name="invocation">The command.</param>
    /// <returns>A task that completes when the command has exited.</returns>
    public static async Task Pipe(CommandInvocation invocation)
    {
        CommandOutput output = invocation.Output;
        PgtailSession session = invocation.Session;
        if (session.LastSource is null)
        {
            output.Line(NoLog);
            return;
        }

        ExportFormat format = ExportFormat.Text;
        IReadOnlyList<string> args = invocation.Args;
        int start = args.Count;
        for (int i = 0; i < args.Count; i++)
        {
            if (args[i] == "--format" && i + 1 < args.Count)
            {
                try
                {
                    format = ExportFormats.Parse(args[++i]);
                }
                catch (FormatException exception)
                {
                    output.Line($"Error: {exception.Message}");
                    return;
                }

                continue;
            }

            if (args[i].StartsWith("--", StringComparison.Ordinal))
            {
                output.Line($"Unknown option: {args[i]}");
                return;
            }

            start = i;
            break;
        }

        string command = invocation.RawFrom(start);
        if (command.Length == 0)
        {
            output.Lines(
            [
                "Usage: pipe [--format text|json|csv] <command...>",
                "",
                "Pipe filtered log entries to an external command.",
                "",
                "Options:",
                "  --format <fmt>   Output format (text, json, csv)",
                "",
                "Examples:",
                "  pipe wc -l              Count filtered entries",
                "  pipe grep ERROR         Search for ERROR in entries",
                "  pipe --format json jq   Process JSON with jq",
            ]);
            return;
        }

        var entries = Filtered(session, session.Buffer.Snapshot(), since: null).ToList();
        var start2 = new ProcessStartInfo(OperatingSystem.IsWindows() ? "cmd.exe" : "/bin/sh")
        {
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardInputEncoding = new UTF8Encoding(false),
        };

        start2.ArgumentList.Add(OperatingSystem.IsWindows() ? "/c" : "-c");
        start2.ArgumentList.Add(command);
        try
        {
            using Process process = Process.Start(start2)!;
            Task<string> stdout = process.StandardOutput.ReadToEndAsync();
            Task<string> stderr = process.StandardError.ReadToEndAsync();
            try
            {
                if (format == ExportFormat.Csv)
                {
                    await process.StandardInput.WriteAsync(EntryExporter.CsvHeader + "\n");
                }

                foreach (LogEntry? entry in entries)
                {
                    await process.StandardInput.WriteAsync(EntryExporter.Format(entry, format) + "\n");
                }

                process.StandardInput.Close();
            }
            catch (IOException)
            {
                // The command stopped reading, as head does; its output still counts.
            }

            await process.WaitForExitAsync();
            (string? text, string? errors) = (await stdout, await stderr);
            if (text.TrimEnd().Length > 0)
            {
                output.Line(text.TrimEnd());
            }

            if (errors.TrimEnd().Length > 0)
            {
                output.Line($"stderr: {errors.TrimEnd()}");
            }

            if (process.ExitCode != 0)
            {
                output.Line($"Command exited with code {process.ExitCode}");
            }
        }
        catch (Win32Exception exception)
        {
            output.Line($"Error running command: {exception.Message}");
        }
    }

    private static IEnumerable<LogEntry> Filtered(PgtailSession session, IEnumerable<LogEntry> entries, DateTime? since)
    {
        DateTime? bound = since is { } time ? LogTimestamps.ToUtc(time) : null;
        return entries.Where(entry => session.ShouldShow(entry)
            && (bound is null || entry.Timestamp is not { } stamp || LogTimestamps.ToUtc(stamp) >= bound));
    }

    private static Func<LogEntry, string>? Highlighter(PgtailSession session, bool highlighted) =>
        highlighted ? entry => AnsiText.Render(session.FormatEntry(entry), session.ColorEnabled) : null;

    private static async IAsyncEnumerable<StyledText> FollowAsync(
        PgtailSession session,
        ILogSource tail,
        string path,
        string file,
        ExportFormat format,
        bool highlighted,
        [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        int count = 0;
        await using (tail)
        {
            await using var writer = new StreamWriter(path, append: false, new UTF8Encoding(false)) { NewLine = "\n" };
            if (format == ExportFormat.Csv)
            {
                await writer.WriteLineAsync(EntryExporter.CsvHeader);
            }

            Func<LogEntry, string>? line = Highlighter(session, highlighted);
            while (!cancellationToken.IsCancellationRequested)
            {
                try
                {
                    _ = await tail.Events.WaitToReadAsync(cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }

                while (tail.Events.TryRead(out LogSourceEvent? item))
                {
                    if (item.Entry is not { } entry || !session.ShouldShow(entry))
                    {
                        continue;
                    }

                    string text = format == ExportFormat.Text && line is not null ? line(entry) : EntryExporter.Format(entry, format);
                    await writer.WriteLineAsync(text);
                    await writer.FlushAsync(CancellationToken.None);
                    count++;
                    yield return session.FormatEntry(entry);
                }
            }
        }

        yield return new StyledText();
        yield return new StyledText($"Exported {count} entries to {file}");
    }
}
