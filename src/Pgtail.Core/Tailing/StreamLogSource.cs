using System.Threading.Channels;
using Pgtail.Parsing;

namespace Pgtail.Tailing;

/// <summary>
/// Reads log entries from piped input until it ends.
/// </summary>
/// <remarks>
/// Every entry is marked as coming from <c>stdin</c>. The format is detected from the first non-blank line. Piped input
/// has no backlog to tell apart, so every entry counts as new. An entry's continuation lines may come in a later read, so
/// the last entry read waits until more input shows it is complete, or until the input is quiet for a moment.
/// </remarks>
/// <param name="input">The piped input.</param>
public sealed class StreamLogSource(Stream input) : ILogSource
{
    private static readonly TimeSpan Quiet = TimeSpan.FromMilliseconds(100);
    private readonly Channel<LogSourceEvent> _events = Channel.CreateUnbounded<LogSourceEvent>(
        new UnboundedChannelOptions { SingleReader = true, SingleWriter = true });

    private readonly CancellationTokenSource _stop = new();
    private readonly EntryGrouper _grouper = new();
    private Task? _loop;

    /// <inheritdoc />
    public ChannelReader<LogSourceEvent> Events => _events.Reader;

    /// <inheritdoc />
    public bool IsUnavailable => false;

    /// <inheritdoc />
    public bool IsPermissionDenied => false;

    /// <summary>
    /// The number of non-blank lines read.
    /// </summary>
    public long LinesRead { get; private set; }

    /// <inheritdoc />
    public void Start() => _loop ??= Task.Run(ReadAsync);

    /// <inheritdoc />
    /// <remarks>
    /// Piped input reads nothing back.
    /// </remarks>
    public void StopReadingOlder()
    {
    }

    /// <inheritdoc />
    public async ValueTask DisposeAsync()
    {
        await _stop.CancelAsync().ConfigureAwait(false);
        if (_loop is not null)
        {
            try
            {
                await _loop.ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                // Stopping is the expected way for the read to end.
            }
        }

        _stop.Dispose();
    }

    private async Task ReadAsync()
    {
        _events.Writer.TryWrite(new LogSourceEvent(LogSourceEventKind.CaughtUp));
        var buffer = new byte[64 * 1024];
        var pending = new List<byte>();
        LogFormat? format = null;
        try
        {
            while (true)
            {
                var reading = input.ReadAsync(buffer, _stop.Token).AsTask();
                if (_grouper.IsHolding && await Task.WhenAny(reading, Task.Delay(Quiet, _stop.Token)).ConfigureAwait(false) != reading)
                {
                    Flush();
                }

                var read = await reading.ConfigureAwait(false);
                if (read == 0)
                {
                    break;
                }

                var start = 0;
                for (var i = 0; i < read; i++)
                {
                    if (buffer[i] == (byte)'\n')
                    {
                        pending.AddRange(buffer.AsSpan(start, i - start));
                        Emit([.. pending], ref format);
                        pending.Clear();
                        start = i + 1;
                    }
                }

                pending.AddRange(buffer.AsSpan(start, read - start));
            }
        }
        catch (IOException)
        {
            // A closed pipe ends the input like end of file.
        }

        if (pending.Count > 0)
        {
            Emit([.. pending], ref format);
        }

        Flush();

        _events.Writer.TryWrite(new LogSourceEvent(LogSourceEventKind.EndOfInput, LinesRead: LinesRead));
        _events.Writer.TryComplete();
    }

    private void Emit(byte[] line, ref LogFormat? format)
    {
        var length = line.Length > 0 && line[^1] == (byte)'\r' ? line.Length - 1 : line.Length;
        var memory = line.AsMemory(0, length);
        if (memory.Span.Trim(" \t\r\n\v\f"u8).IsEmpty)
        {
            return;
        }

        LinesRead++;
        if (format is null)
        {
            format = LogFormatDetector.Detect(memory);
            _events.Writer.TryWrite(new LogSourceEvent(LogSourceEventKind.FormatDetected, Format: format, Path: "stdin"));
        }

        var entry = LogLineParser.Parse(memory, format.Value);
        entry.SourceFile = "stdin";
        if (_grouper.Add(entry) is { } complete)
        {
            _events.Writer.TryWrite(new LogSourceEvent(LogSourceEventKind.Entry, complete));
        }
    }

    private void Flush()
    {
        if (_grouper.Flush() is { } last)
        {
            _events.Writer.TryWrite(new LogSourceEvent(LogSourceEventKind.Entry, last));
        }
    }
}
