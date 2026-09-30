using Pgtail.Styling;

namespace Pgtail.Commands;

/// <summary>
/// What REPL commands can ask of the interactive prompt beyond printing output.
/// </summary>
internal interface IReplHost : ICommandHost
{
    /// <summary>
    /// Whether a streaming tail is paused at the prompt.
    /// </summary>
    bool IsStreaming { get; }

    /// <summary>
    /// Tails a source, full screen or as streaming output.
    /// </summary>
    /// <param name="request">What to tail and how.</param>
    /// <returns>A task that completes when tailing ends or pauses.</returns>
    Task TailAsync(TailRequest request);

    /// <summary>
    /// Stops a paused streaming tail.
    /// </summary>
    void StopStreaming();

    /// <summary>
    /// Asks a yes or no question; no is the default.
    /// </summary>
    /// <param name="question">The question, such as <c>File x exists. Overwrite? [y/N] </c>.</param>
    /// <returns>True for yes.</returns>
    Task<bool> ConfirmAsync(string question);

    /// <summary>
    /// Opens a file in the built-in editor and waits until it is closed.
    /// </summary>
    /// <param name="request">The file and how to check it.</param>
    /// <returns>True when changes were saved.</returns>
    Task<bool> EditAsync(EditRequest request);

    /// <summary>
    /// Shows output that redraws itself until Ctrl+C or q, then leaves the last drawing in place.
    /// </summary>
    /// <param name="render">Draws the current state.</param>
    /// <param name="interval">How often to redraw.</param>
    /// <returns>A task that completes when the user stops it.</returns>
    Task LiveAsync(Func<IReadOnlyList<StyledText>> render, TimeSpan interval);

    /// <summary>
    /// Prints lines as they arrive until Ctrl+C, then returns to the prompt.
    /// </summary>
    /// <param name="lines">The lines, produced until the token is cancelled.</param>
    /// <returns>A task that completes when the user stops it.</returns>
    Task WatchAsync(Func<CancellationToken, IAsyncEnumerable<StyledText>> lines);

    /// <summary>
    /// Leaves the REPL after this command.
    /// </summary>
    void Exit();

    /// <summary>
    /// Clears the screen after this command.
    /// </summary>
    void ClearScreen();

    /// <summary>
    /// Runs a shell command in the terminal after this command.
    /// </summary>
    /// <param name="command">The command line.</param>
    void RunShell(string command);
}
