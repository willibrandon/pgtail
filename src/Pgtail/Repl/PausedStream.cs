using Pgtail.Tailing;

namespace Pgtail.Repl;

/// <summary>
/// A streaming tail paused at the prompt with Ctrl+C.
/// </summary>
/// <param name="Source">The source, still reading.</param>
/// <param name="Label">What the prompt shows in brackets: the instance ID or the file name.</param>
internal sealed record PausedStream(ILogSource Source, string Label);
