using System.Threading.Channels;

namespace Pgtail.Tailing;

/// <summary>
/// A log source that polls on a background task until it is disposed.
/// </summary>
/// <param name="interval">How often to poll.</param>
public abstract class PollingLogSource(TimeSpan interval) : ILogSource
{
    private readonly Channel<LogSourceEvent> _events = Channel.CreateUnbounded<LogSourceEvent>(
        new UnboundedChannelOptions { SingleReader = true, SingleWriter = true });

    private readonly CancellationTokenSource _stop = new();
    private Task? _loop;

    /// <inheritdoc />
    public ChannelReader<LogSourceEvent> Events => _events.Reader;

    /// <inheritdoc />
    public bool IsUnavailable { get; protected set; }

    /// <inheritdoc />
    public bool IsPermissionDenied { get; protected set; }

    /// <inheritdoc />
    public void Start()
    {
        if (_loop is not null)
        {
            return;
        }

        Prepare();
        _loop = Task.Run(RunAsync);
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
                // Stopping is the expected way for the loop to end.
            }
        }

        _events.Writer.TryComplete();
        _stop.Dispose();
        GC.SuppressFinalize(this);
    }

    /// <inheritdoc />
    public virtual void StopReadingOlder()
    {
    }

    /// <summary>
    /// Whether the last poll stopped before the end of what there is to read, so the next one should follow at once.
    /// </summary>
    protected bool Behind { get; set; }

    /// <summary>
    /// Positions the source before its first poll.
    /// </summary>
    protected abstract void Prepare();

    /// <summary>
    /// Reads whatever is new.
    /// </summary>
    protected abstract void Poll();

    /// <summary>
    /// Reports an event to the reader.
    /// </summary>
    /// <param name="item">The event.</param>
    protected void Post(LogSourceEvent item) => _events.Writer.TryWrite(item);

    private async Task RunAsync()
    {
        using var timer = new PeriodicTimer(interval);
        do
        {
            // A backlog, such as a time filter reads back, is read in one go; the interval only paces waiting for more.
            do
            {
                Poll();
            }
            while (Behind && !_stop.IsCancellationRequested);
        }
        while (await timer.WaitForNextTickAsync(_stop.Token).ConfigureAwait(false));
    }
}
