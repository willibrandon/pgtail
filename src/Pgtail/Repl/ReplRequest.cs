using Hex1b;
using Hex1b.Widgets;

namespace Pgtail.Repl;

/// <summary>
/// A request from the REPL for the real terminal.
/// </summary>
/// <param name="Kind">What is needed.</param>
internal sealed record ReplRequest(ReplRequestKind Kind)
{
    /// <summary>
    /// The shell command, for <see cref="ReplRequestKind.Shell"/>.
    /// </summary>
    public string? Command { get; init; }

    /// <summary>
    /// Writes the streamed output until the token is cancelled, for <see cref="ReplRequestKind.Stream"/>.
    /// </summary>
    public Func<TextWriter, CancellationToken, Task>? Stream { get; init; }

    /// <summary>
    /// Sets up the full screen app and returns its builder, for <see cref="ReplRequestKind.Screen"/>.
    /// </summary>
    public Func<Hex1bApp, Hex1bAppOptions, Func<RootContext, Hex1bWidget>>? Screen { get; init; }

    /// <summary>
    /// Completed by whoever serves a <see cref="ReplRequestKind.Screen"/> request once the app has stopped.
    /// </summary>
    public TaskCompletionSource Done { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
}
