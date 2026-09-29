using Pgtail.Parsing;
using Pgtail.Rendering;
using Pgtail.Sessions;

namespace Pgtail.Tailing;

/// <summary>
/// Writes a source's entries to a terminal or pipe as they arrive: the legacy streaming mode.
/// </summary>
/// <param name="session">The session, for filters, formatting, and statistics.</param>
/// <param name="output">Where entries are written.</param>
/// <param name="styled">True when writing to a terminal: colors, attributes, and status lines; false for plain entries.</param>
internal sealed class EntryStreamer(PgtailSession session, TextWriter output, bool styled)
{
    /// <summary>
    /// Streams until the source ends or the token is cancelled.
    /// </summary>
    /// <remarks>
    /// Every entry is counted in the statistics, checked against notification rules, and kept in the session buffer;
    /// only entries that pass the filters are written. On a terminal, format detection and file switches are announced;
    /// in a pipe only entries are written, so the output stays one entry per line for tools such as <c>jq</c>.
    /// </remarks>
    /// <param name="source">The started source.</param>
    /// <param name="cancellationToken">Stops streaming.</param>
    /// <returns>A task that completes when streaming stops.</returns>
    public async Task RunAsync(ILogSource source, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(source);
        try
        {
            while (await source.Events.WaitToReadAsync(cancellationToken))
            {
                while (source.Events.TryRead(out var item))
                {
                    Write(item);
                }

                await output.FlushAsync(cancellationToken);
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            // Ctrl+C ends streaming.
        }
    }

    private void Write(LogSourceEvent item)
    {
        switch (item.Kind)
        {
            case LogSourceEventKind.Entry when item.Entry is { } entry:
                session.Buffer.Add(entry);
                if (session.Observe(entry) is { } notification)
                {
                    _ = Task.Run(() => session.Notifications.Deliver(notification));
                }

                if (session.ShouldShow(entry))
                {
                    output.WriteLine(AnsiText.Render(session.FormatEntry(entry, highlighted: styled), session.ColorEnabled, styled));
                }

                break;
            case LogSourceEventKind.FormatDetected when item.Format is { } format:
                session.DetectedFormat = format;
                if (styled)
                {
                    output.WriteLine($"Detected format: {format.ToDestinationName()}");
                }

                break;
            case LogSourceEventKind.FileSwitched when item.Path is { } path && styled:
                output.WriteLine();
                output.WriteLine($"Switched to: {Path.GetFileName(path)}");
                break;
        }
    }
}
