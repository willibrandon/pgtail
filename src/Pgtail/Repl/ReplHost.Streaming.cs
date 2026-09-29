using Pgtail.Commands;
using Pgtail.Rendering;
using Pgtail.Styling;
using Pgtail.Tailing;

namespace Pgtail.Repl;

/// <content>
/// Streaming output: <c>tail --stream</c> and live event streams, written straight to the terminal.
/// </content>
internal sealed partial class ReplHost
{
    private PausedStream? _stream;

    /// <inheritdoc/>
    public bool IsStreaming => _stream is not null;

    /// <summary>
    /// Opens standard input for a standard input source.
    /// </summary>
    public Func<Stream> StandardInput { get; init; } = Console.OpenStandardInput;

    private string? StreamLabel => _stream?.Label;

    /// <inheritdoc/>
    public async Task TailAsync(TailRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (_stream is not null)
        {
            StopStreaming();
        }

        Session.LastSource = request.Source;
        if (!request.Stream)
        {
            await RunTailScreenAsync(request);
            return;
        }

        Output.Line($"Tailing {request.LogPath}");
        if (Session.Time.IsActive)
        {
            Output.Line($"Time filter: {Session.Time.FormatDescription()}");
        }

        if (Session.Fields.IsActive)
        {
            Output.Line(Session.Fields.FormatStatus());
        }

        if (Session.Display.Mode != Display.DisplayMode.Compact || Session.Display.OutputFormat != Display.OutputFormat.Text)
        {
            Output.Line(Session.Display.FormatStatus());
        }

        Output.Line("Press Ctrl+C to stop");
        Output.Line();
        Session.Buffer.Clear();
        var source = LogSources.Create(request, Session, CurrentDirectory, StandardInput);
        source.Start();
        _stream = new PausedStream(source, request.Source.DisplayName);
        _pending = StreamRequest(async (writer, cancellationToken) =>
        {
            await new EntryStreamer(Session, writer, styled: true).RunAsync(source, cancellationToken);
            await writer.WriteLineAsync();
            await writer.WriteLineAsync("Paused. Use 'stop' to stop tailing.");
        });
    }

    /// <inheritdoc/>
    public void StopStreaming()
    {
        if (_stream is { } stream)
        {
            _stream = null;
            stream.Source.DisposeAsync().AsTask().GetAwaiter().GetResult();
        }
    }

    /// <inheritdoc/>
    public Task WatchAsync(Func<CancellationToken, IAsyncEnumerable<StyledText>> lines)
    {
        ArgumentNullException.ThrowIfNull(lines);
        _pending = StreamRequest(async (writer, cancellationToken) =>
        {
            try
            {
                await foreach (var line in lines(cancellationToken).WithCancellation(cancellationToken))
                {
                    await writer.WriteLineAsync(AnsiText.Render(line, Session.ColorEnabled));
                    await writer.FlushAsync(CancellationToken.None);
                }
            }
            catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
            {
                // Ctrl+C ends watching.
            }
        });

        return Task.CompletedTask;
    }

    // The lines the command printed just before streaming, such as "Press Ctrl+C to stop", are written by the stream
    // itself, once Ctrl+C stops it, so a Ctrl+C pressed as soon as they show is not lost.
    private ReplRequest StreamRequest(Func<TextWriter, CancellationToken, Task> stream)
    {
        var header = Output.Take();
        return new ReplRequest(ReplRequestKind.Stream)
        {
            Stream = async (writer, cancellationToken) =>
            {
                foreach (var line in header)
                {
                    await writer.WriteLineAsync(AnsiText.Render(line, Session.ColorEnabled));
                }

                await writer.FlushAsync(CancellationToken.None);
                await stream(writer, cancellationToken);
            },
        };
    }
}
