using Pgtail.Sessions;

namespace Pgtail.Commands;

/// <summary>
/// What to tail and how.
/// </summary>
/// <param name="Source">The instance, files, or standard input.</param>
/// <param name="LogPath">The first file to read.</param>
/// <param name="Stream">True for streaming output instead of the full screen view.</param>
internal sealed record TailRequest(TailSource Source, string? LogPath, bool Stream);
